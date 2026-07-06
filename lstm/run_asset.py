#!/usr/bin/env python3
"""Per-asset runner: python3 run_asset.py TICKER=AAPL

Strict phase order (the one-shot-OOS discipline):
  D2 load+QC -> D3 split -> D4 features + TRAIN-only z-score -> D5 Train candidates +
  Triple-Barrier labels (purged) -> D6 sequences -> D7 Optuna HPO (purged WF CV) ->
  D8 Kelly λ (Train OOF) + final refit + strategy artifact -> ONLY THEN D9: generate
  OOS candidates, score them ONCE, run the engine ONCE (HODL fallback on zero trades).

Deliverable: Assets/<T>/ {best_params.json, strategy_<T>.py, <T>_README.md} (asserted)
+ one oos_metrics.db UPSERT.
"""
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import torch

import pipeline as P
import model as M
import asset_writers as W

ROOT = Path(__file__).resolve().parent
# The OOS results store. Defaults to the repo's sealed oos_metrics.db (unchanged); an override
# (OOS_METRICS_DB env) lets the reproducibility check write to a scratch db so the committed
# sealed results are never mutated during verification.
OOS_DB = Path(os.environ.get("OOS_METRICS_DB") or (ROOT / "oos_metrics.db"))


def main():
    args = dict(a.split("=", 1) for a in sys.argv[1:] if "=" in a)
    ticker = (args.get("TICKER") or "").upper()
    if not ticker:
        sys.exit("usage: python3 run_asset.py TICKER=AAPL")
    t_start = time.time()
    M.seed_everything()

    # D2-D3
    df = P.load_bars(ticker)
    masks, bounds = P.split_masks(df)

    # per-asset feature manifest: CORE (always) + the searched OPTIONAL/PROPOSED subset
    manifest = P.resolve_manifest(ticker)

    # D4 — features (full superset); manifest z-score stats from full Train (frozen into the
    # artifact / OOS pass); CV folds get their own CAUSAL stats below
    feats = P.feature_frame(df, ticker)                # CORE+OPTIONAL from the RAM cache if built
    norm_stats = P.train_norm_stats(feats, masks["train"], manifest)
    normed = P.normalize(feats, norm_stats, manifest)

    # D5 — Train candidates -> purge -> Triple-Barrier labels
    train_events = P.generate_candidates(df, masks["train"], feats)
    train_events, purged_away = P.purge_train_events(train_events, bounds)
    labeled = P.label_events(df, train_events, bounds["train_end_idx"])

    # D6 — RAW manifest sequences (finiteness is normalization-invariant: affine, σ ≥ 1e-8),
    # then uniqueness weights over exactly the surviving training set
    events, X_raw = P.build_sequences(labeled, feats, manifest)
    if len(events) < 50:
        sys.exit(f"{ticker}: only {len(events)} eligible Train sequences — too thin to model")
    P.assign_uniqueness_weights(events)
    y = np.array([e["y"] for e in events], np.int64)
    w = np.array([e["weight"] for e in events], np.float32)
    t0s = [e["t0"] for e in events]
    print(f"{ticker}: {len(events)} Train sequences, {len(manifest)} features "
          f"({purged_away} purged at the OOS boundary), positives {y.mean():.3f}")

    # D7 — HPO on purged walk-forward CV; each fold normalized with CAUSAL stats
    # (train rows strictly before the fold's embargo boundary — the scaler never sees
    # the fold's validation region or anything after it)
    folds = P.purged_wf_folds(t0s, bounds["train_start_idx"], bounds["train_end_idx"])
    if not folds:
        sys.exit(f"{ticker}: no valid purged CV folds")
    emb = P.CONFIG["EMBARGO_BARS"]
    folds_data = []
    for tr, va, val_lo in folds:
        fold_stats = P.train_norm_stats(feats, masks["train"], manifest, before_idx=val_lo - emb)
        mu = np.array([fold_stats[n]["mean"] for n in manifest], np.float32)
        sd = np.array([fold_stats[n]["std"] for n in manifest], np.float32)
        folds_data.append((tr, va, (X_raw - mu) / sd))
    best_params, refit_epochs, cv_ap = M.hpo(df, events, y, w, folds_data, bounds)
    print(f"{ticker}: HPO best {best_params} refit_epochs={refit_epochs} cv_auc_pr={cv_ap:.4f}")

    # D8 — joint (θ, λ, direction) operating point on Train OOF; final refit on full-Train stats
    cal = M.calibrate_gate_kelly(df, events, y, w, folds_data, best_params, refit_epochs, bounds)
    theta, lam, dmode = cal["theta_entry"], cal["kelly_fraction"], cal["direction_mode"]
    mu_full = np.array([norm_stats[n]["mean"] for n in manifest], np.float32)
    sd_full = np.array([norm_stats[n]["std"] for n in manifest], np.float32)
    X = (X_raw - mu_full) / sd_full
    final_model, _, _ = M.train_model(X, y, w, best_params["hidden"], best_params["lr"],
                                      best_params["dropout"], epochs=refit_epochs,
                                      weight_decay=best_params.get("weight_decay", 0.0),
                                      num_layers=best_params.get("num_layers", 1))
    print(f"{ticker}: gate θ={theta:.2f} λ={lam:.4f} dir={dmode}; refit done")

    # raw (un-normalized) manifest windows for the artifact's golden vectors
    raw_windows = []
    Fraw = feats[manifest].to_numpy(np.float32)
    for e in events[:2]:
        raw_windows.append(Fraw[e["t0"] - P.CONFIG["SEQ_LEN"] + 1:e["t0"] + 1])
    raw_windows = np.stack(raw_windows) if raw_windows else np.empty((0,))

    out_dir = ROOT / "Assets" / ticker
    out_dir.mkdir(parents=True, exist_ok=True)
    meta = W.strategy_meta(final_model, ticker, manifest, best_params, refit_epochs, cal, cv_ap,
                           len(folds), norm_stats, raw_windows)
    W.write_best_params(out_dir / "best_params.json", meta)
    W.write_strategy(out_dir / f"strategy_{ticker}.py", meta)

    # ---- D9: the ONE and ONLY OOS read ----
    oos_events = P.generate_candidates(df, masks["oos"], feats)
    oos_kept, X_oos = P.build_sequences(oos_events, normed, manifest)
    scored = []
    if len(oos_kept):
        p_oos = M.predict_proba(final_model, torch.from_numpy(np.ascontiguousarray(X_oos)))
        scored = list(zip(oos_kept, [float(p) for p in p_oos]))
    scored = M._dir_filter(scored, dmode)                       # long_only acts on up-signals only
    summary, ledger, _ = P.run_engine(df, scored, bounds["oos_start_idx"], bounds["oos_end_idx"],
                                      theta, kelly_fraction=lam)
    if summary["trades"] == 0:
        summary, ledger, _ = P.hodl_fallback(df, bounds["oos_start_idx"], bounds["oos_end_idx"])
    summary["ticker"] = ticker
    summary["kelly_fraction"] = lam
    summary["theta_entry"] = theta
    summary["direction_mode"] = dmode

    oos_first = P.session_date(df, bounds["oos_start_idx"])
    oos_last = P.session_date(df, bounds["oos_end_idx"])
    W.write_readme(out_dir / f"{ticker}_README.md", summary, ledger, manifest)
    W.write_oos_metrics(OOS_DB, {**summary, "cv_auc_pr": cv_ap, "cv_folds": len(folds),
                                 "oos_window": f"{oos_first} -> {oos_last}"})

    expected = {f"strategy_{ticker}.py", f"{ticker}_README.md", "best_params.json"}
    got = {p.name for p in out_dir.iterdir() if p.name != "__pycache__"}
    assert got == expected, f"deliverable contract violated: {sorted(got ^ expected)}"
    print(f"{ticker}: OOS end_capital={summary['end_capital']:.2f} "
          f"return={summary['return_pct']:.2f}% trades={summary['trades']} "
          f"PF={summary['profit_factor']} ({time.time() - t_start:.0f}s)")


if __name__ == "__main__":
    main()

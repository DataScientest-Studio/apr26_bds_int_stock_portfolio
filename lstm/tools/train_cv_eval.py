#!/usr/bin/env python3
"""Train-CV measurement (development only — NEVER reads OOS).

Reproduces run_asset.py's D2–D8 exactly (load → split → features → Train candidates + Triple-Barrier
labels → sequences → purged WF folds → HPO → joint θ/λ/direction calibration), then reports the
Train-side success metrics used to A/B strategy changes:

  train_cv_oof_log_growth : Σ_fold log(end_capital_fold / E0) at the calibrated operating point — the
                            geometric-growth objective (this is exactly what calibrate_gate_kelly maximizes)
  train_cv_pf             : profit factor over the CONCATENATED out-of-fold trade ledger (Σ wins / Σ|losses|)
  train_cv_return_pct     : mean per-fold OOF return %
  plus n_events, candidate count, n_folds, θ, λ, direction, cv_auc_pr — for context.

Everything is on the Train window (2017–2023) with purge+embargo and fold-causal normalization; the OOS
window is never generated here. Deterministic (same seeds as the pipeline). Usage:

  python3 tools/train_cv_eval.py TICKER=AAPL            # one ticker, prints a JSON line
  python3 tools/train_cv_eval.py AAPL KO XOM            # several
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))   # repo root (engine is flat there)
import pipeline as P
import model as M


def train_cv_metrics(ticker):
    """The Train-CV block — a faithful copy of run_asset.py D2–D8, stopping before D9 (no OOS)."""
    M.seed_everything()
    df = P.load_bars(ticker)
    masks, bounds = P.split_masks(df)
    manifest = P.resolve_manifest(ticker)
    feats = P.feature_frame(df, ticker)

    train_events = P.generate_candidates(df, masks["train"], feats)
    n_candidates = len(train_events)
    train_events, _ = P.purge_train_events(train_events, bounds)
    labeled = P.label_events(df, train_events, bounds["train_end_idx"])
    events, X_raw = P.build_sequences(labeled, feats, manifest)
    if len(events) < 50:
        return {"ticker": ticker, "thin": True, "n_events": len(events), "n_candidates": n_candidates}
    P.assign_uniqueness_weights(events)
    y = np.array([e["y"] for e in events], np.int64)
    w = np.array([e["weight"] for e in events], np.float32)
    t0s = [e["t0"] for e in events]

    folds = P.purged_wf_folds(t0s, bounds["train_start_idx"], bounds["train_end_idx"])
    if not folds:
        return {"ticker": ticker, "thin": True, "reason": "no_folds", "n_events": len(events)}
    emb = P.CONFIG["EMBARGO_BARS"]
    folds_data = []
    for tr, va, val_lo in folds:
        st = P.train_norm_stats(feats, masks["train"], manifest, before_idx=val_lo - emb)
        mu = np.array([st[n]["mean"] for n in manifest], np.float32)
        sd = np.array([st[n]["std"] for n in manifest], np.float32)
        folds_data.append((tr, va, (X_raw - mu) / sd))

    best_params, refit_epochs, cv_ap = M.hpo(df, events, y, w, folds_data, bounds)
    cal = M.calibrate_gate_kelly(df, events, y, w, folds_data, best_params, refit_epochs, bounds)
    theta, lam, dmode = cal["theta_entry"], cal["kelly_fraction"], cal["direction_mode"]

    # Train-CV PF: re-run the engine on each fold's OOF predictions at the CALIBRATED operating point
    # (same fold models as calibrate — deterministic), and pool the per-trade account P&L. Strictly
    # inside each fold's [lo, hi+H], provably pre-OOS by the purge invariant (asserted in calibrate).
    H, E0 = P.CONFIG["H"], P.CONFIG["INITIAL_CAPITAL_USD"]
    nets, log_growth, fold_rets, log_growth_fixed = [], 0.0, [], 0.0
    for tr, va, Xf in folds_data:
        if len(np.unique(y[tr])) < 2:
            continue
        m, _, _ = M.train_model(Xf[tr], y[tr], w[tr], best_params["hidden"], best_params["lr"],
                                best_params["dropout"], epochs=refit_epochs,
                                weight_decay=best_params.get("weight_decay", 0.0),
                                num_layers=best_params.get("num_layers", 1))
        oof = M.predict_proba(m, torch.from_numpy(np.ascontiguousarray(Xf[va])))
        all_scored = [(events[j], float(oof[k])) for k, j in enumerate(va)]
        vt0 = [t0s[j] for j in va]
        lo, hi = min(vt0), max(vt0)
        scored = M._dir_filter(all_scored, dmode)
        summary, ledger, _ = P.run_engine(df, scored, lo, hi + H, theta, kelly_fraction=lam)
        log_growth += math.log(max(summary["end_capital"], P.EPS) / E0)
        fold_rets.append(summary["return_pct"])
        nets += [t["account_net_pnl_usd"] for t in ledger]
        # UNBIASED reference: fixed θ=0.5, λ=1.0, both directions — NOT the calibrated point, so
        # not overfit to the fold OOF. A cleaner (still HPO-selected) tradeability signal for A/B.
        fx = P.run_engine(df, all_scored, lo, hi + H, 0.5, kelly_fraction=1.0)[0]["end_capital"]
        log_growth_fixed += math.log(max(fx, P.EPS) / E0)
    nets = np.array(nets)
    gp = float(nets[nets > 0].sum()) if len(nets) else 0.0
    gl = float(-nets[nets < 0].sum()) if len(nets) else 0.0
    pf = (gp / gl) if gl > 0 else (float("inf") if gp > 0 else 0.0)
    return {"ticker": ticker, "thin": False,
            "n_candidates": n_candidates, "n_events": int(len(events)), "n_folds": len(folds),
            "train_cv_oof_log_growth": round(float(log_growth), 6),
            "train_cv_loggrowth_fixed": round(float(log_growth_fixed), 6),
            "train_cv_pf": round(float(pf), 4) if math.isfinite(pf) else None,
            "train_cv_return_pct": round(float(np.mean(fold_rets)), 4) if fold_rets else 0.0,
            "train_cv_trades": int(len(nets)),
            "cv_auc_pr": round(float(cv_ap), 4),
            "theta": round(float(theta), 3), "lambda": round(float(lam), 4), "direction": dmode,
            "reward_risk_b": round(float(P.CONFIG["TB_ATR_TP"]) / float(P.CONFIG["TB_ATR_SL"]), 3)}


def main():
    args = [a.split("=", 1)[1] if a.startswith("TICKER=") else a for a in sys.argv[1:]]
    tickers = [t.upper() for t in args] or ["AAPL"]
    for t in tickers:
        try:
            print(json.dumps(train_cv_metrics(t)), flush=True)
        except Exception as e:
            print(json.dumps({"ticker": t, "error": repr(e)[:200]}), flush=True)


if __name__ == "__main__":
    main()

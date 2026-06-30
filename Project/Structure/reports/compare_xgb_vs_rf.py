#!/usr/bin/env python3
"""Boosting (XGBoost) vs Bagging (RandomForest) — Train-only purged walk-forward AUC-PR.

This is the model-comparison companion for the Modeling Report (Rendering 2,
mentor request 2026-05-28: "compare XGBoost vs RandomForest"). It does NOT touch
the OOS window and it does NOT re-implement the pipeline — it reuses pipeline.py:

  * derive_output_b_from_parquet  -> the exact Train Output-B (X, Y, uniqueness w)
  * purged_wf_folds               -> the exact 4-fold purged walk-forward CV
  * _xgb_train / average_precision -> the exact estimator + AUC-PR metric

Per asset and per fold it scores three models on the held-out fold:
  * xgb_baseline : untuned XGBoost (the project's fallback_params)  -> §3 baseline
  * xgb_tuned    : XGBoost at the saved Optuna best_params          -> should match cv_auc_pr
  * rf           : sklearn RandomForestClassifier (bagging baseline)

RandomForest cannot consume NaN, so the 1d/1w/cross-TF NaNs are median-imputed
(fit on the training fold only). XGBoost needs no imputation (native missing) —
that asymmetry is itself a finding for the report.

Run from anywhere:  python reports/compare_xgb_vs_rf.py
Writes:             reports/xgb_vs_rf_results.json  (+ a Markdown table to stdout)
"""
import json
import sys
import warnings
from pathlib import Path

import numpy as np

# pipeline.py emits "Mean of empty slice" on early-history all-NaN context rows;
# harmless here (those rows are gated out as core-ineligible before scoring).
warnings.filterwarnings("ignore", message="Mean of empty slice", category=RuntimeWarning)

STRUCTURE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STRUCTURE))

import pipeline as P  # noqa: E402
import xgboost as xgb  # noqa: E402
from sklearn.ensemble import RandomForestClassifier  # noqa: E402
from sklearn.impute import SimpleImputer  # noqa: E402

SEED = P.PIPELINE_PARAMETERS["RANDOM_SEED"]
RF_N_ESTIMATORS = 300
TICKERS = ["AAPL", "AMZN", "GOOGL", "JNJ", "JPM", "META", "MSFT", "NVDA", "TSLA", "XOM"]
FALLBACK = dict(P.XGBOOST_OPTUNA_SEARCH_SPACE["fallback_params"])
NAMES = P.feature_names_of()


def _load_best_params(ticker):
    path = STRUCTURE / "Assets" / ticker / "OPTUNAs_XGB_HPOs_best_params.json"
    return dict(json.loads(path.read_text(encoding="utf-8"))["best_params"])


def _xgb_ap(X, y, w, params, tr, va):
    bst = P._xgb_train(X[tr], y[tr], w[tr], params, SEED, feature_names=NAMES)
    p = bst.predict(xgb.DMatrix(X[va], feature_names=NAMES))
    return P.average_precision(y[va], p)


def _rf_ap(X, y, w, tr, va):
    imp = SimpleImputer(strategy="median").fit(X[tr])
    rf = RandomForestClassifier(n_estimators=RF_N_ESTIMATORS, random_state=SEED, n_jobs=1)
    rf.fit(imp.transform(X[tr]), y[tr], sample_weight=w[tr])
    p = rf.predict_proba(imp.transform(X[va]))[:, 1]
    return P.average_precision(y[va], p)


def evaluate(ticker):
    parquet = STRUCTURE / "Assets" / ticker / f"{ticker}_ohlcv_1h.parquet"
    ob = P.derive_output_b_from_parquet(parquet, ticker)
    df_b, bounds = ob["df_b"], ob["bounds"]
    if df_b.empty:
        return {"ticker": ticker, "n_setups": 0, "n_folds": 0}
    X = df_b[NAMES].to_numpy(float)
    y = df_b["Y_outcome"].to_numpy(int)
    w = df_b["label_uniqueness_weight"].to_numpy(float)
    t0s = [int(sid.split(":")[1]) for sid in df_b["setup_id"]]
    folds = P.purged_wf_folds(t0s, bounds["train_start_idx"], bounds["train_end_idx"])
    base_ap, tuned_ap, rf_ap = [], [], []
    best = _load_best_params(ticker)
    for tr, va in folds:
        if len(np.unique(y[tr])) < 2:
            continue
        base_ap.append(_xgb_ap(X, y, w, FALLBACK, tr, va))
        tuned_ap.append(_xgb_ap(X, y, w, best, tr, va))
        rf_ap.append(_rf_ap(X, y, w, tr, va))

    def mean(a):
        return float(np.mean(a)) if a else None

    return {"ticker": ticker, "n_setups": int(len(df_b)), "n_folds": len(folds),
            "n_folds_scored": len(tuned_ap), "pos_rate": float(y.mean()),
            "xgb_baseline_aucpr": mean(base_ap), "xgb_tuned_aucpr": mean(tuned_ap),
            "rf_aucpr": mean(rf_ap)}


def _fmt(v):
    return "—" if v is None else f"{v:.3f}"


def main():
    P.seed_everything(SEED)
    rows = [evaluate(t) for t in TICKERS]
    out = {"seed": SEED, "rf_n_estimators": RF_N_ESTIMATORS, "cv_scheme": "purged_walk_forward",
           "metric": "auc_pr", "scope": "Train only (no OOS read)", "results": rows}
    (Path(__file__).resolve().parent / "xgb_vs_rf_results.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")

    print("\n| Ticker | Setups | Folds | Pos-rate | Baseline XGB | Tuned XGB | RandomForest | Δ (XGB−RF) |")
    print("|---|---|---|---|---|---|---|---|")
    deltas = []
    for r in rows:
        if not r.get("n_folds_scored"):
            print(f"| {r['ticker']} | {r.get('n_setups', 0)} | 0 | — | — | — | — | — |")
            continue
        d = (r["xgb_tuned_aucpr"] - r["rf_aucpr"])
        deltas.append(d)
        print(f"| {r['ticker']} | {r['n_setups']} | {r['n_folds_scored']} | {r['pos_rate']:.3f} "
              f"| {_fmt(r['xgb_baseline_aucpr'])} | {_fmt(r['xgb_tuned_aucpr'])} | {_fmt(r['rf_aucpr'])} "
              f"| {d:+.3f} |")
    if deltas:
        print(f"\nMean tuned-XGB AUC-PR − RF AUC-PR over scored assets: {np.mean(deltas):+.3f}")
    print("\nWrote reports/xgb_vs_rf_results.json")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Writers used by the per-asset notebook (Layers 3.2 + 4.1 + 4.2): the standalone strategy artifact, the OOS README,
the feature-table helper, and write_oos_metrics (the Layer 4.1 OOS verdict -> oos_metrics.db results store the Dashboard
reads). Kept out of pipeline.py (which is pure compute) so each file has one job. No SHA lineage, no contract bundle;
the only state beyond the 7 deliverable files is oos_metrics.db (which lives in Structure/, not Assets/).
"""
from datetime import date
from pathlib import Path

import pipeline as P


def _write_text(path, text):
    P.atomic_write(path, lambda p: Path(p).write_text(text, encoding="utf-8"))


def write_strategy(path, m):
    """File #6: strategy_<TICKER>.py — a standalone artifact with the XGBoost model embedded as base64 (MODEL_B64).
    `m` is pipeline.strategy_meta(...) (+ m["ACCEPTANCE"]). Reloads + selfchecks against the golden vectors on run."""
    body = f'''"""Standalone strategy artifact for {m["ticker"]} (Layer 3.2). Imports with no training-data access.
LABEL_CONTRACT = {m["LABEL_CONTRACT"]}; the XGBoost meta-label model is embedded as base64 (MODEL_B64).
"""
import base64

TICKER = {m["ticker"]!r}
LABEL_CONTRACT = {m["LABEL_CONTRACT"]!r}
FEATURE_MANIFEST = {m["FEATURE_MANIFEST"]!r}
FEATURE_IDS = {m["FEATURE_IDS"]!r}
THRESHOLD_ENTRY = {m["THRESHOLD_ENTRY"]!r}
MODEL_HASH = {m["MODEL_HASH"]!r}
TRAIN_WINDOW = {m["TRAIN_WINDOW"]!r}
EXECUTION_CONTRACT = {m["EXECUTION_CONTRACT"]!r}
ACCEPTANCE = {m["ACCEPTANCE"]!r}
BEST_PARAMS = {m["best_params"]!r}
_GOLDEN_VECTORS = {m["golden_vectors"]!r}
_GOLDEN_PRED = {m["golden_pred"]!r}
MODEL_B64 = "{m["MODEL_B64"]}"


def _load():
    import xgboost as xgb, tempfile, os, hashlib
    raw = base64.b64decode(MODEL_B64)
    assert hashlib.sha256(raw).hexdigest() == MODEL_HASH, "MODEL_HASH mismatch"
    bst = xgb.Booster()
    with tempfile.NamedTemporaryFile(suffix=".ubj", delete=False) as f:
        f.write(raw); tmp = f.name
    try:
        bst.load_model(tmp)
    finally:
        os.unlink(tmp)
    return bst


def predict_proba(X):
    import xgboost as xgb, numpy as np
    return _load().predict(xgb.DMatrix(np.asarray(X, float).reshape(-1, len(FEATURE_MANIFEST)),
                                       feature_names=FEATURE_MANIFEST))


def selfcheck():
    if not _GOLDEN_VECTORS:
        return True
    import numpy as np
    assert np.allclose(predict_proba(_GOLDEN_VECTORS), _GOLDEN_PRED, atol=1e-6), "selfcheck divergence"
    return True


if __name__ == "__main__":
    print("selfcheck:", selfcheck())
'''
    _write_text(path, body)


def features_table_lines(manifest):
    """The effective feature manifest (the X columns the model was trained on) as a Markdown table — straight from the
    resolved manifest. Column order is the model's DMatrix order (timeframe-then-ID); within a timeframe the first
    standard_count features are the standard trendline set (FT), the rest are additional (F)."""
    m = manifest
    blocks = list(m["per_timeframe"]) + ([m["cross_timeframe"]] if m.get("cross_timeframe") else [])
    rows, pos = [], 0
    for blk in blocks:
        tf = blk.get("timeframe", "between_timeframes")
        for i, (fid, name) in enumerate(zip(blk["feature_ids"], blk["feature_names"])):
            pos += 1
            kind = f"Standard trendline (FT{fid})" if i < blk["standard_count"] else f"Additional (F{fid})"
            rows.append(f"| {pos} | {fid} | `{name}` | {tf} | {kind} |")
    n_std = sum(b["standard_count"] for b in blocks)
    return [f"## Features used to train the model ({m['effective_feature_count']} X columns)", "",
            f"- selected timeframes: {', '.join(m['selected_timeframes'])} · {n_std} standard trendline + "
            f"{m['effective_feature_count'] - n_std} additional · model column order = timeframe-then-ID",
            f"- selection source: `{m['feature_selection_source']}`", "",
            "| # | ID | Feature | Timeframe | Type |",
            "|--|--|--|--|--|"] + rows


def write_readme(path, s, ledger, manifest):
    """File #7: <TICKER>_README.md — the OOS capital path + feature table + Risk-Box trade ledger. `s` is the OOS
    run_engine summary (+ s["ticker"]); `ledger` is the trade list; `manifest` is the resolved feature manifest."""
    sp = P.PIPELINE_PARAMETERS["splits"]                                   # the OOS window return_pct is earned over
    oos_days = (date.fromisoformat(sp["oos_end"]) - date.fromisoformat(sp["oos_start"])).days
    roi_per_365 = s["return_pct"] * 365.0 / oos_days if oos_days else 0.0  # return_pct annualized to 365 days
    cap_mode = s.get("capital_mode", P.PIPELINE_PARAMETERS["CAPITAL_MODE"])
    lam = s.get("kelly_fraction")
    L = [f"# {s['ticker']} — OOS report (current cycle)", "",
         "- EXECUTION_SCOPE: SYNTHETIC_SYMMETRIC_OHLCV_RISK_BOX",
         "- RESULT_INTERPRETATION: historical behaviour under this fill / cost / Risk-Box / position-sizing / "
         "compounding model; not broker-specific execution proof.", "",
         f"## Capital path ({cap_mode})", "",
         f"- ROI/365: {roi_per_365:.2f}%",
         f"- data range: {sp['oos_start']} → {sp['oos_end']} ({oos_days} days)",
         f"- start_capital: {s['start_capital']}", f"- end_capital: {s['end_capital']:.2f}",
         f"- return_pct: {s['return_pct']:.2f}%", f"- profit_factor: {s['profit_factor']}",
         f"- max_drawdown_pct: {s['max_drawdown_pct']:.2f}%", f"- win_rate_pct: {s['win_rate_pct']:.2f}%",
         f"- trades: {s['trades']} (wins {s['wins']} / losses {s['losses']})",
         f"- time_in_market_pct: {s['time_in_market_pct']}",
         f"- uncovered_loss_total_usd: {s['uncovered_loss_total_usd']:.2f} (max {s['max_uncovered_loss_usd']:.2f})",
         f"- capital_depleted: {s['capital_depleted']}"]
    if lam is not None:
        L.append(f"- kelly_fraction (λ): {lam:.4f} — per-trade f = clip(λ·(2p−1), 0, "
                 f"{P.PIPELINE_PARAMETERS['KELLY_CAP']}); b=1 symmetric Risk-Box, Train-OOF calibrated")
    L.append("")
    L += features_table_lines(manifest)
    L += ["",
          "## Risk-Box trade ledger (ORDER BY trade_id ASC)", "",
          "| # | dir | entry_fill_timestamp | entry | target | exit_fill_timestamp | exit | reason | acct_net | cap_after |",
          "|--|--|--|--|--|--|--|--|--|--|"]
    for l in ledger[:50]:
        L.append(f"| {l['trade_id']} | {l['direction']} | {l['entry_fill_timestamp']} | {l['entry_fill']:.4f} "
                 f"| {l['target_level']:.4f} | {l['exit_fill_timestamp']} | {l['exit_fill']:.4f} "
                 f"| {l['market_exit_reason']} | {l['account_net_pnl_usd']:.2f} | {l['capital_after']:.2f} |")
    if len(ledger) > 50:
        L.append(f"| … | | {len(ledger)-50} more | | | | | | | |")
    _write_text(path, "\n".join(L) + "\n")


def write_oos_metrics(db_path, row):
    """Layer 4.1 results store: UPSERT one asset's OOS verdict into oos_metrics.db — the per-asset table the Dashboard
    reads. Side-effect OUTSIDE the 7-file deliverable (lives in Structure/, keyed by ticker). stdlib sqlite3; only OOS
    result columns — no lineage / contract / source-QC."""
    import sqlite3
    cols = ["ticker", "start_capital", "end_capital", "net_pnl_usd", "return_pct", "profit_factor",
            "max_drawdown_pct", "win_rate_pct", "trades", "wins", "losses", "time_in_market_pct",
            "capital_depleted", "cv_auc_pr", "cv_folds", "oos_window"]
    con = sqlite3.connect(str(db_path))
    try:
        con.execute(
            "create table if not exists oos_metrics ("
            "ticker text primary key, start_capital real, end_capital real, net_pnl_usd real, return_pct real, "
            "profit_factor real, max_drawdown_pct real, win_rate_pct real, trades integer, wins integer, "
            "losses integer, time_in_market_pct real, capital_depleted integer, cv_auc_pr real, cv_folds integer, "
            "oos_window text)")
        vals = [row.get(c) for c in cols]
        cd = cols.index("capital_depleted")                                   # normalize bool -> 0/1
        if vals[cd] is not None:
            vals[cd] = int(bool(vals[cd]))
        con.execute("insert or replace into oos_metrics (" + ",".join(cols) + ") values (" +
                    ",".join("?" * len(cols)) + ")", vals)
        con.commit()
    finally:
        con.close()

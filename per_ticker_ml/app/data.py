"""app/data.py — the ONE data-access module for the presentation console.

The ONLY place in the app that:
- opens data/results.db (sqlite, mode=ro),
- verifies the schema and dataset completeness (fail-closed statuses),
- holds every SQL query the three pages need,
- caches small aggregates (lru_cache; the db is sealed, so caches never go stale),
- lazy-loads per-asset JSONs ONLY after an asset is selected, strictly via
  asset_results.artifact_path -> manifest.json / parameters.json / metrics.json /
  interpretation.json (no folder scanning, ever).

Pages import this module and nothing else data-related. No page opens SQLite or
touches the filesystem on its own. The data layer is sealed — this module treats
it as immutable. Cached DataFrames are shared across sessions: pages must treat
them as read-only (filtering/sorting returns copies, so plain use is safe).
"""
import json
import sqlite3
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "results.db"

EXPECTED_TABLES = {
    "research_run", "asset_results", "asset_features", "feature_search_summary",
    "integrity_checks", "feature_train_stats", "feature_contributions", "xgb_entry_ranges",
    "oos_read_summary",
}
EXPECTED_FREEZE_PREFIX = "public/"   # stable-1, stable-2, … — the label carries the release
ARTIFACT_JSONS = ("manifest.json", "parameters.json", "metrics.json", "interpretation.json")
MODEL_KEY = {"XGBoost": "xgb", "LSTM": "lstm"}   # display name -> store key

# fail-closed statuses (STREAMLIT_DESIGN §4)
OK = "OK"
NOT_FOUND = "NOT FOUND"
SCHEMA_MISMATCH = "SCHEMA MISMATCH"
INTEGRITY_FAILED = "DATA INTEGRITY: FAILED"
PARTIAL = "DATASET STATUS: PARTIAL"


def _connect():
    return sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)


def _rows(sql, params=()):
    con = _connect()
    con.row_factory = sqlite3.Row
    try:
        return [dict(r) for r in con.execute(sql, params)]
    finally:
        con.close()


# ---------------------------------------------------------------- health (fail-closed)

@lru_cache(maxsize=1)
def health():
    """Single fail-closed verdict the app banners on. Never raises."""
    if not DB_PATH.exists():
        return {"status": NOT_FOUND, "detail": "data/results.db missing — clone incomplete"}
    try:
        tables = {r["name"] for r in _rows("select name from sqlite_master where type='table'")}
    except sqlite3.Error as exc:
        return {"status": NOT_FOUND, "detail": f"unreadable: {exc}"}
    missing = EXPECTED_TABLES - tables
    if missing:
        return {"status": SCHEMA_MISMATCH, "detail": f"missing tables: {sorted(missing)}"}
    run = research_run()
    bad = _rows("select check_name, status from integrity_checks where status != 'PASS'")
    if bad:
        return {"status": INTEGRITY_FAILED, "detail": str([b["check_name"] for b in bad][:5]), "run": run}
    freeze = run.get("presentation_freeze") or ""
    if run.get("research_status") != "FROZEN_FINAL_RESEARCH_SNAPSHOT" \
            or not freeze.startswith(EXPECTED_FREEZE_PREFIX):
        return {"status": PARTIAL,
                "detail": f"status={run.get('research_status')} freeze={freeze or '-'}", "run": run}
    counts = {r["model"]: r["n"] for r in
              _rows("select model, count(*) as n from asset_results group by model")}
    expected = {"xgb": run.get("xgb_assets"), "lstm": run.get("lstm_assets")}
    if counts != expected:
        return {"status": PARTIAL,
                "detail": f"asset rows {counts} != declared {expected}", "run": run}
    return {"status": OK, "detail": freeze, "run": run}


# ---------------------------------------------------------------- small aggregates (cached)

@lru_cache(maxsize=1)
def research_run():
    rows = _rows("select * from research_run")
    return rows[0] if rows else {}


@lru_cache(maxsize=1)
def tickers():
    return [r["ticker"] for r in _rows("select distinct ticker from asset_results order by ticker")]


@lru_cache(maxsize=1)
def integrity():
    return _rows("select * from integrity_checks order by check_name")


# ---------------------------------------------------------------- page DataFrames (cached)

@lru_cache(maxsize=1)
def results_df():
    """Every result row for distributions (Comparison) and medians (Statistics)."""
    rows = _rows(
        "select ticker, model, result_mode, return_pct, profit_factor, model_trades,"
        " hodl_return_pct, beats_hodl, max_drawdown_pct, win_rate_pct,"
        " theta_entry, theta_boundary from asset_results")
    return pd.DataFrame(rows)


@lru_cache(maxsize=1)
def overview_stats():
    """Per-model medians for Statistics. Profit-factor stats are computed ONLY on
    rows with model_trades >= 2 and a non-null PF, and carry that coverage count."""
    df = results_df()
    out = {}
    for model, g in df.groupby("model"):
        pf = g[(g["model_trades"] >= 2) & g["profit_factor"].notna()]["profit_factor"]
        out[model] = {
            "n_assets": int(len(g)),
            "median_return_pct": float(g["return_pct"].median()),
            "median_hodl_return_pct": float(g["hodl_return_pct"].median()),
            "beats_hodl_n": int(g["beats_hodl"].sum()),
            "beats_hodl_pct": float(100.0 * g["beats_hodl"].sum() / len(g)),
            "median_profit_factor": float(pf.median()) if len(pf) else None,
            "pf_coverage_n": int(len(pf)),
        }
    return out


# ---------------------------------------------------------------- basket simulator

@lru_cache(maxsize=2)
def simulator_rows(model):
    """Capital endpoints + the win/loss split for one pipeline, for the Basket Simulator.

    Deliberately NOT part of results_df(): the simulator needs end_capital, wins,
    losses and trade_floor_met, which the distribution pages never read — widening
    the shared frame would make three pages pay for two. There is no per-trade data
    anywhere in this release, so a basket is the sum of per-asset ENDPOINTS: no
    equity curve, no drawdown path, no timing.
    """
    return pd.DataFrame(_rows(
        "select ticker, result_mode, end_capital, return_pct, model_trades, trades,"
        " wins, losses, max_drawdown_pct, win_rate_pct, profit_factor,"
        " trade_floor_met, hodl_return_pct, benchmark_trades, oos_window"
        " from asset_results where model=? order by ticker", (MODEL_KEY.get(model, model),)))


@lru_cache(maxsize=2)
def hodl_returns(model):
    """{ticker: price-only buy-and-hold return %} — the benchmark leg of a basket.
    Assets whose benchmark is null are dropped, so the caller can tell how many of
    its picks actually carry a benchmark."""
    rows = _rows("select ticker, hodl_return_pct from asset_results"
                 " where model=? and hodl_return_pct is not null",
                 (MODEL_KEY.get(model, model),))
    return {r["ticker"]: r["hodl_return_pct"] for r in rows}


@lru_cache(maxsize=1)
def payoff_ratios():
    """The REALIZED median win/loss payoff per model, recovered from sealed scalars.

    profit_factor = (wins x avg_win) / (losses x avg_loss), so avg_win/avg_loss =
    PF x losses / wins. The barrier geometry is nominally 2:1 (2xATR target against
    a 1xATR stop); this is what actually settled once triggers on the close, next-open
    fills, gaps and two-sided costs were paid. Promoted rows only, and only where both
    a win and a loss exist — the ratio is undefined otherwise.
    """
    rows = _rows("select model, profit_factor, wins, losses from asset_results"
                 " where result_mode='ML_MULTI_TRADE' and profit_factor is not null"
                 " and wins > 0 and losses > 0")
    out = {}
    for model in ("xgb", "lstm"):
        vals = pd.Series([r["profit_factor"] * r["losses"] / r["wins"]
                          for r in rows if r["model"] == model])
        out[model] = {"median_payoff": float(vals.median()) if len(vals) else None,
                      "n": int(len(vals))}
    return out


# ---------------------------------------------------------------- per-asset queries

def asset(ticker, model):
    """One sealed row. Accepts either vocabulary for `model` ('XGBoost' or 'xgb'), like
    every other model-keyed accessor here — a display name used to return None silently."""
    rows = _rows("select * from asset_results where ticker=? and model=?",
                 (ticker, MODEL_KEY.get(model, model)))
    return rows[0] if rows else None


def features(ticker, model):
    return _rows("select * from asset_features where ticker=? and model=? order by feature_id",
                 (ticker, model))


def contributions(ticker, model):
    return _rows("select * from feature_contributions where ticker=? and model=? "
                 "order by contribution_share desc", (ticker, model))


# ---------------------------------------------------------------- lazy artifact JSONs

def artifact_dir(ticker, model):
    """Resolved via asset_results.artifact_path ONLY (the tracked artifacts/ tree on a
    clean clone; never a folder scan)."""
    row = asset(ticker, model)
    if not row or not row.get("artifact_path"):
        return None
    return ROOT / row["artifact_path"]


@lru_cache(maxsize=64)
def artifact_json(ticker, model, name):
    """Lazy per-asset JSON (call only AFTER an asset is selected). name must be one of
    ARTIFACT_JSONS; returns None when the file is absent (fail-soft, page shows status)."""
    if name not in ARTIFACT_JSONS:
        raise ValueError(f"not an artifact json: {name}")
    base = artifact_dir(ticker, model)
    if base is None:
        return None
    p = base / name
    if not p.exists():
        return None
    return json.loads(p.read_text())


def interpretation(ticker, model):
    """The interpretation payload (per_bin / trajectories / disclaimer / labels live here)."""
    return artifact_json(ticker, model, "interpretation.json")

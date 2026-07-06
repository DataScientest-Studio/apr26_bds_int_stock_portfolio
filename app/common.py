"""Shared paths, method registry and cached loaders for the unified Streamlit app.

Everything here is READ-ONLY over committed artifacts: the two sealed OOS stores (Track A),
the vendored Track-B CSVs, the committed daily bar store and the pre-OOS inputs table.
Nothing trains, trades or writes at runtime.
"""
import json
import sqlite3
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]          # repo root (this file lives in app/)
DATA = Path(__file__).resolve().parent / "data"     # app-owned committed inputs
BARS_DB = ROOT / "lstm" / "data" / "sp500_1d.duckdb"
ENTRY_USD = 1000.0

_HONEST = ("\n\n> **Honest status (v2):** these sealed numbers are the *strategy-v2* re-seal — profit-aligned "
           "Optuna + asymmetric barriers + generalized Kelly. The one-shot OOS over the full universe "
           "showed v2 does **not** beat the prior baseline (see `docs/PROJECT_STATE.md`). The pipeline is "
           "audited leak-free; the numbers are reported as-is, not curated.")

XGB_HOW = """\
**How this works — an ML + Deep-Research investment scheme (XGBoost, v2)**

- **Per asset, a gradient-boosted tree (XGBoost)** predicts whether a Triple-Barrier trade will win,
  from namespaced **multi-timeframe** features (1h / 1d / 1w). Entry = momentum with a causal
  significant-move gate; **asymmetric ATR barrier** (TP 2× / SL 1×).
- **Optuna (Train only):** tunes the XGBoost hyper-parameters (+ regularization) by maximizing the
  model's own **Train out-of-fold trading log-growth** — chosen for *profit*, not a ranking metric.
- **Feature search (Train only):** forward selection picks each asset's feature subset behind an
  overfit gate; a Claude Sonnet agent may propose new causal-DSL features.
- **Sizing:** generalized fractional Kelly `f = clip(λ·(p−(1−p)/b), 0, cap)`, `b` = barrier reward:risk.
- **One-shot OOS:** the 2024→2026 window is scored **exactly once per asset and never used to choose
  anything** — honest unseen-data performance, not a fit to the test.""" + _HONEST

LSTM_HOW = """\
**How this works — an ML + Deep-Research investment scheme (LSTM, v2)**

- **Per asset, an LSTM** predicts whether a Triple-Barrier trade will win, from a 60-day window of
  causal daily features. Entry = momentum with a causal significant-move gate; **asymmetric ATR
  barrier** (TP 2× / SL 1×).
- **Optuna (Train only):** tunes hidden/lr/dropout + **weight-decay/num-layers** by maximizing the
  model's own **Train out-of-fold trading log-growth** — chosen for *profit*, not AUC-PR.
- **Feature search (Train only):** forward selection behind a seed-averaged, complexity-penalized
  overfit gate; Sonnet may propose new causal-DSL features.
- **Operating point:** entry threshold θ, Kelly fraction λ and trade direction calibrated jointly on
  Train out-of-fold log-growth; generalized Kelly `f = clip(λ·(p−(1−p)/b), 0, cap)`.
- **One-shot OOS:** scored **exactly once per asset and never used to choose anything.**""" + _HONEST

# Ordered — index 0 (XGBoost) is the default. Each method reads its OWN sealed store + HODL feed.
METHODS = {
    "XGBoost": {"noun": "XGBoost",
                "db": ROOT / "xgb" / "data" / "oos_metrics.db",
                "feed": ROOT / "xgb" / "plan" / "data" / "dashboard.json",
                "blurb": XGB_HOW},
    "LSTM": {"noun": "LSTM",
             "db": ROOT / "lstm" / "oos_metrics.db",
             "feed": ROOT / "lstm" / "dashboard" / "data" / "dashboard.json",
             "blurb": LSTM_HOW},
}
METHOD_NAMES = list(METHODS)


@st.cache_data(ttl=60)
def load_metrics(db: Path) -> pd.DataFrame:
    """All oos_metrics rows for one method's store, ticker-sorted. Empty frame on any miss — the
    caller fails soft. Cached per db path, so switching methods is instant after the first read."""
    if not Path(db).exists():
        return pd.DataFrame()
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True, timeout=5.0)
        try:
            return pd.read_sql_query("select * from oos_metrics order by ticker", con)
        finally:
            con.close()
    except (sqlite3.Error, pd.errors.DatabaseError):
        return pd.DataFrame()


def parse_window(window: str) -> tuple[str, str, int]:
    """'2024-01-02 -> 2026-04-30' -> ('2024-01-02', '2026-04-30', days_between)."""
    start_s, end_s = (s.strip() for s in window.split("->"))
    return start_s, end_s, (date.fromisoformat(end_s) - date.fromisoformat(start_s)).days


@st.cache_data(ttl=60)
def load_hodl(feed: Path) -> dict:
    """Per-ticker buy-and-hold return over the OOS window, from one method's committed dashboard feed —
    the honest benchmark the basket is judged against. Empty on any miss (fails soft)."""
    try:
        data = json.loads(Path(feed).read_text(encoding="utf-8"))
        return {a["ticker"]: a["hodl_return_pct"] for a in data.get("assets", [])
                if a.get("hodl_return_pct") is not None}
    except (OSError, ValueError, KeyError):
        return {}


@st.cache_data
def load_tickers() -> pd.DataFrame:
    """Static GICS metadata (ticker, name, sector, industry) — vendored from the parent project."""
    return pd.read_csv(DATA / "tickers.csv")


@st.cache_data
def load_preoos_inputs() -> pd.DataFrame:
    """Per-ticker volatility_60d / ret_60d as of the last Train session (<= 2023-12-29) — the only
    risk inputs the preset-package rule may use (no OOS information; see tools/make_preoos_inputs.py)."""
    return pd.read_csv(DATA / "preoos_inputs.csv")


@st.cache_data
def load_bars() -> pd.DataFrame:
    """The committed daily store as one long frame with per-ticker daily returns — feeds the Data
    Explorer only (descriptive plots). RAW prices: corporate actions are deferred, so a split shows
    as a price cliff; the Explorer says so explicitly."""
    import duckdb
    con = duckdb.connect(str(BARS_DB), read_only=True)
    try:
        df = con.execute(
            "select symbol as ticker, date, open, high, low, close, volume from bars_1d "
            "order by symbol, date").fetchdf()
    finally:
        con.close()
    df["date"] = pd.to_datetime(df["date"])
    df["daily_return"] = df.groupby("ticker")["close"].pct_change()
    return df


def track_a_badge() -> None:
    st.success("**Track A — sealed tier.** Purged + embargoed walk-forward CV, net of costs, "
               "Kelly-sized, one-shot OOS read exactly once per asset, audited leak-free, "
               "byte-reproducible (`make verify-*`).", icon="✅")


def track_b_badge() -> None:
    st.warning("**Track B — exploratory tier.** Cross-sectional ranking experiment vendored from the "
               "parent project, shown for transparency: fixed split + walk-forward **without purge or "
               "embargo** (63-day labels overlap every boundary), **gross** returns (no costs, no "
               "sizing), overlapping horizons (pooled Spearman overstates the effective sample), "
               "survivor-only universe. Package returns on this page are **model predictions, not "
               "backtests**. Numbers here must not be compared 1:1 with Track A results.", icon="⚠️")

#!/usr/bin/env python3
"""ML Basket Simulator — read-only Streamlit demo over two sealed OOS result stores.

Pick a **method** (XGBoost, default — or LSTM), then pick tickers (each = $1000 entry on the first
OOS session) and see what the basket became by the end of that method's fixed OOS window. NOTHING
runs at runtime: no training, no trading — the app only reads the precomputed per-asset OOS rows
(oos_metrics.db) each method's pipeline wrote. Switching the method just swaps the source store and
its buy-and-hold feed; tickers without an OOS row for that method simply do not appear in the picker.

Run:  make app    (Streamlit on :8502)
"""
import json
import sqlite3
import sys
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]          # repo root (this file lives in app/)
sys.path.insert(0, str(ROOT))                       # so `import fs.*` resolves from the repo root
ENTRY_USD = 1000.0
GRID_COLS = 10
CALC_SECONDS = 1.5
DETAIL_COLS = ["ticker", "end_capital", "return_pct", "trades",
               "max_drawdown_pct", "win_rate_pct", "profit_factor"]

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

GRID_CSS = """<style>
/* ticker tiles only (scoped by the st-key-tk_* container class) */
div[class*="st-key-tk_"] button {
    aspect-ratio: 1 / 1;
    width: 100%;
    padding: 0;
    font-size: 0.8rem;
    border-radius: 6px;
}
div[class*="st-key-tk_"] button[data-testid="stBaseButton-secondary"] {
    background: #ffffff;
    color: #262730;
    border: 1px solid #d6d6d8;
}
</style>"""


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


def compute_basket(selected: list, df: pd.DataFrame, feed: Path) -> dict:
    """Basket outcome from the precomputed per-asset rows; invested derives from the matched rows so
    the numbers stay internally consistent. Adds the same basket's buy-and-hold outcome (each $1000
    held over the identical OOS window) as the transparent benchmark."""
    rows = df[df["ticker"].isin(selected)]
    invested = ENTRY_USD * len(rows)
    final = float(rows["end_capital"].sum())
    pnl = final - invested
    hodl = load_hodl(feed)
    hset = [t for t in rows["ticker"] if t in hodl]
    hodl_final = sum(ENTRY_USD * (1.0 + hodl[t] / 100.0) for t in hset)
    hodl_invested = ENTRY_USD * len(hset)
    return {"n": len(rows), "invested": invested, "final": final, "pnl": pnl,
            "return_pct": (pnl / invested * 100.0) if invested else 0.0,
            "hodl_final": hodl_final, "hodl_n": len(hset),
            "hodl_return_pct": ((hodl_final - hodl_invested) / hodl_invested * 100.0) if hodl_invested else None,
            "beats_hodl": final > hodl_final if hset else None,
            "rows": rows[DETAIL_COLS].reset_index(drop=True)}


def go(stage: str) -> None:
    st.session_state.stage = stage


def select_method() -> None:
    """Commit the picker's choice to a plain key that survives stages the selectbox isn't rendered on
    (Streamlit clears widget-keyed state once its widget stops being drawn)."""
    st.session_state.method = st.session_state.method_sel


def toggle(ticker: str) -> None:
    basket = st.session_state.basket
    if ticker in basket:
        basket.discard(ticker)
    else:
        basket.add(ticker)


def stage_start(noun: str, start_s: str) -> None:
    st.title("ML Basket Simulator — XGBoost & LSTM")
    st.header(f"It is {start_s}")
    st.write(f"This is the first OOS day. The {noun} models are already trained.")
    st.button("Start", type="primary", on_click=go, args=("pick",))


def stage_pick(df: pd.DataFrame, noun: str) -> None:
    st.selectbox("Model", METHOD_NAMES, key="method_sel",
                 index=METHOD_NAMES.index(st.session_state.method), on_change=select_method,
                 help="Which trained model's sealed OOS results the basket is computed from. "
                      "XGBoost (1h multi-timeframe) is the default; LSTM is the daily recurrent net.")
    st.subheader("Pick your basket. Every ticker = $1000 entry.")
    n = len(st.session_state.basket)
    st.caption(f"{noun} · {len(df)} tickers with a precomputed OOS result · "
               f"selected: {n} · to invest: {ENTRY_USD * n:,.0f} USD")
    with st.container(height=560):
        tickers = df["ticker"].tolist()
        for i in range(0, len(tickers), GRID_COLS):
            cols = st.columns(GRID_COLS)
            for col, tk in zip(cols, tickers[i:i + GRID_COLS]):
                col.button(tk, key=f"tk_{tk.replace('.', '_')}",
                           type="primary" if tk in st.session_state.basket else "secondary",
                           on_click=toggle, args=(tk,), width="stretch")
    st.button("Calculate basket", type="primary", disabled=(n == 0),
              on_click=go, args=("calc",))
    st.caption("Read-only demo: no training at runtime — only precomputed OOS results "
               "are read. Fixed OOS window; every asset starts from the same $1000; "
               "tickers without an OOS row are not shown.")


def stage_calc(noun: str) -> None:
    with st.spinner(f"Calculating your {noun} basket..."):
        time.sleep(CALC_SECONDS)                 # theatrical pause; nothing computes
    st.session_state.stage = "result"
    st.rerun()


def stage_result(df: pd.DataFrame, noun: str, feed: Path, start_s: str, end_s: str, days: int) -> None:
    r = compute_basket(sorted(st.session_state.basket), df, feed)
    st.header(f"Now it is {days} days later")
    st.write(f"Date: {end_s}")
    st.title(f"Your {noun} basket result is: {r['final']:,.2f} USD")
    st.write(f"From invested: 1000 USD x {r['n']} assets = {r['invested']:,.0f} USD")
    st.write(f"Period: {start_s} -> {end_s} ({days} days)")
    c1, c2 = st.columns(2)
    c1.metric(f"{noun} strategy", f"{r['return_pct']:+.2f}%", delta=f"{r['pnl']:+,.2f} USD")
    if r["hodl_return_pct"] is not None:
        hodl_pnl = r["hodl_final"] - ENTRY_USD * r["hodl_n"]
        c2.metric("Buy & hold (same basket)", f"{r['hodl_return_pct']:+.2f}%",
                  delta=f"{hodl_pnl:+,.2f} USD")
        verdict = "**beat**" if r["beats_hodl"] else "did **not** beat"
        st.caption(f"Over {start_s}→{end_s} (a strong bull market) the {noun} basket {verdict} simply "
                   f"buying & holding the same tickers. The OOS window is read once and never "
                   f"optimized — this comparison is honest, not curated.")
    st.subheader("Per-asset detail")
    st.dataframe(r["rows"], hide_index=True, width="stretch",
                 column_config={
                     "end_capital": st.column_config.NumberColumn("End capital (USD)", format="%.2f"),
                     "return_pct": st.column_config.NumberColumn("Return %", format="%.2f"),
                     "max_drawdown_pct": st.column_config.NumberColumn("Max DD %", format="%.2f"),
                     "win_rate_pct": st.column_config.NumberColumn("Win rate %", format="%.2f"),
                     "profit_factor": st.column_config.NumberColumn("Profit factor", format="%.2f"),
                 })
    st.button("Pick again", on_click=go, args=("pick",))


st.set_page_config(page_title="ML Basket Simulator — XGBoost & LSTM", layout="wide")

# Two modes share one app: the sealed basket demo (default) and the WO-FS feature-selection study.
# The study reads only fs/artifacts and never touches the sealed stores this simulator reads.
MODE_BASKET = "Basket Simulator"
MODE_STUDY = "Studium selekcji cech (WO-FS)"
st.session_state.setdefault("app_mode", MODE_BASKET)


def _select_mode():
    st.session_state.app_mode = st.session_state.app_mode_sel


st.sidebar.radio("Tryb", [MODE_BASKET, MODE_STUDY], key="app_mode_sel",
                 index=[MODE_BASKET, MODE_STUDY].index(st.session_state.app_mode),
                 on_change=_select_mode)
if st.session_state.app_mode == MODE_STUDY:
    from fs import app_pages
    app_pages.render()
    st.stop()

st.markdown(GRID_CSS, unsafe_allow_html=True)
st.session_state.setdefault("stage", "start")
st.session_state.setdefault("basket", set())
st.session_state.setdefault("method", METHOD_NAMES[0])          # default: XGBoost

cfg = METHODS[st.session_state.method]
noun = cfg["noun"]
with st.sidebar:
    st.markdown(cfg["blurb"])

df = load_metrics(cfg["db"])
if df.empty:
    st.error(f"No OOS results found for {noun} in {cfg['db']}. This repo ships the sealed results, so "
             "this only happens if the store was cleared — regenerate: make run-asset TICKER=AAPL.")
    st.stop()

st.session_state.basket &= set(df["ticker"])                   # keep the basket valid for this method
start_s, end_s, days = parse_window(str(df["oos_window"].iat[0]))

{"start": lambda: stage_start(noun, start_s),
 "pick": lambda: stage_pick(df, noun),
 "calc": lambda: stage_calc(noun),
 "result": lambda: stage_result(df, noun, cfg["feed"], start_s, end_s, days),
}[st.session_state.stage]()

#!/usr/bin/env python3
"""ML Basket Simulator — read-only Streamlit demo over oos_metrics.db.

Pick tickers (each = $1000 entry on the first OOS day) and see what the basket
became by the end of the fixed OOS window. NOTHING runs at runtime: no
retraining, no trading — the app only reads the precomputed per-asset OOS rows
from oos_metrics.db (opened read-only, so the live search worker is never
disturbed). Tickers without an OOS row simply do not appear in the picker.

Run:  make app    (or from the repo root: streamlit run Project/Structure/app.py)
"""
import sqlite3
import time
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st

HERE = Path(__file__).resolve().parent
DB = HERE / "oos_metrics.db"
ENTRY_USD = 1000.0
GRID_COLS = 10
CALC_SECONDS = 1.5
DETAIL_COLS = ["ticker", "end_capital", "return_pct", "trades",
               "max_drawdown_pct", "win_rate_pct", "profit_factor"]

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
def load_metrics() -> pd.DataFrame:
    """All oos_metrics rows, ticker-sorted. Empty frame on any miss (absent file,
    table not created yet, transient lock) — the caller fails soft."""
    if not DB.exists():
        return pd.DataFrame()
    try:
        con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, timeout=5.0)
        try:
            return pd.read_sql_query("select * from oos_metrics order by ticker", con)
        finally:
            con.close()
    except (sqlite3.Error, pd.errors.DatabaseError):
        return pd.DataFrame()


def parse_window(window: str) -> tuple[str, str, int]:
    """'2024-01-02 -> 2026-05-29' -> ('2024-01-02', '2026-05-29', 878)."""
    start_s, end_s = (s.strip() for s in window.split("->"))
    return start_s, end_s, (date.fromisoformat(end_s) - date.fromisoformat(start_s)).days


def compute_basket(selected: list, df: pd.DataFrame) -> dict:
    """Basket outcome from the precomputed per-asset rows; invested derives from
    the matched rows so the numbers stay internally consistent."""
    rows = df[df["ticker"].isin(selected)]
    invested = ENTRY_USD * len(rows)
    final = float(rows["end_capital"].sum())
    pnl = final - invested
    return {"n": len(rows), "invested": invested, "final": final, "pnl": pnl,
            "return_pct": (pnl / invested * 100.0) if invested else 0.0,
            "rows": rows[DETAIL_COLS].reset_index(drop=True)}


def go(stage: str) -> None:
    st.session_state.stage = stage


def toggle(ticker: str) -> None:
    basket = st.session_state.basket
    if ticker in basket:
        basket.discard(ticker)
    else:
        basket.add(ticker)


def stage_start(start_s: str) -> None:
    st.title("ML Basket Simulator")
    st.header(f"It is {start_s}")
    st.write("This is the first OOS day. The ML model is already trained.")
    st.button("Start", type="primary", on_click=go, args=("pick",))


def stage_pick(df: pd.DataFrame) -> None:
    st.subheader("Pick your basket. Every ticker = $1000 entry.")
    n = len(st.session_state.basket)
    st.caption(f"{len(df)} tickers with a precomputed OOS result · "
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
    st.caption("Read-only demo: no retraining at runtime — only precomputed OOS "
               "results are read. Fixed OOS window; every asset starts from the "
               "same $1000; tickers without an OOS row are not shown.")


def stage_calc() -> None:
    with st.spinner("Calculating your ML basket..."):
        time.sleep(CALC_SECONDS)                 # theatrical pause; nothing computes
    st.session_state.stage = "result"
    st.rerun()


def stage_result(df: pd.DataFrame, start_s: str, end_s: str, days: int) -> None:
    r = compute_basket(sorted(st.session_state.basket), df)
    st.header(f"Now it is {days} days later")
    st.write(f"Date: {end_s}")
    st.title(f"Your basket result is: {r['final']:,.2f} USD")
    st.write(f"From invested: 1000 USD x {r['n']} assets = {r['invested']:,.0f} USD")
    st.write(f"Period: {start_s} -> {end_s} ({days} days)")
    st.metric("Total return", f"{r['return_pct']:+.2f}%", delta=f"{r['pnl']:+,.2f} USD")
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


st.set_page_config(page_title="ML Basket Simulator", layout="wide")
st.markdown(GRID_CSS, unsafe_allow_html=True)
st.session_state.setdefault("stage", "start")
st.session_state.setdefault("basket", set())

df = load_metrics()
if df.empty:
    st.error("No OOS results yet: Project/Structure/oos_metrics.db is missing or empty "
             "(the file is git-ignored). Produce it first: make run-asset TICKER=AAPL, "
             "or let the feature-search loop fill it.")
    st.stop()

start_s, end_s, days = parse_window(str(df["oos_window"].iat[0]))

{"start": lambda: stage_start(start_s),
 "pick": lambda: stage_pick(df),
 "calc": stage_calc,
 "result": lambda: stage_result(df, start_s, end_s, days),
}[st.session_state.stage]()

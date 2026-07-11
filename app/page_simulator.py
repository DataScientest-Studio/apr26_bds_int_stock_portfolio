"""Basket Simulator (Track B — sealed tier): the stage-machine demo over the two sealed OOS stores,
extended with rule-based PRESET PACKAGES (the parent project's questionnaire -> profile -> selection
rule), computed on strictly pre-OOS inputs so the displayed sealed results stay honest one-shot reads.
"""
import time

import pandas as pd
import streamlit as st

from common import (ENTRY_USD, METHOD_NAMES, METHODS, load_hodl, load_metrics,
                    load_preoos_inputs, load_tickers, parse_window, track_a_badge)
from package_builder import (PROFILE_CONFIG, build_package,
                             risk_answers_to_recommendation_defaults)

GRID_COLS = 10
CALC_SECONDS = 1.5
DETAIL_COLS = ["ticker", "end_capital", "return_pct", "trades",
               "max_drawdown_pct", "win_rate_pct", "profit_factor"]

PRESET_MANUAL = "None (pick manually)"
PRESET_QUESTIONNAIRE = "From my risk profile"
PRESET_NAMES = [PRESET_MANUAL, "Conservative", "Balanced", "Aggressive", PRESET_QUESTIONNAIRE]

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


def compute_basket(selected: list, df: pd.DataFrame, feed) -> dict:
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


def package_pool(df: pd.DataFrame) -> pd.DataFrame:
    """The preset rule's candidate pool for the CURRENT method: sealed Train-CV score (cv_auc_pr)
    x pre-OOS risk inputs x static sector — every column knowable before the OOS window."""
    pre = load_preoos_inputs()
    meta = load_tickers()[["ticker", "sector", "industry"]]
    pool = (df[["ticker", "cv_auc_pr"]]
            .merge(pre[["ticker", "volatility_60d", "ret_60d"]], on="ticker", how="inner")
            .merge(meta, on="ticker", how="left"))
    pool["sector"] = pool["sector"].fillna("Unknown")
    return pool


def go(stage: str) -> None:
    st.session_state.stage = stage


def select_method() -> None:
    """Commit the picker's choice to a plain key that survives stages the selectbox isn't rendered on
    (Streamlit clears widget-keyed state once its widget stops being drawn)."""
    st.session_state.method = st.session_state.method_sel


def select_preset() -> None:
    st.session_state.preset = st.session_state.preset_sel


def toggle(ticker: str) -> None:
    basket = st.session_state.basket
    if ticker in basket:
        basket.discard(ticker)
    else:
        basket.add(ticker)


def apply_preset(df: pd.DataFrame) -> None:
    """Build the preset package for the chosen profile and pre-select it in the grid. The rule and
    its inputs are fixed ex-ante (parent project's rule, pre-OOS data) — never tuned against the
    displayed outcomes."""
    preset = st.session_state.preset
    if preset == PRESET_QUESTIONNAIRE:
        prefs = risk_answers_to_recommendation_defaults(st.session_state.get("risk_answers"))
    else:
        prefs = risk_answers_to_recommendation_defaults(None)
        prefs["profile"] = preset
        prefs["max_volatility_60d"] = PROFILE_CONFIG[preset]["max_volatility_60d"]
        if preset == "Conservative":
            prefs["ranking_objective"] = "Smoother ride"
        elif preset == "Aggressive":
            prefs["ranking_objective"] = "Highest expected return"
        else:
            prefs["ranking_objective"] = "Risk-adjusted return"
    selected, _, relaxed = build_package(
        pool=package_pool(df),
        portfolio_size=prefs["portfolio_size"],
        max_volatility_60d=prefs["max_volatility_60d"],
        max_sector_weight=prefs["max_sector_weight_pct"] / 100,
        excluded_sectors=prefs["excluded_sectors"],
        min_recent_return=prefs["min_recent_return_pct"] / 100,
        ranking_objective=prefs["ranking_objective"],
    )
    st.session_state.basket = set(selected["ticker"]) if not selected.empty else set()
    st.session_state.preset_result = {
        "profile": prefs["profile"], "objective": prefs["ranking_objective"],
        "relaxed": relaxed, "table": selected, "preset": preset,
    }


def render_preset_controls(df: pd.DataFrame) -> None:
    with st.expander("Preset package — pick a whole basket by rule (no cherry-picking)", expanded=False):
        st.markdown(
            "The parent project's portfolio rule (greedy pick, max sector share, volatility cap per "
            "risk profile, relax-only-the-vol-cap if underfilled), applied to **pre-OOS inputs only**: "
            "the Train-CV score `cv_auc_pr` sealed in each row, volatility and momentum as of "
            "**2023-12-29** (the last Train session), and static sector metadata. The parent's "
            "predicted-return rankings are dated at the *end* of the OOS window, so using them here "
            "would be look-ahead — they are not used."
        )
        c1, c2 = st.columns([2, 1])
        c1.selectbox("Preset", PRESET_NAMES, key="preset_sel",
                     index=PRESET_NAMES.index(st.session_state.preset), on_change=select_preset,
                     help="Conservative / Balanced / Aggressive use the parent's volatility caps "
                          "(0.35 / 0.50 / 0.80 annualized). 'From my risk profile' maps your "
                          "questionnaire answers (Risk Profile page) to profile, size and exclusions.")
        needs_form = (st.session_state.preset == PRESET_QUESTIONNAIRE
                      and not st.session_state.get("risk_answers"))
        if needs_form:
            st.info("Fill in the **Risk Profile** page first — this preset maps your answers.")
        c2.button("Apply preset", type="primary",
                  disabled=(st.session_state.preset == PRESET_MANUAL or needs_form),
                  on_click=apply_preset, args=(df,))
        pr = st.session_state.get("preset_result")
        if pr and pr["preset"] == st.session_state.preset and not pr["table"].empty:
            t = pr["table"]
            st.caption(f"Package: **{pr['profile']}** profile · objective *{pr['objective']}* · "
                       f"{len(t)} tickers, {t['sector'].nunique()} sectors"
                       + (" · **volatility cap relaxed** (not enough eligible names)" if pr["relaxed"] else ""))
            st.dataframe(
                t[["rank", "ticker", "sector", "cv_auc_pr", "volatility_60d", "ret_60d", "sector_weight"]],
                hide_index=True, width="stretch",
                column_config={
                    "cv_auc_pr": st.column_config.NumberColumn("Train-CV AUC-PR", format="%.3f"),
                    "volatility_60d": st.column_config.NumberColumn("Vol (pre-OOS, ann.)", format="%.2f"),
                    "ret_60d": st.column_config.NumberColumn("60d ret (pre-OOS)", format="%.2%"),
                    "sector_weight": st.column_config.NumberColumn("Sector weight", format="%.0%"),
                })
            st.caption("Illustrative application of a rule fixed ex-ante in the parent project. The "
                       "sealed OOS rows were published before this rule was ported, so treat the basket "
                       "total as an honest read under a fixed rule — not as a new out-of-sample claim.")


def stage_start(noun: str, start_s: str) -> None:
    st.header(f"It is {start_s}")
    st.write(f"This is the first OOS day. The {noun} models are already trained.")
    st.button("Start", type="primary", on_click=go, args=("pick",))


def stage_pick(df: pd.DataFrame, noun: str) -> None:
    st.selectbox("Model", METHOD_NAMES, key="method_sel",
                 index=METHOD_NAMES.index(st.session_state.method), on_change=select_method,
                 help="Which trained model's sealed OOS results the basket is computed from. "
                      "XGBoost (1h multi-timeframe) is the default; LSTM is the daily recurrent net.")
    render_preset_controls(df)
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


def stage_result(df: pd.DataFrame, noun: str, feed, start_s: str, end_s: str, days: int) -> None:
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


def render() -> None:
    st.title("ML Basket Simulator — XGBoost & LSTM")
    track_a_badge()
    st.markdown(GRID_CSS, unsafe_allow_html=True)
    st.session_state.setdefault("stage", "start")
    st.session_state.setdefault("basket", set())
    st.session_state.setdefault("method", METHOD_NAMES[0])          # default: XGBoost
    st.session_state.setdefault("preset", PRESET_MANUAL)

    cfg = METHODS[st.session_state.method]
    noun = cfg["noun"]
    with st.sidebar:
        st.markdown(cfg["blurb"])

    df = load_metrics(cfg["db"])
    if df.empty:
        st.error(f"No OOS results found for {noun} in {cfg['db']}. This repo ships the sealed results, "
                 "so this only happens if the store was cleared — regenerate: make run-asset TICKER=AAPL.")
        st.stop()

    st.session_state.basket &= set(df["ticker"])                   # keep the basket valid for this method
    start_s, end_s, days = parse_window(str(df["oos_window"].iat[0]))

    {"start": lambda: stage_start(noun, start_s),
     "pick": lambda: stage_pick(df, noun),
     "calc": lambda: stage_calc(noun),
     "result": lambda: stage_result(df, noun, cfg["feed"], start_s, end_s, days),
     }[st.session_state.stage]()

"""Project Report: the unified two-track narrative — what was built, how each track is evaluated,
and the honest verdicts. This page is the app-side counterpart of docs/UNIFIED_APP.md.
"""
import pandas as pd
import streamlit as st

from common import METHODS, load_metrics, parse_window, track_a_badge, track_b_badge

LADDER = pd.DataFrame([
    {"Dimension": "Question asked",
     "Track A — sealed pipelines": "Will THIS proposed trade on this asset net positive?",
     "Track B — ranking recommender": "Which stocks rank best on 63-day forward return?"},
    {"Dimension": "Label / target",
     "Track A — sealed pipelines": "Triple-Barrier (TP 2×ATR / SL 1×ATR), Y = net>0 after costs",
     "Track B — ranking recommender": "Continuous 63-trading-day forward return (regression)"},
    {"Dimension": "Models",
     "Track A — sealed pipelines": "XGBoost (1h, multi-timeframe) and LSTM (daily), per asset",
     "Track B — ranking recommender": "Ridge / RF / RF-no-history (selected) / XGBoost / PyTorch MLP"},
    {"Dimension": "Validation",
     "Track A — sealed pipelines": "Purged + embargoed walk-forward CV; ONE-SHOT OOS 2024→2026 read once",
     "Track B — ranking recommender": "Fixed split + 13-fold walk-forward WITHOUT purge/embargo"},
    {"Dimension": "Costs & sizing",
     "Track A — sealed pipelines": "1bp fee + 2bp slippage per side; generalized Kelly",
     "Track B — ranking recommender": "Gross returns; equal-weight top-N; no execution model"},
    {"Dimension": "Benchmark",
     "Track A — sealed pipelines": "Per-asset buy & hold over the same OOS window",
     "Track B — ranking recommender": "Universe average forward return per fold"},
    {"Dimension": "Result status",
     "Track A — sealed pipelines": "Realized, sealed, byte-reproducible (make verify-*)",
     "Track B — ranking recommender": "Exploratory; package returns are model predictions"},
])


def render() -> None:
    st.title("Project Report — one app, two evaluation tiers")
    st.write(
        "This application unifies two research tracks of the same S&P 500 project. They answer "
        "different questions under **different standards of evidence**, so the app keeps them on "
        "separate pages with permanent tier badges — numbers from the two tracks are never shown "
        "in one results table."
    )
    track_a_badge()
    track_b_badge()

    st.subheader("The methodology ladder")
    st.dataframe(LADDER, hide_index=True, width="stretch")

    st.subheader("What each track concluded — honestly")
    a, b = st.columns(2)
    with a:
        st.markdown("#### Track A (sealed)")
        for name, cfg in METHODS.items():
            df = load_metrics(cfg["db"])
            if df.empty:
                continue
            start_s, end_s, _ = parse_window(str(df["oos_window"].iat[0]))
            beat = None
            try:
                import json
                feed = json.loads(cfg["feed"].read_text(encoding="utf-8"))["assets"]
                flags = [x.get("beats_hodl") for x in feed if x.get("beats_hodl") is not None]
                beat = f"{sum(flags)}/{len(flags)}" if flags else None
            except (OSError, ValueError, KeyError):
                pass
            st.markdown(
                f"- **{name}** — {len(df)} assets, OOS {start_s} → {end_s}, median profit factor "
                f"{df['profit_factor'].median():.2f}"
                + (f", beats buy & hold on {beat} assets" if beat else "") + "."
            )
        st.markdown(
            "**Verdict:** the strategy-v2 levers did **not** beat the prior baseline over the full "
            "universe (a small dev sample had flattered them), and in a strong bull OOS most assets "
            "do not beat buy & hold. What the track demonstrates is the **method**: leak-free labels, "
            "purged validation, profit-aligned selection, honest one-shot OOS, byte-reproducibility. "
            "A negative, trustworthy answer — reported as-is."
        )
    with b:
        st.markdown("#### Track B (exploratory)")
        st.markdown(
            "- Five model families compared on one fixed split; **Ridge** actually won the fixed-split "
            "metrics; the practical recommender uses **RF without `history_days`** (a shortcut feature "
            "found and removed — a genuine leakage catch).\n"
            "- Walk-forward: rank correlation drops from 0.16 (fixed split) to **≈ 0.06** — an in-project "
            "demonstration that single splits flatter.\n"
            "- Deep learning (PyTorch MLP) was tested and honestly rejected (negative rank correlation).\n"
            "- The questionnaire → profile → package layer produces sensible, diversified baskets — its "
            "'expected returns' are **model predictions, not backtests**."
        )
        st.markdown(
            "**Verdict:** a weak-but-positive, *exploratory* ranking signal under a lenient evaluation "
            "standard (no purge, gross, overlapping labels). Presented for what it is; its selection "
            "*rules* (risk profiles, sector caps) are sound and are reused on the sealed tier with "
            "strictly pre-OOS inputs."
        )

    st.subheader("How the tracks are connected — without cheating")
    st.markdown(
        """
The bridge between the tracks is the **portfolio rule, not the model scores**:

1. The **Risk Profile** questionnaire maps your answers to a profile (additive score → Conservative /
   Balanced / Aggressive), a portfolio size and sector exclusions — identical mapping on both tracks.
2. On **Track B** the rule ranks by the RF's predicted 63-day return — a *prediction*, shown as such.
3. On **Track A** the same rule builds preset packages from **pre-OOS inputs only** — the Train-CV
   score sealed in each row, volatility/momentum as of 2023-12-29, and static sector data. The
   parent's prediction rankings are dated at the **end** of the sealed OOS window, so using them
   there would be look-ahead; they are not used.

That way the *design* (one form, one rule, three risk profiles) is coherent across the whole app,
while every displayed number keeps its own evaluation tier.
        """
    )
    st.caption("Full write-up: docs/UNIFIED_APP.md · Track-A internals: docs/PROJECT_STATE.md · "
               "reproduce: make verify-xgb / make verify-lstm.")

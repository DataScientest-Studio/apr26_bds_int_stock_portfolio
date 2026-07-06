"""Risk Profile page: the parent project's 9-question investor questionnaire (ported 1:1).

Submitting stores the answers in st.session_state["risk_answers"]; both downstream consumers
(the Track-B Recommender's preference controls and the Track-A simulator's preset packages)
prefill from that one dict — the same score -> profile mapping either way.
"""
import streamlit as st

from package_builder import PROFILE_CONFIG, risk_answers_to_recommendation_defaults
from risk_assessment import render_questionnaire


def render() -> None:
    st.title("Risk Profile")
    st.write(
        "Answer the questions below so the app can match portfolios to your risk profile. "
        "After submitting, both the **Recommender (Track B)** preference controls and the "
        "**Basket Simulator (Track A)** preset packages are prefilled from these answers."
    )
    result = render_questionnaire()
    if result:
        st.success("Thanks — your answers were recorded for this session.")
        defaults = risk_answers_to_recommendation_defaults(result)
        profile = defaults["profile"]
        c1, c2, c3 = st.columns(3)
        c1.metric("Mapped profile", profile,
                  help="An additive score over experience, horizon, loss tolerance, drawdown reaction "
                       "and goal maps to Conservative (score ≤ −3), Aggressive (≥ +3) or Balanced.")
        c2.metric("Volatility cap", f"{defaults['max_volatility_60d']:.2f}",
                  help="The profile's annualized 60-day volatility cap "
                       "(Conservative 0.35 / Balanced 0.50 / Aggressive 0.80).")
        c3.metric("Portfolio size", f"{defaults['portfolio_size']}",
                  help="From your position-count answer: Few → 3, Moderate → 7, Fully diversified → 10.")
        st.caption(PROFILE_CONFIG[profile]["description"])
        with st.expander("Your recorded answers"):
            st.write(result)

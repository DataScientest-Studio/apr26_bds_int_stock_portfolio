"""Final Presentation: the running order for the live defense, four owned segments.

Segment 1 (Introduction, owner G) is fully built as a ~5-minute presenter aid: the problem, the
original brief, the approach at a glance, what we delivered, and the progress milestones — with
visuals drawn from committed report figures. It deliberately does NOT explain the algorithms; the
modelling detail is covered in the ML Part 1 / Part 2 segments that follow.

The remaining three segments stay as placeholders until their owners fill them in.
"""
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent.parent          # repo root (parent of app/)

# committed report figures reused as presentation visuals
FIG_RISK_RETURN = ROOT / "reports" / "figures" / "06_risk_return.png"
FIG_PIPELINE = ROOT / "reports" / "figures" / "13_trackb_pipeline_overview.png"
FIG_FUNNEL = ROOT / "reports" / "figures" / "12_trackb_portfolio_funnel.png"
FIG_APP = ROOT / "mac-2026-06-09-full-6y" / "report_assets" / "01_recommendation.png"


def _img(path: Path, caption: str, width="stretch") -> None:
    """Render a figure if present; never break the slide if an asset is missing."""
    if path.is_file():
        st.image(str(path), caption=caption, width=width)
    else:
        st.warning(f"Missing figure: {path.relative_to(ROOT)}")


def _introduction() -> None:
    st.title("Introduction")
    st.caption("Sets up the problem and what we built — the modelling detail comes in the ML segments.")

    # ── 1. The problem ────────────────────────────────────────────────────────
    st.header("1  The problem — where does a beginner even start?")
    left, right = st.columns([5, 6], gap="large")
    with left:
        st.markdown(
            """
- A retail investor who wants to pick **individual stocks** faces **~500 names** in the S&P 500
  alone — and no idea where to begin.
- Existing tools either lump everyone into a generic *"aggressive / moderate / conservative"* bucket,
  or assume you already **speak the language of finance**.
- Every dot on the right is one S&P 500 stock, placed by **risk vs. return** — hundreds of choices,
  wildly different profiles, one decision to make.
- **How each dot is placed:** only from a stock's **past daily prices** — average return on one axis,
  how much it swings (**risk**) on the other. No forecasts, just history.
- **The lone dot top-right (<a href="/app/static/SNDK.txt" target="_blank" rel="noopener">SNDK</a>) is
  a data lesson, not a great stock:** it shows ~343% return, but it's a **recent entrant** (history
  starts 2025-02-13, ~1.3 years) — measuring a short, steep run over-inflates it.
- **So data quality isn't uniform:** that outlier broke our assumption that all 503 tickers have
  equal-quality history — we now track **per-ticker history length**.
            """,
            unsafe_allow_html=True,
        )
    with right:
        _img(FIG_RISK_RETURN, "503 S&P 500 stocks by annualized risk vs. return — the choice-overload problem")

    st.divider()

    # ── 2. The original brief ─────────────────────────────────────────────────
    st.header("2  The original brief")
    b1, b2 = st.columns(2, gap="large")
    with b1:
        st.markdown(
            """
**Goal.** A beginner-friendly **stock portfolio recommender**: a short questionnaire about the
investor →  a small portfolio of **5–10 stocks**, each shown with the **risk metrics that justify
the pick**.

**Guardrails set up front**
- Universe: **S&P 500** (~503 tickers).
- **Price-only** by design — no fundamentals, no paid feeds.
- **No single sector > 30%** of the portfolio.
- Decision *support* for a beginner — **not** financial advice.
            """
        )
    with b2:
        st.markdown(
            """
**The setup**
- Course: *Data Scientist* · difficulty **8/10** · mentor **Paul Grolier**.
- Data source: **Alpaca** free IEX feed — daily OHLCV, S&P 500, ~5–6 years of history
  (yfinance kept only as a cross-check).
- Deliverables: EDA report → modelling report → final report → **Streamlit app + oral defense**.
            """
        )

    st.caption("Scope tightened early, stated up front: **S&P 500 only** (Alpaca's free feed has no "
               "DAX 40), and the original **clustering** step gave way to **direct ranking**.")

    st.divider()

    # ── 3. The approach at a glance ───────────────────────────────────────────
    st.header("3  The approach at a glance")
    st.markdown(
        "One time-respecting pipeline: **raw prices → engineered features → chronological split → "
        "model → ranked predictions → a diversified portfolio.** *(The modelling steps are covered "
        "in the ML segments — here it's just the shape.)*"
    )
    _, mid, _ = st.columns([1, 5, 1])
    with mid:
        _img(FIG_PIPELINE, "From raw prices to a beginner-friendly portfolio — the end-to-end shape")
    st.markdown(
        "That same shape runs **twice**, at **two levels of rigour** — the reason why is the next slide."
    )

    st.divider()

    # ── 4. What we delivered ──────────────────────────────────────────────────
    st.header("4  What we delivered")
    d1, d2 = st.columns([6, 5], gap="large")
    with d1:
        _img(FIG_APP, "The recommender — questionnaire in, justified portfolio out")
    with d2:
        st.markdown(
            """
- **One unified multi-page Streamlit app** — from raw data all the way to an interactive,
  justified recommendation.
- We went **beyond the original single-model brief** into **two evaluation tiers**:
  - an **exploratory** ranking recommender (the original questionnaire → portfolio), and
  - a **sealed** pipeline validated under a stricter standard of evidence — where the **method**, not
    a market-beating result, is the deliverable.
- Every number carries a **tier badge**; the two tiers never share a results table.
- Reproducible end to end: the sealed results re-run **byte-for-byte**.
            """
        )

    st.divider()

    # ── 5. What's next in this talk ───────────────────────────────────────────
    st.header("5  Agenda")
    st.markdown(
        """
Parts 1 & 2 walk the modelling **behind both tiers**; the Conclusion gives the **verdict** on each.

- **Machine Learning — Part 1 (M):** the data, features and first models.
- **Machine Learning — Part 2 (P):** validation, model comparison, results.
- **Conclusion (T):** the verdict, limitations stated openly, and next steps.
        """
    )


def _conclusion() -> None:
    st.header("Conclusion")
    st.markdown(
        """
- **Scope evolved, on purpose:** we first considered **yfinance** for data but chose **Alpaca**'s
  feed instead; clustering gave way to supervised models, and the 12-month target to
  **63 trading days** — 5–6 years of history can't validate a yearly horizon.
- **Recommender — weak signal, simple wins:** walk-forward rank correlation ≈ **0.06** (≈ 0.16 on a
  single split); **Ridge beat the fancier models**, and a deep-learning model was tested, not selected.
- **Biggest lesson — don't trust one test:** checked on a single slice of data the model looked
  okay (0.16), but testing it across **many time periods** dropped the score to **0.06** — much weaker.
- **Data quality isn't uniform:** new entrants like SNDK have short, ragged histories — we now track
  per-ticker history instead of assuming a clean panel.
        """
    )


_PLACEHOLDERS = [
    ("Machine Learning — Part 1", "M", "First half of the modelling story."),
    ("Machine Learning — Part 2", "P", "Second half of the modelling story."),
]


def render() -> None:
    _introduction()

    st.divider()
    st.header("Machine Learning segments")
    st.caption("Owned by M and P — still placeholders; drafted by their owners.")
    for i, (title, owner, hint) in enumerate(_PLACEHOLDERS, start=2):
        st.subheader(f"{i}. {title}  ·  ({owner})")
        st.info(f"🚧 Placeholder — owned by **{owner}**. {hint}")

    st.divider()
    _conclusion()

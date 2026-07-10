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
- Every dot on the right is one S&P 500 stock, placed by **risk vs. return**. The cloud is the
  problem: hundreds of choices, wildly different profiles, one decision to make.
            """
        )
    with right:
        _img(FIG_RISK_RETURN, "503 S&P 500 stocks by annualized risk vs. return — the choice-overload problem")

    with st.expander("📐 How each dot is placed — the risk/return recipe"):
        st.markdown(
            """
Every dot is **one S&P 500 stock**, positioned from its own daily prices — no forecasts, just history.

1. **Daily return** = day-over-day % change of the **adjusted close** (splits & dividends already
   handled): `r_t = adj_close_t / adj_close_(t−1) − 1`.
2. For each stock, take the **mean** and the **standard deviation** of those daily returns over its
   full history.
3. **Y — annualized return** = mean daily return **× 252** (trading days in a year).
4. **X — annualized risk (volatility)** = std of daily return **× √252** — risk grows with the
   *square root* of time, return grows *linearly*.
5. The dashed cross-hairs are the **median** of each axis — the "typical" stock the cloud centers on.

*This is data preparation, not a model — the ML that ranks these stocks comes in the next segments.*
            """
        )

    with st.expander("💡 That lone dot top-right — SNDK — is a data lesson, not a great stock"):
        st.markdown(
            """
- <b><a href="/app/static/SNDK.txt" target="_blank" rel="noopener">SNDK (SanDisk)</a></b> sits at
  <b>~343% return / ~98% risk</b> — miles from every other name. It looks like the best stock in the
  index. It isn't. <i>(Click the ticker to open its raw price CSV — the very first row is its start date.)</i>
- It's a <b>recent S&P 500 entrant</b>: its price history starts only on <b>2025-02-13</b>, ~<b>320
  trading days (~1.3 years)</b> vs. a median of ~1,460 for everyone else.
- <b>Annualizing a short, steep run inflates both axes.</b> The outlier is an artifact of a
  <b>ragged / unbalanced panel</b>, not a real risk-return edge.
- <b>Why it matters here:</b> our mentor flagged it, and it broke our early assumption that <i>"all 503
  tickers have uniform data quality."</i> We now track <b>per-ticker history length</b> and handle new
  entrants explicitly — the kind of data-integrity habit this project is built on.
            """,
            unsafe_allow_html=True,
        )

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


_PLACEHOLDERS = [
    ("Machine Learning — Part 1", "M", "First half of the modelling story."),
    ("Machine Learning — Part 2", "P", "Second half of the modelling story."),
    ("Conclusion", "T", "Verdict, limitations stated openly, next steps."),
]


def render() -> None:
    _introduction()

    st.divider()
    st.header("Remaining segments")
    st.caption("Running order for the rest of the defense — one owner per segment. Placeholders for now.")
    for i, (title, owner, hint) in enumerate(_PLACEHOLDERS, start=2):
        st.subheader(f"{i}. {title}  ·  ({owner})")
        st.info(f"🚧 Placeholder — owned by **{owner}**. {hint}")

"""Data Explorer: the parent project's Exploration + 6 mentor-validated DataViz plots, recomputed
from the COMMITTED daily store (lstm/data/sp500_1d.duckdb, 2016->2026) + vendored GICS metadata.
Every plot keeps its "statistical validation" expander (a live pandas computation that proves the
visual claim). Headline numbers are computed from the data at render time — never hardcoded.

Honest note shown on the page: prices are RAW (corporate actions deferred), so a split appears as a
price cliff; these are descriptive plots and the conclusions (imbalance, fat tails, risk!=return)
are unaffected, but per-ticker total returns across a split are not economically meaningful.
"""
import pandas as pd
import streamlit as st

from common import load_bars, load_tickers
from plots import (get_price_line_summary, plot_correlation_heatmap, plot_price_line,
                   plot_return_hist, plot_risk_return_scatter, plot_sector_count,
                   plot_volume_box)

RAW_NOTE = ("Prices in this store are **raw** (corporate actions deferred): a stock split shows up "
            "as a price cliff (e.g. a 10:1 split looks like −90% in one day). The descriptive "
            "conclusions below do not depend on that; per-ticker *total return* across a split does — "
            "treat the line plot's total return as path arithmetic, not an investment result.")


def _exploration(tickers: pd.DataFrame, prices: pd.DataFrame) -> None:
    st.subheader("Exploration")
    st.write("First rows of the metadata table:")
    st.dataframe(tickers.head(10))
    st.write(f"Prices table shape: {prices.shape[0]:,} rows, {prices.shape[1]} columns "
             f"({prices['ticker'].nunique()} tickers, "
             f"{prices['date'].min().date()} → {prices['date'].max().date()})")
    st.write("Summary statistics on price columns:")
    st.dataframe(prices[["open", "high", "low", "close", "volume"]].describe())
    if st.checkbox("Show missing values"):
        st.dataframe(prices.isna().sum())


def _dataviz(tickers: pd.DataFrame, prices: pd.DataFrame) -> None:
    st.subheader("DataViz — 6 validated plots")

    st.markdown("**Plot 1 — countplot** (sector, categorical variable)")
    st.caption("Shows how many stocks sit in each sector — the universe is imbalanced, so a naïve "
               "picker would overweight the biggest sectors.")
    st.pyplot(plot_sector_count(tickers), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        st.markdown("**Validation method:** Raw data aggregation (`value_counts()`).\n\n"
                    "**Interpretation:** aggregating the metadata proves the visual imbalance. If a "
                    "recommender chose randomly, it would statistically favor the largest sectors "
                    "purely due to their count in the index — this validates the hard "
                    "max-share-per-sector business rule used by both package builders in this app.")
        st.dataframe(tickers["sector"].value_counts())

    st.markdown("**Plot 2 — boxplot** (mean daily volume per stock)")
    mean_volume = prices.groupby("ticker")["volume"].mean()
    st.caption(f"Y-axis = average shares traded per day (k = thousands). Red dashed line = median "
               f"(~{mean_volume.median() / 1000:.0f}k shares/day).")
    st.markdown(
        f"""
- **{prices['ticker'].nunique()} stocks, one average per name** — each point is the mean daily volume
  over all days in the store (not a single day).
- **Typical stock ~{mean_volume.median() / 1000:.0f}k shares/day** — half of the names trade less than
  the median; half trade more.
- **Middle 50% sit between ~{mean_volume.quantile(0.25) / 1000:.0f}k and
  ~{mean_volume.quantile(0.75) / 1000:.0f}k/day** — most names are in this band.
- **A few names dominate liquidity** — the dots above the whisker are the extreme mega-liquid names.
        """
    )
    st.pyplot(plot_volume_box(prices), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        st.markdown("**Validation method:** Descriptive statistics (`describe()`) on aggregated mean "
                    "daily volume.\n\n**Interpretation:** the exact percentiles below match the box; "
                    "the gap between the `75%` percentile and `max` statistically validates the "
                    "extreme outliers (the long upper whisker).")
        st.dataframe(mean_volume.describe())

    st.markdown("**Plot 3 — histplot** (daily returns)")
    returns = prices["daily_return"].dropna()
    st.caption("X-axis = % price change vs the previous day. Y-axis = how many days fall in each bin.")
    st.markdown(
        f"""
- **~{len(returns) / 1000:.0f}k daily returns** — one per stock per trading day (first day of each
  stock dropped: no "yesterday" to compare).
- **Typical day ≈ {returns.median() * 100:+.2f}%** — red dashed line (median); prices usually move
  very little in one session.
- **Most mass sits near 0%** — normal market behaviour.
- **Long tails left and right** — rare but real crashes and spikes; risk lives in those tails
  (raw-price splits also land here — see the note above).
- **Why it matters** — the average daily move is tiny but its spread (std ≈
  {returns.std() * 100:.1f}%/day) is large, so grouping stocks must use **risk**, not return alone.
        """
    )
    st.pyplot(plot_return_hist(prices), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        st.markdown("**Validation method:** Global descriptive statistics across all daily-return "
                    "observations.\n\n**Interpretation:** the median confirms a typical day is almost "
                    "flat; comparing `std` to `min`/`max` proves the fat tails — extreme events, "
                    "not daily noise, drive equity risk.")
        st.dataframe(returns.describe())

    st.markdown("**Plot 4 — lineplot** (price over time)")
    st.caption("Y-axis = raw close (USD). Use the dropdown to compare names over the same calendar.")
    ticker = st.selectbox("Choose a ticker", sorted(prices["ticker"].unique()))
    summary = get_price_line_summary(prices, ticker)
    if summary:
        st.markdown(
            f"""
- **{summary['n_days']:,} trading days** for **{ticker}**, from
  **{summary['start_date'].strftime('%Y-%m-%d')}** to **{summary['end_date'].strftime('%Y-%m-%d')}**.
- Starts at **{summary['start_price']:.2f} USD**, ends at **{summary['end_price']:.2f} USD** →
  **path total {summary['total_return_pct']:+.0f}%** (raw prices — a split distorts this number; see
  the note above).
- **Price path ≠ daily risk** — a smooth upward line can still have large daily volatility (Plot 3).
            """
        )
    st.pyplot(plot_price_line(prices, ticker), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        if summary:
            st.markdown("**Validation method:** Point-to-point percentage change calculation.\n\n"
                        "**Interpretation:** 'total return' is strictly a function of the first and "
                        "last close in the store — the equation below reproduces the title number "
                        "exactly.")
            st.code(f"({summary['end_price']:.2f} / {summary['start_price']:.2f} - 1) * 100 = "
                    f"{summary['total_return_pct']:.2f}%")

    st.markdown("**Plot 5 — heatmap** (Correlation Matrix)")
    st.caption("Pearson correlation between daily returns of the 10 most traded stocks.")
    st.markdown(
        """
- **Why correlation matters** — if all stocks in a portfolio move together (correlation near 1.0),
  the risk is concentrated: diversification is the core free lunch this checks.
- **Business value** — both package builders in this app cap the per-sector share specifically to
  avoid clusters of highly-correlated names.
        """
    )
    st.pyplot(plot_correlation_heatmap(prices), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        st.markdown("**Validation method:** Pearson correlation matrix on wide-format daily returns.\n\n"
                    "**Interpretation:** values near `1.0` = lockstep movement (poor diversification); "
                    "near `0.0` = independent movement. The matrix below is exactly what the heatmap "
                    "renders.")
        top_tickers = prices.groupby("ticker")["volume"].mean().nlargest(10).index
        data = prices[prices["ticker"].isin(top_tickers)]
        wide_returns = data.pivot(index="date", columns="ticker", values="daily_return").dropna()
        st.dataframe(wide_returns.corr())

    st.markdown("**Plot 6 — scatterplot** (Risk vs. Return)")
    st.caption("X-axis = annualized volatility (risk). Y-axis = annualized return. Each point = one stock.")
    st.markdown(
        """
- **What is 'risk' here?** — annualized volatility (std of daily returns × √252). In finance,
  volatility equates to uncertainty.
- **The core of the recommender** — some stocks offer higher returns for the same risk; others are
  volatile without the reward. That asymmetry is why grouping by risk profile is necessary.
- **Business value** — a conservative profile filters out the right side of this plot; an aggressive
  one may venture there for higher expected return.
        """
    )
    st.pyplot(plot_risk_return_scatter(prices), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        stats = prices.groupby("ticker")["daily_return"].agg(["mean", "std"]).dropna()
        pearson_corr = stats["mean"].corr(stats["std"])
        st.markdown("**Validation method:** Pearson correlation between per-stock volatility and "
                    "mean return.\n\n**Interpretation:** a strong positive correlation would mean "
                    "'more risk always equals more reward'.")
        st.write(f"**Calculated Pearson correlation:** `{pearson_corr:.4f}`")
        st.markdown(f"A correlation this close to 0 (`{pearson_corr:.4f}`) statistically validates the "
                    "scatterplot's message: blind risk does **not** guarantee proportionally higher "
                    "return — a smart selector must seek efficiency, not just risk.")


def render() -> None:
    st.title("Data Explorer")
    st.info(RAW_NOTE, icon="ℹ️")
    tickers = load_tickers()
    prices = load_bars()
    _exploration(tickers, prices)
    st.divider()
    _dataviz(tickers, prices)

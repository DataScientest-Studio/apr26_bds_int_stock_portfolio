"""Stocks Recommender Based on User Profile — Streamlit app.

Run:
    source .venv/bin/activate
    streamlit run app.py
"""

from __future__ import annotations

import math
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from src.data_loader import load_prices, load_tickers
from src.plots import (
    get_price_line_summary,
    plot_price_line,
    plot_return_hist,
    plot_sector_count,
    plot_volume_box,
    plot_risk_return_scatter,
    plot_correlation_heatmap,
)

st.set_page_config(page_title="Stocks Recommender Based on User Profile", layout="wide")
st.title("Stocks Recommender Based on User Profile")

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models"
BEST_MODEL_NAME = "Random Forest without history_days"
BEST_MODEL_KEY = "random_forest_no_history"
BEST_MODEL_RANKINGS_FILE = MODEL_DIR / "random_forest_no_history_latest_rankings.csv"
BEST_MODEL_METRICS_FILE = MODEL_DIR / "random_forest_no_history_metrics.csv"
WALK_FORWARD_SUMMARY_FILE = MODEL_DIR / "walk_forward_rf_no_history_summary.csv"
FEATURE_IMPORTANCE_FILE = MODEL_DIR / "random_forest_no_history_feature_importance.csv"
MODEL_METRIC_FILES = {
    "Ridge baseline": MODEL_DIR / "model_metrics.csv",
    "Random Forest": MODEL_DIR / "random_forest_metrics.csv",
    "Random Forest without history_days": MODEL_DIR / "random_forest_no_history_metrics.csv",
    "XGBoost without history_days": MODEL_DIR / "xgboost_no_history_metrics.csv",
    "ROCm PyTorch MLP": MODEL_DIR / "rocm_model_metrics.csv",
}

PROFILE_CONFIG = {
    "Conservative": {
        "max_volatility_60d": 0.35,
        "description": "Lower volatility first, with a stricter cap on jumpy stocks.",
    },
    "Balanced": {
        "max_volatility_60d": 0.50,
        "description": "Middle risk level with room for moderate volatility.",
    },
    "Aggressive": {
        "max_volatility_60d": 0.80,
        "description": "Higher risk tolerance when the model score is strong.",
    },
    "Custom": {
        "max_volatility_60d": 0.50,
        "description": "User-defined risk and diversification settings.",
    },
}


@st.cache_data
def get_data():
    tickers = load_tickers()
    prices = load_prices()
    return tickers, prices


@st.cache_data
def load_best_model_outputs():
    rankings = pd.read_csv(BEST_MODEL_RANKINGS_FILE, parse_dates=["date"])
    metrics = pd.read_csv(BEST_MODEL_METRICS_FILE)
    walk_forward = pd.read_csv(WALK_FORWARD_SUMMARY_FILE)
    feature_importance = pd.read_csv(FEATURE_IMPORTANCE_FILE)
    rankings = rankings.sort_values("predicted_63d_return", ascending=False).reset_index(drop=True)
    return rankings, metrics, walk_forward, feature_importance


@st.cache_data
def load_model_comparison_outputs():
    rows = []
    for display_name, path in MODEL_METRIC_FILES.items():
        metric = pd.read_csv(path).iloc[0].to_dict()
        metric["display_model"] = display_name
        rows.append(metric)

    comparison = pd.DataFrame(rows)
    comparison["is_selected_for_app"] = comparison["display_model"].eq(BEST_MODEL_NAME)
    comparison = comparison[
        [
            "display_model",
            "mae",
            "rmse",
            "spearman_rank_corr",
            "test_universe_avg_actual_return",
            "top5_avg_actual_return",
            "train_start",
            "train_end",
            "test_start",
            "test_end",
            "is_selected_for_app",
        ]
    ]
    walk_forward = pd.read_csv(WALK_FORWARD_SUMMARY_FILE)
    return comparison, walk_forward


def fmt_pct(value: float) -> str:
    return f"{value:.1%}"


def format_model_comparison(comparison: pd.DataFrame) -> pd.io.formats.style.Styler:
    display = comparison.rename(
        columns={
            "display_model": "Model",
            "mae": "MAE",
            "rmse": "RMSE",
            "spearman_rank_corr": "Rank Corr",
            "test_universe_avg_actual_return": "Universe Avg Return",
            "top5_avg_actual_return": "Top-5 Avg Return",
            "train_start": "Train Start",
            "train_end": "Train End",
            "test_start": "Test Start",
            "test_end": "Test End",
            "is_selected_for_app": "Used In App",
        }
    ).copy()
    display["Used In App"] = display["Used In App"].map({True: "Yes", False: "No"})
    return display.style.format(
        {
            "MAE": "{:.3f}",
            "RMSE": "{:.3f}",
            "Rank Corr": "{:.3f}",
            "Universe Avg Return": "{:.1%}",
            "Top-5 Avg Return": "{:.1%}",
        }
    )


def plot_model_metric_bars(comparison: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ordered_top5 = comparison.sort_values("top5_avg_actual_return", ascending=True)
    axes[0].barh(
        ordered_top5["display_model"],
        ordered_top5["top5_avg_actual_return"],
        color=["#1f8a5b" if name == BEST_MODEL_NAME else "#6f7f8f" for name in ordered_top5["display_model"]],
    )
    axes[0].set_title("Top-5 Actual Return")
    axes[0].set_xlabel("Return")
    axes[0].grid(axis="x", alpha=0.25)

    ordered_corr = comparison.sort_values("spearman_rank_corr", ascending=True)
    axes[1].barh(
        ordered_corr["display_model"],
        ordered_corr["spearman_rank_corr"],
        color=["#1f8a5b" if name == BEST_MODEL_NAME else "#6f7f8f" for name in ordered_corr["display_model"]],
    )
    axes[1].set_title("Spearman Rank Correlation")
    axes[1].set_xlabel("Correlation")
    axes[1].axvline(0, color="#222222", linewidth=1, alpha=0.35)
    axes[1].grid(axis="x", alpha=0.25)
    fig.tight_layout()
    return fig


def plot_feature_importance(feature_importance: pd.DataFrame):
    top_features = feature_importance.head(12).sort_values("importance")
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(top_features["feature"], top_features["importance"], color="#3478f6")
    ax.set_xlabel("Importance")
    ax.set_ylabel("")
    ax.set_title("Top Model Features")
    ax.grid(axis="x", alpha=0.25)
    fig.tight_layout()
    return fig


def plot_model_rankings(rankings: pd.DataFrame, selected: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 5.5))
    ax.scatter(
        rankings["volatility_60d"],
        rankings["predicted_63d_return"],
        s=24,
        alpha=0.35,
        color="#767676",
        label="Eligible universe",
    )
    if not selected.empty:
        ax.scatter(
            selected["volatility_60d"],
            selected["predicted_63d_return"],
            s=96,
            color="#1f8a5b",
            edgecolor="white",
            linewidth=1.0,
            label="Selected stocks",
        )
        for _, row in selected.iterrows():
            ax.annotate(
                row["ticker"],
                (row["volatility_60d"], row["predicted_63d_return"]),
                xytext=(5, 4),
                textcoords="offset points",
                fontsize=8,
            )
    ax.axhline(0, color="#222222", linewidth=1, alpha=0.35)
    ax.set_xlabel("60-Day Volatility")
    ax.set_ylabel("Predicted 63-Day Return")
    ax.set_title("Best Model Ranking View")
    ax.legend(loc="best")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    return fig


def apply_recommendation_preferences(
    rankings: pd.DataFrame,
    portfolio_size: int,
    max_volatility_60d: float,
    max_sector_weight: float,
    excluded_sectors: list[str],
    min_predicted_return: float,
    min_recent_return: float,
    ranking_objective: str,
) -> tuple[pd.DataFrame, pd.DataFrame, bool]:
    filtered = rankings.copy()
    filtered = filtered[~filtered["sector"].isin(excluded_sectors)]
    filtered = filtered[filtered["predicted_63d_return"] >= min_predicted_return]
    filtered = filtered[filtered["ret_60d"] >= min_recent_return]

    strict = filtered[filtered["volatility_60d"] <= max_volatility_60d].copy()
    relaxed = False
    candidate_pool = strict

    if len(candidate_pool) < portfolio_size:
        candidate_pool = filtered.copy()
        relaxed = True

    if ranking_objective == "Risk-adjusted return":
        candidate_pool["selection_score"] = (
            candidate_pool["predicted_63d_return"] / candidate_pool["volatility_60d"].clip(lower=0.01)
        )
    elif ranking_objective == "Smoother ride":
        candidate_pool["selection_score"] = (
            candidate_pool["predicted_63d_return"] - 0.35 * candidate_pool["volatility_60d"]
        )
    else:
        candidate_pool["selection_score"] = candidate_pool["predicted_63d_return"]

    candidate_pool = candidate_pool.sort_values(
        ["selection_score", "predicted_63d_return"],
        ascending=False,
    )

    max_sector_count = max(1, math.floor(portfolio_size * max_sector_weight))
    selected_rows = []
    sector_counts: dict[str, int] = {}

    for _, row in candidate_pool.iterrows():
        sector = row["sector"]
        if sector_counts.get(sector, 0) >= max_sector_count:
            continue
        selected_rows.append(row)
        sector_counts[sector] = sector_counts.get(sector, 0) + 1
        if len(selected_rows) == portfolio_size:
            break

    selected = pd.DataFrame(selected_rows).copy()
    if selected.empty:
        return selected, candidate_pool, relaxed

    selected.insert(0, "rank", range(1, len(selected) + 1))
    selected["weight"] = 1 / len(selected)
    selected["sector_weight"] = selected.groupby("sector")["weight"].transform("sum")
    return selected, candidate_pool, relaxed


def summarize_selection(selected: pd.DataFrame) -> dict[str, float]:
    if selected.empty:
        return {
            "expected_return": 0.0,
            "avg_volatility": 0.0,
            "recent_return": 0.0,
            "max_sector_weight": 0.0,
            "sectors": 0,
        }
    return {
        "expected_return": (selected["predicted_63d_return"] * selected["weight"]).sum(),
        "avg_volatility": (selected["volatility_60d"] * selected["weight"]).sum(),
        "recent_return": (selected["ret_60d"] * selected["weight"]).sum(),
        "max_sector_weight": selected.groupby("sector")["weight"].sum().max(),
        "sectors": selected["sector"].nunique(),
    }


tickers, prices = get_data()

page = st.sidebar.radio("Page", ["Recommendation", "Model Comparison", "Exploration", "DataViz"])

if page == "Recommendation":
    rankings, metrics, walk_forward, feature_importance = load_best_model_outputs()
    latest_date = rankings["date"].max().date().isoformat()
    metric_row = metrics.iloc[0]
    walk_row = walk_forward.iloc[0]

    st.subheader("Best Practical Model")
    st.write(
        f"The app uses **{BEST_MODEL_NAME}** rankings from **{latest_date}**. "
        "This model was selected for the final recommender because it keeps strong ranking performance "
        "while removing the questionable `history_days` shortcut feature."
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Fixed-split top-5 return",
        fmt_pct(metric_row["top5_avg_actual_return"]),
        help=(
            "Average actual 63-trading-day return of the model's top 5 picks in the fixed test period. "
            "Higher means the top-ranked stocks performed better in that historical test."
        ),
    )
    c2.metric(
        "Rank correlation",
        f"{metric_row['spearman_rank_corr']:.3f}",
        help=(
            "Spearman rank correlation compares predicted stock ranking with actual future ranking. "
            "Positive values mean the model tended to rank better future performers higher."
        ),
    )
    c3.metric(
        "Walk-forward top-5 return",
        fmt_pct(walk_row["mean_top5_avg_actual_return"]),
        help=(
            "Average actual return of the top 5 picks across repeated walk-forward test windows. "
            "This is a stricter validation view than one fixed train/test split."
        ),
    )
    c4.metric(
        "Top-5 beat universe",
        f"{int(walk_row['positive_top5_folds'])}/{int(walk_row['folds'])} folds",
        help=(
            "How often the top 5 picks beat the average stock in the same test window. "
            "This checks whether the model added value repeatedly, not just once."
        ),
    )

    with st.expander(
        "Model evaluation details",
    ):
        st.caption(
            "Fixed-split metrics test one historical train/test cut. Walk-forward metrics retrain through time "
            "and test repeated future windows, which better matches how a recommender would be used."
        )
        metrics_view = metrics[
            [
                "model",
                "train_start",
                "train_end",
                "test_start",
                "test_end",
                "mae",
                "rmse",
                "spearman_rank_corr",
                "test_universe_avg_actual_return",
                "top5_avg_actual_return",
            ]
        ].copy()
        st.dataframe(metrics_view, width="stretch")
        st.dataframe(walk_forward, width="stretch")

    st.caption(
        "Feature importance shows which input signals the selected Random Forest used most when ranking stocks."
    )
    st.pyplot(plot_feature_importance(feature_importance), clear_figure=True)

    st.subheader("Define Preferences")
    left, right = st.columns([1, 1])
    with left:
        profile = st.selectbox(
            "Risk profile",
            list(PROFILE_CONFIG),
            index=1,
            help=(
                "Sets the starting volatility cap. Conservative starts lower, Balanced is moderate, "
                "Aggressive allows jumpier stocks, and Custom starts from the Balanced value."
            ),
        )
        st.caption(PROFILE_CONFIG[profile]["description"])
        default_volatility = PROFILE_CONFIG[profile]["max_volatility_60d"]
        max_volatility_60d = st.slider(
            "Maximum 60-day volatility",
            min_value=0.10,
            max_value=1.20,
            value=float(default_volatility),
            step=0.05,
            format="%.2f",
            help=(
                "Filters out stocks whose annualized 60-day volatility is above this value. "
                "Lower values generally mean smoother recent price behavior; higher values allow larger swings."
            ),
        )
        portfolio_size = st.slider(
            "Number of recommended stocks",
            min_value=3,
            max_value=20,
            value=10,
            step=1,
            help=(
                "Controls how many stocks the app returns. More stocks usually improve diversification, "
                "but each holding gets a smaller equal weight."
            ),
        )
        ranking_objective = st.selectbox(
            "Selection objective",
            ["Highest expected return", "Risk-adjusted return", "Smoother ride"],
            index=0,
            help=(
                "Highest expected return ranks by model score. Risk-adjusted return divides expected return by "
                "volatility. Smoother ride penalizes volatile names more directly."
            ),
        )
    with right:
        max_sector_weight_pct = st.slider(
            "Maximum sector weight",
            min_value=10,
            max_value=60,
            value=30,
            step=5,
            format="%d%%",
            help=(
                "Limits concentration in one sector. For example, 30% with 10 stocks allows at most 3 names "
                "from the same sector in an equal-weight portfolio."
            ),
        )
        max_sector_weight = max_sector_weight_pct / 100
        sectors = sorted(rankings["sector"].dropna().unique())
        excluded_sectors = st.multiselect(
            "Exclude sectors",
            sectors,
            help=(
                "Removes selected sectors before ranking. Use this to avoid sectors the user does not want "
                "to invest in or already owns elsewhere."
            ),
        )
        min_predicted_return_pct = st.slider(
            "Minimum predicted 63-day return",
            min_value=-20,
            max_value=25,
            value=0,
            step=1,
            format="%d%%",
            help=(
                "Requires the model's expected 63-trading-day return to be at least this value. "
                "Raising it makes the filter stricter and may reduce diversification."
            ),
        )
        min_predicted_return = min_predicted_return_pct / 100
        min_recent_return_pct = st.slider(
            "Minimum recent 60-day return",
            min_value=-80,
            max_value=150,
            value=-80,
            step=5,
            format="%d%%",
            help=(
                "Filters by the stock's realized return over the latest 60 trading days. "
                "Use it to avoid recent losers or to focus on positive momentum."
            ),
        )
        min_recent_return = min_recent_return_pct / 100

    selected, candidate_pool, relaxed = apply_recommendation_preferences(
        rankings=rankings,
        portfolio_size=portfolio_size,
        max_volatility_60d=max_volatility_60d,
        max_sector_weight=max_sector_weight,
        excluded_sectors=excluded_sectors,
        min_predicted_return=min_predicted_return,
        min_recent_return=min_recent_return,
        ranking_objective=ranking_objective,
    )

    st.subheader("Recommended Stocks")
    if selected.empty:
        st.error("No stocks match these preferences. Relax the volatility, return, or sector filters.")
    else:
        if relaxed:
            st.warning(
                "The strict volatility cap did not leave enough candidates, so the app relaxed only that cap "
                "after applying the other filters."
                " Other preferences are still enforced."
            )

        summary = summarize_selection(selected)
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric(
            "Stocks",
            f"{len(selected)}",
            help="Number of stocks selected after applying the user preferences and diversification rules.",
        )
        s2.metric(
            "Expected 63-day return",
            fmt_pct(summary["expected_return"]),
            help=(
                "Equal-weighted average of the selected stocks' model-predicted 63-trading-day returns. "
                "This is a model estimate, not a guaranteed outcome."
            ),
        )
        s3.metric(
            "Avg 60-day volatility",
            fmt_pct(summary["avg_volatility"]),
            help=(
                "Equal-weighted average of selected stocks' annualized 60-day volatility. "
                "Higher values indicate larger recent price swings."
            ),
        )
        s4.metric(
            "Recent 60-day return",
            fmt_pct(summary["recent_return"]),
            help=(
                "Equal-weighted average of the selected stocks' actual return over the latest 60 trading days. "
                "This describes recent momentum, not the model's future forecast."
            ),
        )
        s5.metric(
            "Sectors",
            f"{summary['sectors']}",
            help="Number of different sectors represented in the selected portfolio.",
        )

        display_columns = [
            "rank",
            "ticker",
            "sector",
            "industry",
            "weight",
            "predicted_63d_return",
            "volatility_60d",
            "ret_60d",
            "sector_weight",
        ]
        display = selected[display_columns].copy()
        percent_columns = ["weight", "predicted_63d_return", "volatility_60d", "ret_60d", "sector_weight"]
        st.dataframe(
            display.style.format({column: "{:.1%}" for column in percent_columns}),
            width="stretch",
            hide_index=True,
        )
        with st.expander("How to read the recommendation table"):
            st.markdown(
                """
- `rank`: order after applying the selected objective and diversification rules.
- `weight`: equal position size based on the number of selected stocks.
- `predicted_63d_return`: model estimate for the next 63 trading days.
- `volatility_60d`: recent annualized volatility; higher means larger price swings.
- `ret_60d`: actual return over the most recent 60 trading days.
- `sector_weight`: total equal-weight exposure to that stock's sector after selection.
                """
            )

        sector_weights = selected.groupby("sector")["weight"].sum().sort_values(ascending=False)
        st.caption("Sector weights show how much of the equal-weight portfolio is allocated to each sector.")
        st.bar_chart(sector_weights)
        st.caption(
            "The scatter plot compares all currently eligible candidates with the selected stocks. "
            "It shows the tradeoff between predicted return and recent volatility."
        )
        st.pyplot(plot_model_rankings(candidate_pool, selected), clear_figure=True)

        csv = selected[display_columns].to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download recommendations as CSV",
            data=csv,
            file_name="stock_recommendations.csv",
            mime="text/csv",
            help="Exports the currently displayed recommendations and their key metrics.",
        )

elif page == "Model Comparison":
    comparison, walk_forward = load_model_comparison_outputs()
    best_fixed_top5 = comparison.loc[comparison["top5_avg_actual_return"].idxmax()]
    best_fixed_rank = comparison.loc[comparison["spearman_rank_corr"].idxmax()]
    selected_model = comparison[comparison["is_selected_for_app"]].iloc[0]
    walk_row = walk_forward.iloc[0]

    st.subheader("Models Tested")
    st.write(
        "The experiment compared a simple linear baseline, tree-based models, boosted trees, "
        "and a deep-learning model. The final app uses the model that gave the best practical "
        "balance between performance, explainability, and cleaner feature design."
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric(
        "Models compared",
        f"{len(comparison)}",
        help="Number of fixed-split model variants with saved evaluation metrics in the experiment folder.",
    )
    m2.metric(
        "Best fixed top-5",
        best_fixed_top5["display_model"],
        fmt_pct(best_fixed_top5["top5_avg_actual_return"]),
        help="The model whose historical top 5 picks had the highest actual return in the fixed test period.",
    )
    m3.metric(
        "Best fixed rank corr",
        best_fixed_rank["display_model"],
        f"{best_fixed_rank['spearman_rank_corr']:.3f}",
        help="The model with the strongest Spearman rank correlation in the fixed test period.",
    )
    m4.metric(
        "Selected for app",
        selected_model["display_model"],
        help="The model used by the Recommendation page to rank stocks before applying user preferences.",
    )

    st.dataframe(format_model_comparison(comparison), width="stretch", hide_index=True)

    with st.expander("How to read these metrics"):
        st.markdown(
            """
- `MAE`: average absolute forecast error. Lower is better.
- `RMSE`: forecast error metric that punishes large misses more. Lower is better.
- `Rank Corr`: Spearman rank correlation between predicted and actual future ranking. Higher is better.
- `Universe Avg Return`: average actual return of all tested stocks during the test window.
- `Top-5 Avg Return`: average actual return of the model's five highest-ranked stocks.
- `Used In App`: whether the Recommendation page uses that model's latest rankings.
            """
        )

    st.pyplot(plot_model_metric_bars(comparison), clear_figure=True)

    st.subheader("Deep Learning Model")
    rocm = comparison[comparison["display_model"].eq("ROCm PyTorch MLP")].iloc[0]
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Model type", "PyTorch MLP", help="A multilayer perceptron neural network trained with PyTorch.")
    d2.metric("MAE", f"{rocm['mae']:.3f}", help="Average absolute error. This was much higher than the simpler models.")
    d3.metric("RMSE", f"{rocm['rmse']:.3f}", help="Large-error-sensitive metric. Lower would be better.")
    d4.metric(
        "Rank Corr",
        f"{rocm['spearman_rank_corr']:.3f}",
        help="Negative rank correlation means this neural network did not rank future winners reliably in this run.",
    )
    st.write(
        "A deep-learning model was tested, but it was not selected because its prediction errors were larger "
        "and its rank correlation was slightly negative. In this dataset, extra model complexity did not improve "
        "the recommendation quality."
    )

    st.subheader("Why The App Uses Random Forest Without history_days")
    w1, w2, w3, w4 = st.columns(4)
    w1.metric(
        "Walk-forward folds",
        f"{int(walk_row['folds'])}",
        help="Number of repeated time-based train/test windows used in the walk-forward validation.",
    )
    w2.metric(
        "Mean top-5 return",
        fmt_pct(walk_row["mean_top5_avg_actual_return"]),
        help="Average actual return of the top 5 picks across the walk-forward folds.",
    )
    w3.metric(
        "Mean top-10 return",
        fmt_pct(walk_row["mean_top10_avg_actual_return"]),
        help="Average actual return of the top 10 picks across the walk-forward folds.",
    )
    w4.metric(
        "Top-5 beat universe",
        f"{int(walk_row['positive_top5_folds'])}/{int(walk_row['folds'])}",
        help="How often the top 5 picks beat the average stock in the same walk-forward test window.",
    )
    st.write(
        "Ridge had the strongest fixed-split results, but the practical recommender uses the no-history Random Forest "
        "because it avoids the suspicious `history_days` shortcut, remains explainable through feature importance, "
        "and has a walk-forward validation result. The Recommendation page then adds portfolio constraints on top of "
        "that model ranking."
    )

    with st.expander("Model selection takeaway"):
        st.markdown(
            """
- Best fixed-split benchmark: `Ridge baseline`.
- Best practical app model: `Random Forest without history_days`.
- Deep learning was tested: `ROCm PyTorch MLP`.
- Final recommendation logic: model ranking first, then user preferences and diversification constraints.
            """
        )

elif page == "Exploration":
    st.subheader("1. Exploration")
    st.write("First rows of the metadata table:")
    st.dataframe(tickers.head(10))
    st.write(f"Prices table shape: {prices.shape[0]} rows, {prices.shape[1]} columns")
    st.write("Summary statistics on price columns:")
    st.dataframe(prices[["open", "high", "low", "close", "adj_close", "volume"]].describe())

    if st.checkbox("Show missing values"):
        st.dataframe(prices.isna().sum())

elif page == "DataViz":
    st.subheader("2. DataViz — 6 plots for Step 1")

    st.markdown("**Plot 1 — countplot** (sector, categorical variable)")
    st.caption("Shows how many stocks sit in each sector — the universe is imbalanced, so a naïve picker would overweight Industrials and Financials.")
    st.pyplot(plot_sector_count(tickers), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        st.markdown("**Validation method:** Raw data aggregation (`value_counts()`).\n\n**Interpretation:** By aggregating the metadata, we mathematically prove the visual imbalance. If the recommender chose randomly, it would statistically favor Industrials and Financials purely due to their massive volume in the index. This data manipulation validates the necessity of our hard '30% max per sector' business rule.")
        st.dataframe(tickers['sector'].value_counts())

    st.markdown("**Plot 2 — boxplot** (mean daily volume per stock)")
    st.caption(
        "Y-axis = average shares traded per day on IEX (k = thousands). "
        "Red dashed line = median (~104k shares/day)."
    )
    st.markdown(
        """
- **503 stocks, one average per name** — each point is the mean daily volume over all days in the dataset (not a single day).
- **Typical stock ~104k shares/day** — half of S&P names trade less than the median; half trade more.
- **Middle 50% sit between ~60k and ~200k/day** — the blue box; most names are in this band, not extremely quiet or hyper-liquid.
- **A few names dominate liquidity** — e.g. NVDA ~1.6M vs NVR ~1.7k shares/day on average; the dots are those extreme mega-liquid names.
        """
    )
    st.pyplot(plot_volume_box(prices), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        st.markdown("**Validation method:** Descriptive statistics (`describe()`) on aggregated mean daily volume.\n\n**Interpretation:** The table below calculates the exact percentiles (25%, 50% median, 75%) of the mean volume distribution. You can see the `50%` (median) explicitly matches our ~104k observation. The massive difference between the `75%` percentile and the `max` value statistically validates the existence of extreme outliers (the long upper whisker and dots in the boxplot).")
        st.dataframe(prices.groupby("ticker")["volume"].mean().describe())

    st.markdown("**Plot 3 — histplot** (daily returns)")
    st.caption(
        "X-axis = % price change vs the previous day. Y-axis = how many days fall in each bin (k = thousands)."
    )
    st.markdown(
        """
- **What ~725k means** — We have **503 stocks**, each with **~1,460 trading days** in the CSV. That is **503 × ~1,460 ≈ 726k rows** (one row = one stock on one day). We drop **503 days** (the first day of each stock, no “yesterday” to compare) → **~725k daily returns**. Each bar asks: “On how many of those days did the price move by this %?”
- **Typical day ≈ +0.07%** — red dashed line (median); prices usually move very little in one session.
- **Most mass sits near 0%** — the histogram is highest around “no big move”; that is normal market behaviour.
- **Long tails left and right** — rare but real crashes (e.g. −53% in one day) and spikes (e.g. +127%); risk is in those tails.
- **Why it matters for the recommender** — average return is tiny (~0.07%/day), but a typical daily move is ~1% (up or down) and the spread across all days (std) is ~2%/day — so clustering must use **risk**, not return alone.
        """
    )
    st.pyplot(plot_return_hist(prices), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        st.markdown("**Validation method:** Global descriptive statistics (`describe()`) across ~725k daily return observations.\n\n**Interpretation:** The `50%` (median) confirms our observation that a typical day is almost completely flat (~0.07%). However, comparing the standard deviation (`std`) to the `min` and `max` statistically proves the 'fat tails' concept: crashes and spikes extend far beyond normal variance, meaning risk in the stock market is driven by rare, extreme events rather than daily noise.")
        st.dataframe(prices["daily_return"].describe())

    st.markdown("**Plot 4 — lineplot** (price over time)")
    st.caption(
        "Y-axis = split/dividend-adjusted close (USD). Use the dropdown to compare how different names evolved over the same calendar."
    )
    ticker = st.selectbox("Choose a ticker", sorted(tickers["ticker"]))
    summary = get_price_line_summary(prices, ticker)
    st.markdown(
        f"""
- **What the line shows** — **{summary['n_days']:,} trading days** for **{ticker}**, from **{summary['start_date'].strftime('%Y-%m-%d')}** to **{summary['end_date'].strftime('%Y-%m-%d')}**. Each point is the **adjusted close** (USD): corporate actions are already baked in, so the path is comparable over time.
- **This ticker in our window** — starts at **{summary['start_price']:.2f} USD**, ends at **{summary['end_price']:.2f} USD** → **total return {summary['total_return_pct']:+.0f}%** over the full series (not per day).
- **Same market, different stories** — compare dropdown names: e.g. **NVDA ~+1973%**, **AAPL ~+236%**, **KO ~+100%**, **NVR ~+53%** in this CSV. Steep lines are past winners, not a promise of future performance.
- **Price path ≠ daily risk** — a smooth upward line can still have **~2% daily volatility** (Plot 3). The Y-axis here is **level**, not day-to-day swings.
- **Why it matters for the recommender** — Step 1 clusters by **risk profile**, not by “who drew the prettiest line”. This plot is a **sanity check** for demos: when we recommend a stock from a cluster, you can open it here and see **why that name’s history matches** (or differs from) the user’s horizon and loss tolerance.
        """
    )
    st.pyplot(plot_price_line(prices, ticker), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        if summary:
            st.markdown("**Validation method:** Point-to-point percentage change calculation.\n\n**Interpretation:** The line chart visually represents the price journey, but 'Total Return' is strictly a function of the start and end points. The equation below explicitly calculates this using the first and last `adj_close` values in our dataset. This validates that despite the visual volatility along the path, the final realized return for a buy-and-hold strategy is exactly as stated in the chart title.")
            st.code(f"({summary['end_price']:.2f} / {summary['start_price']:.2f} - 1) * 100 = {summary['total_return_pct']:.2f}%")

    st.markdown("**Plot 5 — heatmap** (Correlation Matrix)")
    st.caption("Shows the Pearson correlation coefficient between daily returns of the 10 most traded stocks.")
    st.markdown(
        """
- **Why Correlation Matters** — A core principle of portfolio management is diversification. If all stocks in a portfolio move in the exact same direction (correlation near 1.0), the risk is concentrated.
- **Top 10 Stocks** — This heatmap isolates the 10 most liquid names in the dataset. Notice how certain stocks might be highly correlated with each other, but less correlated with others.
- **Business Value** — The recommender uses sector constraints (max 30% per sector) specifically to avoid high correlations and build a diversified, safer portfolio for the user.
        """
    )
    st.pyplot(plot_correlation_heatmap(prices), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        st.markdown("**Validation method:** Pearson Correlation Coefficient matrix calculation.\n\n**Interpretation:** The heatmap is a visual representation of this exact matrix. Values closer to `1.0` indicate stocks moving in perfect lockstep, while values closer to `0.0` indicate independent movement. By calculating this mathematically on the wide-format returns dataframe, we prove that certain stock pairs offer poor diversification (high correlation). The recommender avoids this by scattering picks across multiple clusters and sectors.")
        top_tickers = prices.groupby("ticker")["volume"].mean().nlargest(10).index
        data = prices[prices["ticker"].isin(top_tickers)]
        wide_returns = data.pivot(index="date", columns="ticker", values="daily_return").dropna()
        st.dataframe(wide_returns.corr())

    st.markdown("**Plot 6 — scatterplot** (Risk vs. Return)")
    st.caption("X-axis = Annualized Volatility (Risk). Y-axis = Annualized Return. Each point is one stock.")
    st.markdown(
        """
- **What is 'Risk' here?** — Risk is mathematically calculated as **Annualized Volatility** (the standard deviation of a stock's daily returns, scaled to a 252-day trading year). In finance, volatility equates to uncertainty. A stock with 15% volatility is relatively stable and its price moves predictably, whereas a 50% volatility stock can swing wildly up and down, creating panic for inexperienced investors.
- **The Core of the Recommender** — This chart proves why grouping stocks by risk profile is necessary. Some stocks offer higher returns for the same level of risk, while others are highly volatile without the reward.
- **Four Quadrants** — The dashed lines represent the median risk and median return across the S&P 500. The top-left quadrant (High Return, Low Risk) is the theoretical "sweet spot".
- **Business Value** — For a conservative user, the recommender will explicitly filter out high-volatility names (the right side of the plot). For an aggressive user, it can venture into the higher risk territory aiming for higher expected returns.
        """
    )
    st.pyplot(plot_risk_return_scatter(prices), clear_figure=True)
    with st.expander("🔍 View statistical validation"):
        stats = prices.groupby("ticker")["daily_return"].agg(["mean", "std"]).dropna()
        pearson_corr = stats["mean"].corr(stats["std"])
        st.markdown("**Validation method:** Pearson Correlation between Annualized Volatility and Annualized Expected Return.\n\n**Interpretation:** We mathematically aggregated all 503 stocks into a single (Risk, Return) tuple and calculated their linear correlation. A strong positive correlation (e.g., > 0.7) would mean 'more risk always equals more reward'.")
        st.write(f"**Calculated Pearson correlation:** `{pearson_corr:.4f}`")
        st.markdown(f"Because the correlation is so close to 0 (`{pearson_corr:.4f}`), we statistically validate the core observation from the scatterplot: taking blind risk does **not** guarantee proportionally higher returns. This definitively proves the business need for a smart recommender that seeks the 'efficient frontier' (high return for a given risk) rather than just picking randomly.")

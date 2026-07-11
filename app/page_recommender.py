"""Recommender (Track A — exploratory tier): the parent project's ranking recommender + model
comparison, rendered from the VENDORED CSVs (app/data/trackB/). Ported from
mac-2026-06-09-full-6y/app.py; every number here is a model prediction or a fixed-split /
un-purged walk-forward metric — the permanent tier badge says so, and nothing on this page ever
selects tickers for the sealed Track-B simulator (that would be look-ahead: these rankings are
dated at the END of the Track-B OOS window).
"""
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from common import DATA, track_b_badge
from package_builder import (OBJECTIVES, PROFILE_CONFIG,
                             apply_recommendation_preferences,
                             risk_answers_to_recommendation_defaults)

TRACK_B = DATA / "trackB"
BEST_MODEL_NAME = "Random Forest without history_days"
MODEL_METRIC_FILES = {
    "Ridge baseline": TRACK_B / "model_metrics.csv",
    "Random Forest": TRACK_B / "random_forest_metrics.csv",
    "Random Forest without history_days": TRACK_B / "random_forest_no_history_metrics.csv",
    "XGBoost without history_days": TRACK_B / "xgboost_no_history_metrics.csv",
    "ROCm PyTorch MLP": TRACK_B / "rocm_model_metrics.csv",
}


@st.cache_data
def load_best_model_outputs():
    rankings = pd.read_csv(TRACK_B / "random_forest_no_history_latest_rankings.csv", parse_dates=["date"])
    metrics = pd.read_csv(TRACK_B / "random_forest_no_history_metrics.csv")
    walk_forward = pd.read_csv(TRACK_B / "walk_forward_rf_no_history_summary.csv")
    feature_importance = pd.read_csv(TRACK_B / "random_forest_no_history_feature_importance.csv")
    rankings = rankings.sort_values("predicted_63d_return", ascending=False).reset_index(drop=True)
    return rankings, metrics, walk_forward, feature_importance


@st.cache_data
def load_walk_forward_folds():
    return pd.read_csv(TRACK_B / "walk_forward_rf_no_history_fold_metrics.csv")


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
        ["display_model", "mae", "rmse", "spearman_rank_corr", "test_universe_avg_actual_return",
         "top5_avg_actual_return", "train_start", "train_end", "test_start", "test_end",
         "is_selected_for_app"]
    ]
    walk_forward = pd.read_csv(TRACK_B / "walk_forward_rf_no_history_summary.csv")
    return comparison, walk_forward


def fmt_pct(value: float) -> str:
    return f"{value:.1%}"


def format_model_comparison(comparison: pd.DataFrame):
    display = comparison.rename(columns={
        "display_model": "Model", "mae": "MAE", "rmse": "RMSE", "spearman_rank_corr": "Rank Corr",
        "test_universe_avg_actual_return": "Universe Avg Return",
        "top5_avg_actual_return": "Top-5 Avg Return", "train_start": "Train Start",
        "train_end": "Train End", "test_start": "Test Start", "test_end": "Test End",
        "is_selected_for_app": "Used In App"}).copy()
    display["Used In App"] = display["Used In App"].map({True: "Yes", False: "No"})
    return display.style.format({"MAE": "{:.3f}", "RMSE": "{:.3f}", "Rank Corr": "{:.3f}",
                                 "Universe Avg Return": "{:.1%}", "Top-5 Avg Return": "{:.1%}"})


def plot_model_metric_bars(comparison: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    ordered_top5 = comparison.sort_values("top5_avg_actual_return", ascending=True)
    axes[0].barh(ordered_top5["display_model"], ordered_top5["top5_avg_actual_return"],
                 color=["#1f8a5b" if name == BEST_MODEL_NAME else "#6f7f8f"
                        for name in ordered_top5["display_model"]])
    axes[0].set_title("Top-5 Actual Return")
    axes[0].set_xlabel("Return")
    axes[0].grid(axis="x", alpha=0.25)
    ordered_corr = comparison.sort_values("spearman_rank_corr", ascending=True)
    axes[1].barh(ordered_corr["display_model"], ordered_corr["spearman_rank_corr"],
                 color=["#1f8a5b" if name == BEST_MODEL_NAME else "#6f7f8f"
                        for name in ordered_corr["display_model"]])
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
    ax.scatter(rankings["volatility_60d"], rankings["predicted_63d_return"], s=24, alpha=0.35,
               color="#767676", label="Eligible universe")
    if not selected.empty:
        ax.scatter(selected["volatility_60d"], selected["predicted_63d_return"], s=96,
                   color="#1f8a5b", edgecolor="white", linewidth=1.0, label="Selected stocks")
        for _, row in selected.iterrows():
            ax.annotate(row["ticker"], (row["volatility_60d"], row["predicted_63d_return"]),
                        xytext=(5, 4), textcoords="offset points", fontsize=8)
    ax.axhline(0, color="#222222", linewidth=1, alpha=0.35)
    ax.set_xlabel("60-Day Volatility")
    ax.set_ylabel("Predicted 63-Day Return")
    ax.set_title("Best Model Ranking View")
    ax.legend(loc="best")
    ax.grid(alpha=0.2)
    fig.tight_layout()
    return fig


def summarize_selection(selected: pd.DataFrame) -> dict:
    return {"expected_return": float((selected["predicted_63d_return"] * selected["weight"]).sum()),
            "avg_volatility": float((selected["volatility_60d"] * selected["weight"]).sum()),
            "recent_return": float((selected["ret_60d"] * selected["weight"]).sum()),
            "sectors": int(selected["sector"].nunique())}


def _render_recommendation() -> None:
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
    c1.metric("Fixed-split top-5 return", fmt_pct(metric_row["top5_avg_actual_return"]),
              help="Average actual 63-trading-day return of the model's top 5 picks in the fixed test "
                   "period. Higher means the top-ranked stocks performed better in that historical test.")
    c2.metric("Rank correlation", f"{metric_row['spearman_rank_corr']:.3f}",
              help="Spearman rank correlation compares predicted stock ranking with actual future "
                   "ranking. Positive values mean the model tended to rank better future performers higher.")
    c3.metric("Walk-forward top-5 return", fmt_pct(walk_row["mean_top5_avg_actual_return"]),
              help="Average actual return of the top 5 picks across repeated walk-forward test windows. "
                   "This is a stricter validation view than one fixed train/test split.")
    c4.metric("Top-5 beat universe", f"{int(walk_row['positive_top5_folds'])}/{int(walk_row['folds'])} folds",
              help="How often the top 5 picks beat the average stock in the same test window. "
                   "This checks whether the model added value repeatedly, not just once.")

    with st.expander("Model evaluation details"):
        st.caption(
            "Fixed-split metrics test one historical train/test cut. Walk-forward metrics retrain "
            "through time and test repeated future windows, which better matches how a recommender "
            "would be used. Caveat (see the badge above): this walk-forward has NO purge/embargo — "
            "the last 63 training days' labels overlap each test window, and returns are gross."
        )
        metrics_view = metrics[["model", "train_start", "train_end", "test_start", "test_end",
                                "mae", "rmse", "spearman_rank_corr",
                                "test_universe_avg_actual_return", "top5_avg_actual_return"]].copy()
        st.dataframe(metrics_view, width="stretch")
        st.dataframe(load_walk_forward_folds(), width="stretch")

    st.caption("Feature importance shows which input signals the selected Random Forest used most "
               "when ranking stocks.")
    st.pyplot(plot_feature_importance(feature_importance), clear_figure=True)

    st.subheader("Define Preferences")
    risk_answers = st.session_state.get("risk_answers")
    preference_defaults = risk_answers_to_recommendation_defaults(risk_answers)
    if risk_answers and st.session_state.get("_applied_risk_answers") != risk_answers:
        st.session_state["recommendation_profile"] = preference_defaults["profile"]
        st.session_state["recommendation_max_volatility_60d"] = preference_defaults["max_volatility_60d"]
        st.session_state["recommendation_portfolio_size"] = preference_defaults["portfolio_size"]
        st.session_state["recommendation_ranking_objective"] = preference_defaults["ranking_objective"]
        st.session_state["recommendation_max_sector_weight_pct"] = preference_defaults["max_sector_weight_pct"]
        st.session_state["recommendation_excluded_sectors"] = preference_defaults["excluded_sectors"]
        st.session_state["recommendation_min_predicted_return_pct"] = preference_defaults["min_predicted_return_pct"]
        st.session_state["recommendation_min_recent_return_pct"] = preference_defaults["min_recent_return_pct"]
        st.session_state["_applied_risk_answers"] = risk_answers.copy()

    if risk_answers:
        st.info("Preference controls are prefilled from the Risk Profile questionnaire. "
                "You can still adjust them before reviewing the recommendations.")

    left, right = st.columns([1, 1])
    with left:
        profile_options = list(PROFILE_CONFIG)
        profile = st.selectbox(
            "Risk profile", profile_options,
            index=profile_options.index(preference_defaults["profile"]),
            key="recommendation_profile",
            help="Sets the starting volatility cap. Conservative starts lower, Balanced is moderate, "
                 "Aggressive allows jumpier stocks, and Custom starts from the Balanced value.")
        st.caption(PROFILE_CONFIG[profile]["description"])
        max_volatility_60d = st.slider(
            "Maximum 60-day volatility", min_value=0.10, max_value=1.20,
            value=float(preference_defaults["max_volatility_60d"]), step=0.05, format="%.2f",
            key="recommendation_max_volatility_60d",
            help="Filters out stocks whose annualized 60-day volatility is above this value. "
                 "Lower values generally mean smoother recent price behavior; higher values allow "
                 "larger swings.")
        portfolio_size = st.slider(
            "Number of recommended stocks", min_value=3, max_value=20,
            value=preference_defaults["portfolio_size"], step=1,
            key="recommendation_portfolio_size",
            help="Controls how many stocks the app returns. More stocks usually improve "
                 "diversification, but each holding gets a smaller equal weight.")
        ranking_objective = st.selectbox(
            "Selection objective", OBJECTIVES,
            index=OBJECTIVES.index(preference_defaults["ranking_objective"]),
            key="recommendation_ranking_objective",
            help="Highest expected return ranks by model score. Risk-adjusted return divides expected "
                 "return by volatility. Smoother ride penalizes volatile names more directly.")
    with right:
        max_sector_weight_pct = st.slider(
            "Maximum sector weight", min_value=10, max_value=60,
            value=preference_defaults["max_sector_weight_pct"], step=5, format="%d%%",
            key="recommendation_max_sector_weight_pct",
            help="Limits concentration in one sector. For example, 30% with 10 stocks allows at most "
                 "3 names from the same sector in an equal-weight portfolio.")
        max_sector_weight = max_sector_weight_pct / 100
        sectors = sorted(rankings["sector"].dropna().unique())
        if risk_answers:
            st.session_state["recommendation_excluded_sectors"] = [
                sector for sector in st.session_state.get("recommendation_excluded_sectors", [])
                if sector in sectors]
        default_excluded_sectors = [s for s in preference_defaults["excluded_sectors"] if s in sectors]
        excluded_sectors = st.multiselect(
            "Exclude sectors", sectors, default=default_excluded_sectors,
            key="recommendation_excluded_sectors",
            help="Removes selected sectors before ranking. Use this to avoid sectors the user does "
                 "not want to invest in or already owns elsewhere.")
        min_predicted_return_pct = st.slider(
            "Minimum predicted 63-day return", min_value=-20, max_value=25,
            value=preference_defaults["min_predicted_return_pct"], step=1, format="%d%%",
            key="recommendation_min_predicted_return_pct",
            help="Requires the model's expected 63-trading-day return to be at least this value. "
                 "Raising it makes the filter stricter and may reduce diversification.")
        min_predicted_return = min_predicted_return_pct / 100
        min_recent_return_pct = st.slider(
            "Minimum recent 60-day return", min_value=-80, max_value=150,
            value=preference_defaults["min_recent_return_pct"], step=5, format="%d%%",
            key="recommendation_min_recent_return_pct",
            help="Filters by the stock's realized return over the latest 60 trading days. "
                 "Use it to avoid recent losers or to focus on positive momentum.")
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
        return
    if relaxed:
        st.warning("The strict volatility cap did not leave enough candidates, so the app relaxed "
                   "only that cap after applying the other filters. Other preferences are still enforced.")

    summary = summarize_selection(selected)
    s1, s2, s3, s4, s5 = st.columns(5)
    s1.metric("Stocks", f"{len(selected)}",
              help="Number of stocks selected after applying the user preferences and diversification rules.")
    s2.metric("Expected 63-day return", fmt_pct(summary["expected_return"]),
              help="Equal-weighted average of the selected stocks' model-predicted 63-trading-day "
                   "returns. This is a model estimate, not a guaranteed outcome — and not a backtest.")
    s3.metric("Avg 60-day volatility", fmt_pct(summary["avg_volatility"]),
              help="Equal-weighted average of selected stocks' annualized 60-day volatility. "
                   "Higher values indicate larger recent price swings.")
    s4.metric("Recent 60-day return", fmt_pct(summary["recent_return"]),
              help="Equal-weighted average of the selected stocks' actual return over the latest 60 "
                   "trading days. This describes recent momentum, not the model's future forecast.")
    s5.metric("Sectors", f"{summary['sectors']}",
              help="Number of different sectors represented in the selected portfolio.")

    display_columns = ["rank", "ticker", "sector", "industry", "weight", "predicted_63d_return",
                       "volatility_60d", "ret_60d", "sector_weight"]
    display = selected[display_columns].copy()
    percent_columns = ["weight", "predicted_63d_return", "volatility_60d", "ret_60d", "sector_weight"]
    st.dataframe(display.style.format({c: "{:.1%}" for c in percent_columns}),
                 width="stretch", hide_index=True)
    with st.expander("How to read the recommendation table"):
        st.markdown(
            """
- `rank`: order after applying the selected objective and diversification rules.
- `weight`: equal position size based on the number of selected stocks.
- `predicted_63d_return`: model estimate for the next 63 trading days — **a prediction, not a backtest**.
- `volatility_60d`: recent annualized volatility; higher means larger price swings.
- `ret_60d`: actual return over the most recent 60 trading days.
- `sector_weight`: total equal-weight exposure to that stock's sector after selection.
            """
        )

    sector_weights = selected.groupby("sector")["weight"].sum().sort_values(ascending=False)
    st.caption("Sector weights show how much of the equal-weight portfolio is allocated to each sector.")
    st.bar_chart(sector_weights)
    st.caption("The scatter plot compares all currently eligible candidates with the selected stocks. "
               "It shows the tradeoff between predicted return and recent volatility.")
    st.pyplot(plot_model_rankings(candidate_pool, selected), clear_figure=True)

    csv = selected[display_columns].to_csv(index=False).encode("utf-8")
    st.download_button("Download recommendations as CSV", data=csv,
                       file_name="stock_recommendations.csv", mime="text/csv",
                       help="Exports the currently displayed recommendations and their key metrics.")


def _render_model_comparison() -> None:
    comparison, walk_forward = load_model_comparison_outputs()
    best_fixed_top5 = comparison.loc[comparison["top5_avg_actual_return"].idxmax()]
    best_fixed_rank = comparison.loc[comparison["spearman_rank_corr"].idxmax()]
    selected_model = comparison[comparison["is_selected_for_app"]].iloc[0]
    walk_row = walk_forward.iloc[0]

    st.subheader("Models Tested")
    st.write(
        "The experiment compared a simple linear baseline, tree-based models, boosted trees, "
        "and a deep-learning model. The final recommender uses the model that gave the best practical "
        "balance between performance, explainability, and cleaner feature design."
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Models compared", f"{len(comparison)}",
              help="Number of fixed-split model variants with saved evaluation metrics.")
    m2.metric("Best fixed top-5", best_fixed_top5["display_model"],
              fmt_pct(best_fixed_top5["top5_avg_actual_return"]),
              help="The model whose historical top 5 picks had the highest actual return in the "
                   "fixed test period.")
    m3.metric("Best fixed rank corr", best_fixed_rank["display_model"],
              f"{best_fixed_rank['spearman_rank_corr']:.3f}",
              help="The model with the strongest Spearman rank correlation in the fixed test period.")
    m4.metric("Selected for app", selected_model["display_model"],
              help="The model used by the Recommendation section to rank stocks before applying "
                   "user preferences.")

    st.dataframe(format_model_comparison(comparison), width="stretch", hide_index=True)

    with st.expander("How to read these metrics"):
        st.markdown(
            """
- `MAE`: average absolute forecast error. Lower is better.
- `RMSE`: forecast error metric that punishes large misses more. Lower is better.
- `Rank Corr`: Spearman rank correlation between predicted and actual future ranking. Higher is better.
- `Universe Avg Return`: average actual return of all tested stocks during the test window.
- `Top-5 Avg Return`: average actual return of the model's five highest-ranked stocks.
- `Used In App`: whether the Recommendation section uses that model's latest rankings.
            """
        )

    st.pyplot(plot_model_metric_bars(comparison), clear_figure=True)

    st.subheader("Deep Learning Model")
    rocm = comparison[comparison["display_model"].eq("ROCm PyTorch MLP")].iloc[0]
    d1, d2, d3, d4 = st.columns(4)
    d1.metric("Model type", "PyTorch MLP",
              help="A multilayer perceptron neural network trained with PyTorch.")
    d2.metric("MAE", f"{rocm['mae']:.3f}",
              help="Average absolute error. This was much higher than the simpler models.")
    d3.metric("RMSE", f"{rocm['rmse']:.3f}",
              help="Large-error-sensitive metric. Lower would be better.")
    d4.metric("Rank Corr", f"{rocm['spearman_rank_corr']:.3f}",
              help="Negative rank correlation means this neural network did not rank future winners "
                   "reliably in this run.")
    st.write(
        "A deep-learning model was tested, but it was not selected because its prediction errors were "
        "larger and its rank correlation was slightly negative. In this dataset, extra model complexity "
        "did not improve the recommendation quality."
    )

    st.subheader("Why The App Uses Random Forest Without history_days")
    w1, w2, w3, w4 = st.columns(4)
    w1.metric("Walk-forward folds", f"{int(walk_row['folds'])}",
              help="Number of repeated time-based train/test windows used in the walk-forward validation.")
    w2.metric("Mean top-5 return", fmt_pct(walk_row["mean_top5_avg_actual_return"]),
              help="Average actual return of the top 5 picks across the walk-forward folds.")
    w3.metric("Mean top-10 return", fmt_pct(walk_row["mean_top10_avg_actual_return"]),
              help="Average actual return of the top 10 picks across the walk-forward folds.")
    w4.metric("Top-5 beat universe", f"{int(walk_row['positive_top5_folds'])}/{int(walk_row['folds'])}",
              help="How often the top 5 picks beat the average stock in the same walk-forward test window.")
    st.write(
        "Ridge had the strongest fixed-split results, but the practical recommender uses the no-history "
        "Random Forest because it avoids the suspicious `history_days` shortcut, remains explainable "
        "through feature importance, and has a walk-forward validation result. The Recommendation "
        "section then adds portfolio constraints on top of that model ranking."
    )
    st.caption("Naming note: 'Random Forest' here is the Track-A ranking *regressor* (best of its "
               "family). It is unrelated to any classifier baselines used inside the Track-B "
               "pipelines — the two tracks answer different questions on different data.")

    with st.expander("Model selection takeaway"):
        st.markdown(
            """
- Best fixed-split benchmark: `Ridge baseline`.
- Best practical app model: `Random Forest without history_days`.
- Deep learning was tested: `ROCm PyTorch MLP`.
- Final read: **the best model is not always the most complex model** — and a single fixed split
  flatters; the walk-forward view is weaker (rank correlation ≈ 0.06) and itself carries the
  no-purge caveat from the badge above.
            """
        )


def render() -> None:
    st.title("Recommender — Track A (exploratory)")
    track_b_badge()
    _render_recommendation()
    st.divider()
    _render_model_comparison()

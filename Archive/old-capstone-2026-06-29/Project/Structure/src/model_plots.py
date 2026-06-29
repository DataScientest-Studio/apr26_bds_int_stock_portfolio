"""Plotly figure builders for the model / portfolio / walk-forward pages.

Each function returns a Plotly ``Figure`` to be rendered with
``st.plotly_chart(fig, use_container_width=True)``. Pure presentation — no data
loading, no ML imports. The existing 6 EDA plots stay in ``src/plots.py``
(Seaborn); these are the new interactive views.
"""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Short, readable labels for the metric selector.
METRIC_LABELS = {
    "mae": "MAE (lower is better)",
    "rmse": "RMSE (lower is better)",
    "spearman_rank_corr": "Spearman rank IC (higher is better)",
    "top5_avg_actual_return": "Top-5 avg actual return (higher is better)",
    "test_universe_avg_actual_return": "Universe avg actual return",
    "lift_over_universe": "Top-5 lift over universe avg (higher is better)",
}


def plot_metrics_leaderboard(metrics_df: pd.DataFrame, metric: str) -> go.Figure:
    """Horizontal bar of one metric across all models."""
    d = metrics_df.copy()
    label_col = "label" if "label" in d.columns else "model"
    d = d.sort_values(metric, ascending=True)
    fig = px.bar(
        d,
        x=metric,
        y=label_col,
        orientation="h",
        text=d[metric].round(4),
        title=f"Model comparison — {METRIC_LABELS.get(metric, metric)}",
    )
    fig.update_traces(textposition="outside")
    fig.update_layout(yaxis_title="", xaxis_title=METRIC_LABELS.get(metric, metric))
    # Overlay the universe baseline when comparing realized top-5 returns.
    if metric == "top5_avg_actual_return" and "test_universe_avg_actual_return" in d.columns:
        universe = float(d["test_universe_avg_actual_return"].dropna().median())
        fig.add_vline(
            x=universe,
            line_dash="dash",
            line_color="red",
            annotation_text=f"universe avg {universe:.3f}",
        )
    return fig


def plot_pred_vs_actual(pred_df: pd.DataFrame) -> go.Figure:
    """2-D density of predicted vs actual 63-day return (handles ~147k rows)."""
    d = pred_df
    fig = px.density_heatmap(
        d,
        x="target_63d_return",
        y="predicted_63d_return",
        nbinsx=60,
        nbinsy=60,
        color_continuous_scale="Blues",
        title="Predicted vs actual 63-day return (density)",
    )
    lo = float(min(d["target_63d_return"].min(), d["predicted_63d_return"].min()))
    hi = float(max(d["target_63d_return"].max(), d["predicted_63d_return"].max()))
    fig.add_trace(
        go.Scatter(x=[lo, hi], y=[lo, hi], mode="lines", line=dict(color="red", dash="dash"), name="y = x")
    )
    fig.update_layout(xaxis_title="Actual return", yaxis_title="Predicted return")
    return fig


def plot_residual_hist(pred_df: pd.DataFrame) -> go.Figure:
    residual = pred_df["target_63d_return"] - pred_df["predicted_63d_return"]
    fig = px.histogram(residual, nbins=80, title="Residuals (actual − predicted)")
    fig.update_layout(xaxis_title="Residual", yaxis_title="Count", showlegend=False)
    return fig


def _importance_kind(feature: str) -> str:
    return "Sector dummy" if str(feature).startswith("sector_") else "Numeric feature"


def plot_feature_importance_bar(imp_df: pd.DataFrame, top_n: int = 12, title: str = "Feature importance") -> go.Figure:
    d = imp_df.head(top_n).copy()
    d["kind"] = d["feature"].apply(_importance_kind)
    d = d.sort_values("importance", ascending=True)
    fig = px.bar(
        d,
        x="importance",
        y="feature",
        orientation="h",
        color="kind",
        color_discrete_map={"Numeric feature": "#2c7fb8", "Sector dummy": "#7fcdbb"},
        title=title,
    )
    fig.update_layout(yaxis_title="", xaxis_title="Importance", legend_title="")
    return fig


def plot_feature_importance_compare(rf_imp: pd.DataFrame, nohist_imp: pd.DataFrame, top_n: int = 12) -> go.Figure:
    a = rf_imp.head(top_n).assign(model="RF (with history_days)")
    b = nohist_imp.head(top_n).assign(model="RF (no history_days)")
    d = pd.concat([a, b], ignore_index=True)
    fig = px.bar(
        d,
        x="importance",
        y="feature",
        color="model",
        orientation="h",
        barmode="group",
        title="Feature importance — RF with vs without history_days",
    )
    fig.update_layout(yaxis_title="", xaxis_title="Importance", legend_title="")
    return fig


def plot_walkforward_folds(fold_df: pd.DataFrame) -> go.Figure:
    """Per-fold realized returns (bars) plus rank IC (line, secondary axis)."""
    d = fold_df.sort_values("fold")
    fig = go.Figure()
    fig.add_bar(x=d["fold"], y=d["top5_avg_actual_return"], name="Top-5 return")
    fig.add_bar(x=d["fold"], y=d["top10_avg_actual_return"], name="Top-10 return")
    fig.add_bar(x=d["fold"], y=d["universe_avg_actual_return"], name="Universe avg")
    fig.add_trace(
        go.Scatter(
            x=d["fold"],
            y=d["spearman_rank_corr"],
            name="Spearman IC",
            yaxis="y2",
            mode="lines+markers",
            line=dict(color="black"),
        )
    )
    fig.add_hline(y=0, line_color="grey", line_width=1)
    fig.update_layout(
        barmode="group",
        title="Walk-forward — realized returns and rank IC per fold",
        xaxis_title="Fold",
        yaxis_title="Actual 63-day return",
        yaxis2=dict(title="Spearman rank corr", overlaying="y", side="right"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


def plot_rocm_training_curve(mse_list) -> go.Figure:
    epochs = list(range(1, len(mse_list) + 1))
    fig = px.line(
        x=epochs,
        y=mse_list,
        title="ROCm MLP — training loss (MSE) per epoch",
        labels={"x": "Epoch", "y": "Train MSE"},
    )
    fig.add_annotation(
        x=epochs[-1],
        y=mse_list[-1],
        text=f"final MSE {mse_list[-1]:.4f}",
        showarrow=True,
        arrowhead=1,
    )
    return fig


def plot_rankings_scatter(rankings_df: pd.DataFrame, highlight_tickers=None, caps=(0.35, 0.50, 0.80)) -> go.Figure:
    d = rankings_df.copy()
    fig = px.scatter(
        d,
        x="volatility_60d",
        y="predicted_63d_return",
        color="sector",
        hover_data=["ticker", "industry"],
        title="Latest rankings — predicted return vs 60-day volatility",
    )
    for cap in caps:
        fig.add_vline(x=cap, line_dash="dot", line_color="grey", annotation_text=f"cap {cap}")
    if highlight_tickers:
        sel = d[d["ticker"].isin(highlight_tickers)]
        fig.add_trace(
            go.Scatter(
                x=sel["volatility_60d"],
                y=sel["predicted_63d_return"],
                mode="markers",
                marker=dict(size=13, color="black", symbol="x"),
                name="Selected",
                hovertext=sel["ticker"],
            )
        )
    fig.update_layout(xaxis_title="60-day volatility", yaxis_title="Predicted 63-day return")
    return fig


def plot_portfolio_risk_return(summary_df: pd.DataFrame) -> go.Figure:
    d = summary_df.copy()
    fig = px.scatter(
        d,
        x="avg_volatility_60d_weighted",
        y="expected_63d_return_weighted",
        text="profile",
        color="profile",
        title="Portfolio profiles — expected return vs volatility",
    )
    fig.update_traces(textposition="top center", marker=dict(size=16))
    fig.update_layout(
        xaxis_title="Avg 60-day volatility (weighted)",
        yaxis_title="Expected 63-day return (weighted)",
        showlegend=False,
    )
    return fig


def plot_sector_allocation(sector_weights_df: pd.DataFrame, profile: str, cap: float = 0.30) -> go.Figure:
    d = sector_weights_df[sector_weights_df["profile"] == profile].sort_values("weight", ascending=True)
    fig = px.bar(d, x="weight", y="sector", orientation="h", title=f"{profile.title()} — sector allocation")
    fig.add_vline(x=cap, line_dash="dash", line_color="red", annotation_text=f"{int(cap * 100)}% cap")
    fig.update_layout(xaxis_title="Weight", yaxis_title="")
    return fig


def plot_portfolio_correlation(returns_wide: pd.DataFrame) -> go.Figure:
    corr = returns_wide.corr()
    fig = px.imshow(
        corr,
        text_auto=".2f",
        color_continuous_scale="RdBu",
        zmin=-1,
        zmax=1,
        title="Holding correlation (daily returns)",
    )
    return fig

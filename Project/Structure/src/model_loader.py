"""Read precomputed model / portfolio / walk-forward artifacts for the app.

Reads exclusively from the single ``liora.duckdb`` (via src/db.py) — no CSV,
no ML libraries, never trains anything. The 5-model leaderboard is preserved as
static rows in ``model_metrics`` (4 frozen baselines + the live XGBoost+Optuna
production model). Function signatures are unchanged from the CSV era so the
Streamlit layer (wrapped in ``@st.cache_data``) is untouched.
"""

from __future__ import annotations

import pandas as pd

from . import db

# Portfolio-construction constants — kept identical to build_portfolios so the
# Recommender questionnaire mapping is provably the same as how portfolios are
# built. We only READ precomputed portfolio tables here.
PORTFOLIO_SIZE = 10
MAX_SECTOR_WEIGHT = 0.30
MAX_STOCK_WEIGHT = 0.20

PROFILES = {
    "conservative": {
        "max_volatility_60d": 0.35,
        "description": "Lower-volatility picks first; accepts lower expected return for a smoother ride.",
    },
    "balanced": {
        "max_volatility_60d": 0.50,
        "description": "Middle risk profile; allows more volatile stocks but still filters extreme names.",
    },
    "aggressive": {
        "max_volatility_60d": 0.80,
        "description": "Higher risk profile; allows high-volatility stocks if the model score is strong.",
    },
}

# Registry of the 5 models (model_key -> display label). The production model is
# `xgboost_no_history` (XGBoost + Optuna); the other four are frozen baselines
# kept for the comparison leaderboard. File stems are retained for reference /
# ingest, but reads now go to DuckDB tables keyed by model_key.
MODELS = {
    "baseline_ridge": {
        "label": "Ridge (baseline)",
        "metrics": "model_metrics.csv",
        "predictions": "predictions.csv",
        "rankings": "latest_rankings.csv",
        "feature_importance": None,
        "training_history": None,
    },
    "random_forest": {
        "label": "Random Forest (with history_days)",
        "metrics": "random_forest_metrics.csv",
        "predictions": "random_forest_predictions.csv",
        "rankings": "random_forest_latest_rankings.csv",
        "feature_importance": "random_forest_feature_importance.csv",
        "training_history": None,
    },
    "random_forest_no_history": {
        "label": "Random Forest (no history_days)",
        "metrics": "random_forest_no_history_metrics.csv",
        "predictions": "random_forest_no_history_predictions.csv",
        "rankings": "random_forest_no_history_latest_rankings.csv",
        "feature_importance": "random_forest_no_history_feature_importance.csv",
        "training_history": None,
    },
    "xgboost_no_history": {
        "label": "XGBoost + Optuna — production",
        "metrics": "xgboost_no_history_metrics.csv",
        "predictions": "xgboost_no_history_predictions.csv",
        "rankings": "xgboost_no_history_latest_rankings.csv",
        "feature_importance": "xgboost_no_history_feature_importance.csv",
        "training_history": None,
    },
    "pytorch_mlp_rocm": {
        "label": "PyTorch MLP (ROCm GPU)",
        "metrics": "rocm_model_metrics.csv",
        "predictions": "rocm_predictions.csv",
        "rankings": "rocm_latest_rankings.csv",
        "feature_importance": None,
        "training_history": "rocm_training_history.json",
    },
}

# The production model key — single source of truth for app / portfolios.
PRODUCTION_MODEL_KEY = "xgboost_no_history"

WALK_FORWARD = {
    "summary": "walk_forward_rf_no_history_summary.csv",
    "folds": "walk_forward_rf_no_history_fold_metrics.csv",
    "feature_importance": "walk_forward_rf_no_history_feature_importance.csv",
    "predictions": "walk_forward_rf_no_history_predictions.csv",
}

FEATURE_GLOSSARY = {
    "ret_5d": "5-day price return — short-term momentum.",
    "ret_20d": "20-day (≈1 month) price return.",
    "ret_60d": "60-day (≈3 month) price return — medium-term momentum.",
    "mean_return_20d": "Average daily return over the last 20 days, annualized.",
    "mean_return_60d": "Average daily return over the last 60 days, annualized.",
    "volatility_20d": "20-day volatility — how jumpy the stock is short-term.",
    "volatility_60d": "60-day volatility — the risk measure used for the portfolio caps.",
    "log_avg_volume_20d": "Log of average 20-day volume — a liquidity proxy.",
    "drawdown_252d": "How far below its 1-year peak the stock currently sits.",
    "history_days": "How many trading days of history the stock has — a leak-prone "
    "shortcut that was removed in the production model.",
}

# Normalized metric columns shared across all models (matches model_metrics).
_METRIC_COLS = [
    "model",
    "label",
    "model_key",
    "mae",
    "rmse",
    "spearman_rank_corr",
    "test_universe_avg_actual_return",
    "top5_avg_actual_return",
    "test_start",
    "test_end",
    "test_rows",
    "test_tickers",
    "device",
    "final_train_mse",
]


def _read(sql: str, params=None) -> pd.DataFrame | None:
    """Read-only query → DataFrame, or None when the result is empty."""
    df = db.query(sql, params)
    return None if df is None or df.empty else df


def load_model_metrics() -> pd.DataFrame:
    """The 5-model leaderboard, normalized to the shared metric columns."""
    df = db.query("SELECT * FROM model_metrics")
    if df is None or df.empty:
        return pd.DataFrame(columns=_METRIC_COLS)
    keep = [c for c in _METRIC_COLS if c in df.columns]
    return df[keep]


def load_predictions(model_key: str):
    df = _read(
        "SELECT date, ticker, sector, target_63d_return, predicted_63d_return "
        "FROM model_predictions WHERE model_key = ?",
        [model_key],
    )
    if df is not None:
        df["date"] = pd.to_datetime(df["date"])
    return df


def load_rankings(model_key: str):
    df = _read(
        "SELECT date, ticker, sector, industry, predicted_63d_return, "
        "volatility_60d, ret_60d FROM model_rankings WHERE model_key = ? "
        "ORDER BY predicted_63d_return DESC",
        [model_key],
    )
    if df is not None:
        df["date"] = pd.to_datetime(df["date"])
        df = df.reset_index(drop=True)
    return df


def load_feature_importance(model_key: str):
    if not MODELS[model_key]["feature_importance"]:
        return None  # linear / neural models expose no tree importances
    return _read(
        "SELECT feature, importance FROM feature_importance "
        "WHERE model_key = ? ORDER BY importance DESC",
        [model_key],
    )


def load_rocm_history():
    df = _read(
        "SELECT train_mse FROM rocm_training_history "
        "WHERE model_key = 'pytorch_mlp_rocm' ORDER BY epoch"
    )
    return None if df is None else df["train_mse"].tolist()


def load_walkforward_summary():
    return _read("SELECT * FROM walk_forward_summary")


def load_walkforward_folds():
    return _read("SELECT * FROM walk_forward_folds ORDER BY fold")


def load_walkforward_feature_importance():
    return _read(
        "SELECT feature, importance FROM walk_forward_feature_importance "
        "ORDER BY importance DESC"
    )


def load_portfolio_summary():
    return _read("SELECT * FROM portfolio_summary")


def load_portfolio_recommendations():
    df = _read("SELECT * FROM portfolio_recommendations")
    if df is not None and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
    return df


def load_portfolio_sector_weights():
    return _read("SELECT * FROM portfolio_sector_weights")


def map_questionnaire_to_profile(volatility_comfort: str) -> str:
    """Map a risk answer to one of the 3 precomputed profiles (read-only)."""
    return {
        "Low": "conservative",
        "Medium": "balanced",
        "High": "aggressive",
    }.get(volatility_comfort, "balanced")

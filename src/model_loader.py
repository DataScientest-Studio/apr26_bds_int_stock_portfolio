"""Read precomputed model / portfolio / walk-forward artifacts for the Streamlit app.

Pure pandas/json — imports NO ML libraries and never trains anything. Every
artifact is read from the dated model export (see ``MODEL_DIR``). The Streamlit
layer wraps these loaders in ``@st.cache_data``.

Data-snapshot note: these artifacts were trained on the Alpaca S&P 500 export
(503 tickers, 2021-06-09 → 2026-06-05). The live root ``data/`` is a *different*
snapshot (yfinance, 543 tickers incl. DAX 40). The app shows a banner on every
page that reads these files.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

# Single source of truth for the (dated) model export location.
# Change this one line if the export folder is regenerated under a new date.
MODEL_DIR = Path(__file__).resolve().parent.parent / "mac-2026-06-08" / "models"

# Portfolio-construction constants — copied verbatim from
# mac-2026-06-08/models/build_portfolios.py so the Recommender's questionnaire
# mapping is provably identical to how the portfolios were built. We only READ
# the precomputed portfolio CSVs here; we never re-run the selection.
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

# Registry of the 5 trained models and their artifact file stems.
# feature_importance / training_history are absent for some models (-> None).
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
        "label": "Random Forest (no history_days) — production",
        "metrics": "random_forest_no_history_metrics.csv",
        "predictions": "random_forest_no_history_predictions.csv",
        "rankings": "random_forest_no_history_latest_rankings.csv",
        "feature_importance": "random_forest_no_history_feature_importance.csv",
        "training_history": None,
    },
    "xgboost_no_history": {
        "label": "XGBoost (no history_days)",
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

WALK_FORWARD = {
    "summary": "walk_forward_rf_no_history_summary.csv",
    "folds": "walk_forward_rf_no_history_fold_metrics.csv",
    "feature_importance": "walk_forward_rf_no_history_feature_importance.csv",
    "predictions": "walk_forward_rf_no_history_predictions.csv",
}

# Plain-language glossary for the Model Explorer feature-importance section.
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

# Normalized metric columns shared across all *_metrics.csv files.
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


def _path(name) -> Path:
    return name if isinstance(name, Path) else MODEL_DIR / name


def safe_read_csv(name, **kwargs):
    """Read a CSV from ``MODEL_DIR``; return ``None`` if the file is missing."""
    path = _path(name)
    if not path.exists():
        return None
    return pd.read_csv(path, **kwargs)


def safe_read_json(name):
    """Read a JSON file from ``MODEL_DIR``; return ``None`` if missing."""
    path = _path(name)
    if not path.exists():
        return None
    with open(path) as handle:
        return json.load(handle)


def load_model_metrics() -> pd.DataFrame:
    """Concatenate every model's metrics into one tidy, normalized table.

    Handles the heterogeneous schemas: ``model_metrics.csv`` (Ridge) has no
    ``model`` column; ``rocm_model_metrics.csv`` adds ``device`` and
    ``final_train_mse``.
    """
    rows = []
    for key, cfg in MODELS.items():
        df = safe_read_csv(cfg["metrics"])
        if df is None or df.empty:
            continue
        row = df.iloc[0].to_dict()
        if not str(row.get("model", "")).strip():
            row["model"] = key
        row["model_key"] = key
        row["label"] = cfg["label"]
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=_METRIC_COLS)
    out = pd.DataFrame(rows)
    keep = [c for c in _METRIC_COLS if c in out.columns]
    return out[keep]


def load_predictions(model_key: str):
    return safe_read_csv(MODELS[model_key]["predictions"], parse_dates=["date"])


def load_rankings(model_key: str):
    df = safe_read_csv(MODELS[model_key]["rankings"], parse_dates=["date"])
    if df is not None:
        df = df.sort_values("predicted_63d_return", ascending=False).reset_index(drop=True)
    return df


def load_feature_importance(model_key: str):
    name = MODELS[model_key]["feature_importance"]
    if not name:
        return None
    df = safe_read_csv(name)
    if df is not None:
        df = df.sort_values("importance", ascending=False).reset_index(drop=True)
    return df


def load_rocm_history():
    data = safe_read_json(MODELS["pytorch_mlp_rocm"]["training_history"])
    if not data:
        return None
    return data.get("train_mse")


def load_walkforward_summary():
    return safe_read_csv(WALK_FORWARD["summary"])


def load_walkforward_folds():
    df = safe_read_csv(WALK_FORWARD["folds"])
    if df is not None:
        df = df.sort_values("fold").reset_index(drop=True)
    return df


def load_walkforward_feature_importance():
    df = safe_read_csv(WALK_FORWARD["feature_importance"])
    if df is not None:
        df = df.sort_values("importance", ascending=False).reset_index(drop=True)
    return df


def load_portfolio_summary():
    return safe_read_csv("portfolio_summary.csv")


def load_portfolio_recommendations():
    return safe_read_csv("portfolio_recommendations.csv", parse_dates=["date"])


def load_portfolio_sector_weights():
    return safe_read_csv("portfolio_sector_weights.csv")


def map_questionnaire_to_profile(volatility_comfort: str) -> str:
    """Map a risk answer to one of the 3 precomputed profiles (read-only).

    Mirrors the volatility-cap ordering in ``build_portfolios.py``
    (0.35 / 0.50 / 0.80) without re-running portfolio selection.
    """
    return {
        "Low": "conservative",
        "Medium": "balanced",
        "High": "aggressive",
    }.get(volatility_comfort, "balanced")

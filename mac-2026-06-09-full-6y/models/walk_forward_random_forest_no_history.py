"""Walk-forward backtest for Random Forest without history_days.

The model is retrained several times on expanding historical windows. Each fold
tests the next 63 trading days, matching the 63-day forward-return target.

Run from the project export folder:
    python models/walk_forward_random_forest_no_history.py
"""

from __future__ import annotations

import pickle
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

TARGET_HORIZON_DAYS = 63
INITIAL_TRAIN_DATES = 504
TEST_WINDOW_DATES = 63
STEP_DATES = 63
RANDOM_SEED = 42


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = pd.read_csv(DATA_DIR / "prices_long.csv", parse_dates=["date"])
    tickers = pd.read_csv(DATA_DIR / "tickers.csv")
    return prices.sort_values(["ticker", "date"]).reset_index(drop=True), tickers


def add_features(prices: pd.DataFrame, tickers: pd.DataFrame) -> pd.DataFrame:
    df = prices.copy()
    grouped = df.groupby("ticker", group_keys=False)

    df["daily_return"] = grouped["adj_close"].pct_change()
    df["ret_5d"] = grouped["adj_close"].pct_change(5)
    df["ret_20d"] = grouped["adj_close"].pct_change(20)
    df["ret_60d"] = grouped["adj_close"].pct_change(60)
    df["mean_return_20d"] = grouped["daily_return"].rolling(20).mean().reset_index(level=0, drop=True) * 252
    df["mean_return_60d"] = grouped["daily_return"].rolling(60).mean().reset_index(level=0, drop=True) * 252
    df["volatility_20d"] = grouped["daily_return"].rolling(20).std().reset_index(level=0, drop=True) * np.sqrt(252)
    df["volatility_60d"] = grouped["daily_return"].rolling(60).std().reset_index(level=0, drop=True) * np.sqrt(252)
    df["avg_volume_20d"] = grouped["volume"].rolling(20).mean().reset_index(level=0, drop=True)
    df["log_avg_volume_20d"] = np.log1p(df["avg_volume_20d"])

    rolling_high = grouped["adj_close"].rolling(252, min_periods=60).max().reset_index(level=0, drop=True)
    df["drawdown_252d"] = df["adj_close"] / rolling_high - 1
    df["target_63d_return"] = grouped["adj_close"].shift(-TARGET_HORIZON_DAYS) / df["adj_close"] - 1

    return df.merge(tickers[["ticker", "sector", "industry"]], on="ticker", how="left")


def prepare_model_matrix(feature_rows: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    numeric_features = [
        "ret_5d",
        "ret_20d",
        "ret_60d",
        "mean_return_20d",
        "mean_return_60d",
        "volatility_20d",
        "volatility_60d",
        "log_avg_volume_20d",
        "drawdown_252d",
    ]

    rows = feature_rows.copy()
    rows["sector"] = rows["sector"].fillna("Unknown")
    sector_dummies = pd.get_dummies(rows["sector"], prefix="sector", dtype=float)
    model_df = pd.concat([rows, sector_dummies], axis=1)
    feature_cols = numeric_features + list(sector_dummies.columns)
    return model_df.dropna(subset=feature_cols + ["target_63d_return"]).copy(), feature_cols


def make_model() -> RandomForestRegressor:
    return RandomForestRegressor(
        n_estimators=250,
        max_depth=10,
        min_samples_leaf=20,
        max_features="sqrt",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )


def evaluate_fold(
    fold_id: int,
    train_rows: pd.DataFrame,
    test_rows: pd.DataFrame,
) -> dict[str, object]:
    error = test_rows["predicted_63d_return"] - test_rows["target_63d_return"]
    top5_by_date = (
        test_rows.sort_values(["date", "predicted_63d_return"], ascending=[True, False])
        .groupby("date")
        .head(5)
    )
    top10_by_date = (
        test_rows.sort_values(["date", "predicted_63d_return"], ascending=[True, False])
        .groupby("date")
        .head(10)
    )

    return {
        "fold": fold_id,
        "train_start": train_rows["date"].min().date().isoformat(),
        "train_end": train_rows["date"].max().date().isoformat(),
        "test_start": test_rows["date"].min().date().isoformat(),
        "test_end": test_rows["date"].max().date().isoformat(),
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "test_tickers": test_rows["ticker"].nunique(),
        "mae": float(error.abs().mean()),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "spearman_rank_corr": float(
            test_rows["predicted_63d_return"].corr(test_rows["target_63d_return"], method="spearman")
        ),
        "universe_avg_actual_return": float(test_rows["target_63d_return"].mean()),
        "top5_avg_actual_return": float(top5_by_date["target_63d_return"].mean()),
        "top10_avg_actual_return": float(top10_by_date["target_63d_return"].mean()),
    }


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    prices, tickers = load_data()
    features = add_features(prices, tickers)
    supervised, feature_cols = prepare_model_matrix(features)
    dates = supervised["date"].drop_duplicates().sort_values().reset_index(drop=True)

    fold_metrics: list[dict[str, object]] = []
    prediction_frames: list[pd.DataFrame] = []
    importance_frames: list[pd.DataFrame] = []

    fold_id = 1
    start_idx = INITIAL_TRAIN_DATES
    while start_idx + TEST_WINDOW_DATES <= len(dates):
        train_end_date = dates.iloc[start_idx - 1]
        test_start_date = dates.iloc[start_idx]
        test_end_date = dates.iloc[start_idx + TEST_WINDOW_DATES - 1]

        train_rows = supervised[supervised["date"] <= train_end_date].copy()
        test_rows = supervised[
            (supervised["date"] >= test_start_date) & (supervised["date"] <= test_end_date)
        ].copy()

        model = make_model()
        model.fit(train_rows[feature_cols], train_rows["target_63d_return"])
        test_rows["predicted_63d_return"] = model.predict(test_rows[feature_cols])

        metrics = evaluate_fold(fold_id, train_rows, test_rows)
        fold_metrics.append(metrics)
        prediction_frames.append(
            test_rows[["date", "ticker", "sector", "target_63d_return", "predicted_63d_return"]].assign(
                fold=fold_id
            )
        )
        importance_frames.append(
            pd.DataFrame(
                {
                    "fold": fold_id,
                    "feature": feature_cols,
                    "importance": model.feature_importances_,
                }
            )
        )

        print(
            f"fold={fold_id} train={metrics['train_start']}..{metrics['train_end']} "
            f"test={metrics['test_start']}..{metrics['test_end']} "
            f"mae={metrics['mae']:.4f} spearman={metrics['spearman_rank_corr']:.4f} "
            f"top5={metrics['top5_avg_actual_return']:.4f}",
            flush=True,
        )

        fold_id += 1
        start_idx += STEP_DATES

    metrics_df = pd.DataFrame(fold_metrics)
    predictions_df = pd.concat(prediction_frames, ignore_index=True)
    importance_df = pd.concat(importance_frames, ignore_index=True)
    avg_importance = (
        importance_df.groupby("feature", as_index=False)["importance"]
        .mean()
        .sort_values("importance", ascending=False)
    )

    summary = pd.DataFrame(
        [
            {
                "model": "walk_forward_random_forest_no_history",
                "folds": len(metrics_df),
                "mean_mae": metrics_df["mae"].mean(),
                "mean_rmse": metrics_df["rmse"].mean(),
                "mean_spearman_rank_corr": metrics_df["spearman_rank_corr"].mean(),
                "mean_universe_avg_actual_return": metrics_df["universe_avg_actual_return"].mean(),
                "mean_top5_avg_actual_return": metrics_df["top5_avg_actual_return"].mean(),
                "mean_top10_avg_actual_return": metrics_df["top10_avg_actual_return"].mean(),
                "positive_top5_folds": int(
                    (metrics_df["top5_avg_actual_return"] > metrics_df["universe_avg_actual_return"]).sum()
                ),
            }
        ]
    )

    metrics_df.to_csv(MODEL_DIR / "walk_forward_rf_no_history_fold_metrics.csv", index=False)
    summary.to_csv(MODEL_DIR / "walk_forward_rf_no_history_summary.csv", index=False)
    predictions_df.to_csv(MODEL_DIR / "walk_forward_rf_no_history_predictions.csv", index=False)
    avg_importance.to_csv(MODEL_DIR / "walk_forward_rf_no_history_feature_importance.csv", index=False)

    with (MODEL_DIR / "walk_forward_rf_no_history_last_model.pkl").open("wb") as f:
        pickle.dump({"model": model, "feature_cols": feature_cols}, f)

    print()
    print("Walk-forward summary:")
    print(summary.T.to_string(header=False))
    print()
    print("Average feature importance:")
    print(avg_importance.head(12).to_string(index=False))


if __name__ == "__main__":
    main()

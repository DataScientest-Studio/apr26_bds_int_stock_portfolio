"""Train a Random Forest stock return model.

This model uses the same feature and target setup as the Ridge and ROCm
experiments, then adds feature importance for beginner-friendly interpretation.

Run from the project export folder:
    python models/train_random_forest_model.py
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
TEST_START_DATE = pd.Timestamp("2025-01-01")
RANDOM_SEED = 42


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    prices = pd.read_csv(DATA_DIR / "prices_long.csv", parse_dates=["date"])
    tickers = pd.read_csv(DATA_DIR / "tickers.csv")
    prices = prices.sort_values(["ticker", "date"]).reset_index(drop=True)
    return prices, tickers


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
    df["history_days"] = grouped.cumcount() + 1
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
        "history_days",
    ]

    rows = feature_rows.copy()
    rows["sector"] = rows["sector"].fillna("Unknown")
    sector_dummies = pd.get_dummies(rows["sector"], prefix="sector", dtype=float)
    model_df = pd.concat([rows, sector_dummies], axis=1)
    feature_cols = numeric_features + list(sector_dummies.columns)
    return model_df.dropna(subset=feature_cols), feature_cols


def time_split(supervised: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.Timestamp]:
    train_rows = supervised[supervised["date"] < TEST_START_DATE].copy()
    test_rows = supervised[supervised["date"] >= TEST_START_DATE].copy()

    if not train_rows.empty and not test_rows.empty:
        return train_rows, test_rows, TEST_START_DATE

    dates = supervised["date"].drop_duplicates().sort_values().reset_index(drop=True)
    if len(dates) < 4:
        raise ValueError("Not enough supervised dates to create a time-based train/test split.")

    split_idx = max(1, int(len(dates) * 0.75))
    split_idx = min(split_idx, len(dates) - 1)
    split_date = pd.Timestamp(dates.iloc[split_idx])
    train_rows = supervised[supervised["date"] < split_date].copy()
    test_rows = supervised[supervised["date"] >= split_date].copy()
    return train_rows, test_rows, split_date


def evaluate(test_rows: pd.DataFrame, train_rows: pd.DataFrame, split_date: pd.Timestamp) -> pd.DataFrame:
    error = test_rows["predicted_63d_return"] - test_rows["target_63d_return"]
    top5_by_date = (
        test_rows.sort_values(["date", "predicted_63d_return"], ascending=[True, False])
        .groupby("date")
        .head(5)
    )

    return pd.DataFrame(
        [
            {
                "model": "random_forest",
                "train_start": train_rows["date"].min().date().isoformat(),
                "train_end": train_rows["date"].max().date().isoformat(),
                "test_start": test_rows["date"].min().date().isoformat(),
                "test_end": test_rows["date"].max().date().isoformat(),
                "split_date": split_date.date().isoformat(),
                "train_rows": len(train_rows),
                "test_rows": len(test_rows),
                "test_tickers": test_rows["ticker"].nunique(),
                "mae": float(error.abs().mean()),
                "rmse": float(np.sqrt(np.mean(error**2))),
                "spearman_rank_corr": float(
                    test_rows["predicted_63d_return"].corr(
                        test_rows["target_63d_return"], method="spearman"
                    )
                ),
                "test_universe_avg_actual_return": float(test_rows["target_63d_return"].mean()),
                "top5_avg_actual_return": float(top5_by_date["target_63d_return"].mean()),
            }
        ]
    )


def main() -> None:
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    prices, tickers = load_data()
    features = add_features(prices, tickers)
    model_df, feature_cols = prepare_model_matrix(features)

    supervised = model_df.dropna(subset=["target_63d_return"]).copy()
    train_rows, test_rows, split_date = time_split(supervised)

    if train_rows.empty or test_rows.empty:
        raise ValueError("Train/test split produced an empty dataset.")

    model = RandomForestRegressor(
        n_estimators=400,
        max_depth=10,
        min_samples_leaf=20,
        max_features="sqrt",
        random_state=RANDOM_SEED,
        n_jobs=-1,
    )
    model.fit(train_rows[feature_cols], train_rows["target_63d_return"])

    test_rows["predicted_63d_return"] = model.predict(test_rows[feature_cols])
    metrics = evaluate(test_rows, train_rows, split_date)

    latest_date = model_df["date"].max()
    latest_rows = model_df[model_df["date"] == latest_date].copy()
    latest_rows["predicted_63d_return"] = model.predict(latest_rows[feature_cols])
    latest_rankings = latest_rows.sort_values("predicted_63d_return", ascending=False)[
        ["date", "ticker", "sector", "industry", "predicted_63d_return", "volatility_60d", "ret_60d"]
    ]

    feature_importance = (
        pd.DataFrame({"feature": feature_cols, "importance": model.feature_importances_})
        .sort_values("importance", ascending=False)
        .reset_index(drop=True)
    )

    with (MODEL_DIR / "random_forest_model.pkl").open("wb") as f:
        pickle.dump({"model": model, "feature_cols": feature_cols}, f)

    metrics.to_csv(MODEL_DIR / "random_forest_metrics.csv", index=False)
    test_rows[
        ["date", "ticker", "sector", "target_63d_return", "predicted_63d_return"]
    ].sort_values(["date", "predicted_63d_return"], ascending=[True, False]).to_csv(
        MODEL_DIR / "random_forest_predictions.csv", index=False
    )
    latest_rankings.to_csv(MODEL_DIR / "random_forest_latest_rankings.csv", index=False)
    feature_importance.to_csv(MODEL_DIR / "random_forest_feature_importance.csv", index=False)

    print("Random Forest training complete")
    print(f"Train rows: {len(train_rows):,} | Test rows: {len(test_rows):,}")
    print(f"Split date: {split_date.date().isoformat()}")
    print(metrics.T.to_string(header=False))
    print()
    print("Top feature importances:")
    print(feature_importance.head(12).to_string(index=False))
    print()
    print("Top latest predicted 63-day returns:")
    print(latest_rankings.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

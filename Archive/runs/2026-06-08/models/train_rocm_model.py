"""Train a ROCm/PyTorch baseline model on the Strix Halo GPU.

This keeps the same data split and feature idea as train_first_model.py, but
uses a small PyTorch neural network and requires a visible ROCm device.

Run from the project export folder:
    HSA_ENABLE_DXG_DETECTION=1 python models/train_rocm_model.py
"""

from __future__ import annotations

import json
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd
import torch
from torch import nn
from torch.utils.data import DataLoader, TensorDataset


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
MODEL_DIR = BASE_DIR / "models"

TARGET_HORIZON_DAYS = 63
TEST_START_DATE = pd.Timestamp("2025-01-01")
RANDOM_SEED = 42
BATCH_SIZE = int(os.getenv("ROCM_BATCH_SIZE", "8192"))
EPOCHS = int(os.getenv("ROCM_EPOCHS", "80"))
LEARNING_RATE = 1e-3
WEIGHT_DECAY = 1e-4


class ReturnRegressor(nn.Module):
    def __init__(self, n_features: int) -> None:
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(n_features, 64),
            nn.ReLU(),
            nn.Dropout(0.10),
            nn.Linear(64, 32),
            nn.ReLU(),
            nn.Linear(32, 1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.net(x).squeeze(-1)


def set_seed() -> None:
    random.seed(RANDOM_SEED)
    np.random.seed(RANDOM_SEED)
    torch.manual_seed(RANDOM_SEED)
    torch.cuda.manual_seed_all(RANDOM_SEED)


def get_device() -> torch.device:
    if not torch.cuda.is_available():
        raise RuntimeError(
            "No ROCm GPU visible to PyTorch. Run with HSA_ENABLE_DXG_DETECTION=1 "
            "and verify rocminfo shows gfx1151."
        )
    return torch.device("cuda")


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

    df = df.merge(tickers[["ticker", "sector", "industry"]], on="ticker", how="left")
    return df


def prepare_model_matrix(feature_rows: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
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
    model_df = model_df.dropna(subset=feature_cols)
    return model_df, feature_cols, numeric_features


def scale_features(
    train_rows: pd.DataFrame,
    other_rows: pd.DataFrame,
    feature_cols: list[str],
    numeric_features: list[str],
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, dict[str, float]]]:
    means = train_rows[numeric_features].mean()
    stds = train_rows[numeric_features].std().replace(0, 1)

    train_x = train_rows[feature_cols].copy()
    other_x = other_rows[feature_cols].copy()
    train_x[numeric_features] = (train_x[numeric_features] - means) / stds
    other_x[numeric_features] = (other_x[numeric_features] - means) / stds

    scaler = {
        "means": means.to_dict(),
        "stds": stds.to_dict(),
    }
    return train_x, other_x, scaler


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


def to_tensor(df: pd.DataFrame, device: torch.device) -> torch.Tensor:
    return torch.tensor(df.to_numpy(dtype=np.float32), device=device)


def train_model(
    train_x: pd.DataFrame,
    train_y: pd.Series,
    device: torch.device,
) -> tuple[ReturnRegressor, list[float]]:
    x = to_tensor(train_x, device)
    y = torch.tensor(train_y.to_numpy(dtype=np.float32), device=device)

    dataset = TensorDataset(x, y)
    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)

    model = ReturnRegressor(train_x.shape[1]).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    loss_fn = nn.MSELoss()

    losses: list[float] = []
    model.train()
    for epoch in range(1, EPOCHS + 1):
        epoch_loss = 0.0
        for batch_x, batch_y in loader:
            optimizer.zero_grad(set_to_none=True)
            loss = loss_fn(model(batch_x), batch_y)
            loss.backward()
            optimizer.step()
            epoch_loss += loss.item() * len(batch_x)

        epoch_loss /= len(dataset)
        losses.append(epoch_loss)
        if epoch == 1 or epoch % 50 == 0:
            print(f"epoch={epoch:03d} train_mse={epoch_loss:.6f}", flush=True)

    torch.cuda.synchronize(device)
    return model, losses


@torch.no_grad()
def add_predictions(
    model: ReturnRegressor,
    rows: pd.DataFrame,
    x: pd.DataFrame,
    device: torch.device,
) -> pd.DataFrame:
    model.eval()
    out = rows.copy()
    predictions = model(to_tensor(x, device)).detach().cpu().numpy()
    out["predicted_63d_return"] = predictions
    return out


def evaluate(test_rows: pd.DataFrame, train_rows: pd.DataFrame, device_name: str, final_loss: float) -> pd.DataFrame:
    error = test_rows["predicted_63d_return"] - test_rows["target_63d_return"]
    top5_by_date = (
        test_rows.sort_values(["date", "predicted_63d_return"], ascending=[True, False])
        .groupby("date")
        .head(5)
    )

    metrics = {
        "model": "pytorch_mlp_rocm",
        "device": device_name,
        "train_start": train_rows["date"].min().date().isoformat(),
        "train_end": train_rows["date"].max().date().isoformat(),
        "test_start": test_rows["date"].min().date().isoformat(),
        "test_end": test_rows["date"].max().date().isoformat(),
        "train_rows": len(train_rows),
        "test_rows": len(test_rows),
        "test_tickers": test_rows["ticker"].nunique(),
        "final_train_mse": final_loss,
        "mae": float(error.abs().mean()),
        "rmse": float(np.sqrt(np.mean(error**2))),
        "spearman_rank_corr": float(
            test_rows["predicted_63d_return"].corr(test_rows["target_63d_return"], method="spearman")
        ),
        "test_universe_avg_actual_return": float(test_rows["target_63d_return"].mean()),
        "top5_avg_actual_return": float(top5_by_date["target_63d_return"].mean()),
    }
    return pd.DataFrame([metrics])


def main() -> None:
    set_seed()
    device = get_device()
    device_name = torch.cuda.get_device_name(0)
    print(f"Training on ROCm device: {device_name}", flush=True)
    print(f"Training config: epochs={EPOCHS}, batch_size={BATCH_SIZE}", flush=True)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)

    prices, tickers = load_data()
    features = add_features(prices, tickers)
    model_df, feature_cols, numeric_features = prepare_model_matrix(features)

    supervised = model_df.dropna(subset=["target_63d_return"]).copy()
    train_rows, test_rows, split_date = time_split(supervised)

    if train_rows.empty or test_rows.empty:
        raise ValueError("Train/test split produced an empty dataset. Check date range and data files.")

    train_x, test_x, scaler = scale_features(train_rows, test_rows, feature_cols, numeric_features)
    model, losses = train_model(train_x, train_rows["target_63d_return"], device)

    test_predictions = add_predictions(model, test_rows, test_x, device)
    metrics = evaluate(test_predictions, train_rows, device_name, losses[-1])

    latest_date = model_df["date"].max()
    latest_rows = model_df[model_df["date"] == latest_date].copy()
    _, latest_x, _ = scale_features(train_rows, latest_rows, feature_cols, numeric_features)
    latest_rankings = add_predictions(model, latest_rows, latest_x, device)
    latest_rankings = latest_rankings.sort_values("predicted_63d_return", ascending=False)[
        ["date", "ticker", "sector", "industry", "predicted_63d_return", "volatility_60d", "ret_60d"]
    ]

    torch.save(
        {
            "model_state_dict": model.state_dict(),
            "feature_cols": feature_cols,
            "numeric_features": numeric_features,
            "scaler": scaler,
            "target_horizon_days": TARGET_HORIZON_DAYS,
            "test_start_date": test_rows["date"].min().date().isoformat(),
            "split_date": split_date.date().isoformat(),
            "device_name": device_name,
            "architecture": "ReturnRegressor(64,32)",
        },
        MODEL_DIR / "rocm_model.pt",
    )

    metrics.to_csv(MODEL_DIR / "rocm_model_metrics.csv", index=False)
    test_predictions[
        ["date", "ticker", "sector", "target_63d_return", "predicted_63d_return"]
    ].sort_values(["date", "predicted_63d_return"], ascending=[True, False]).to_csv(
        MODEL_DIR / "rocm_predictions.csv", index=False
    )
    latest_rankings.to_csv(MODEL_DIR / "rocm_latest_rankings.csv", index=False)
    (MODEL_DIR / "rocm_training_history.json").write_text(json.dumps({"train_mse": losses}, indent=2))

    print("ROCm model training complete")
    print(f"Train rows: {len(train_rows):,} | Test rows: {len(test_rows):,}")
    print(f"Split date: {split_date.date().isoformat()}")
    print(metrics.T.to_string(header=False))
    print()
    print("Top latest predicted 63-day returns:")
    print(latest_rankings.head(10).to_string(index=False))


if __name__ == "__main__":
    main()

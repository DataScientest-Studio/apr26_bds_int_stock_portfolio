"""Parity gate: SQL `features` view vs legacy pandas add_features().

Confirms the DuckDB window-function feature pipeline reproduces the original
pandas feature engineering column-for-column (nan-aware, tight tolerance)
before training switches to reading the SQL view. Run from Project/Structure:

    ../.venv/bin/python tests/parity_features.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

STRUCTURE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STRUCTURE))

from src.paths import DATA_DIR  # noqa: E402

TARGET_HORIZON_DAYS = 63


def add_features(prices: pd.DataFrame, tickers: pd.DataFrame) -> pd.DataFrame:
    """Reference pandas feature engineering (verbatim from the archived
    train_xgboost_no_history_model.py) — the ground truth src/features.sql must
    reproduce. Inlined so this test stays runnable after the legacy scripts move
    to Archive/.
    """
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


FEATURE_COLS = [
    "ret_5d", "ret_20d", "ret_60d",
    "mean_return_20d", "mean_return_60d",
    "volatility_20d", "volatility_60d",
    "avg_volume_20d", "log_avg_volume_20d",
    "drawdown_252d", "daily_return", "target_63d_return",
]


def main() -> int:
    prices = (
        pd.read_csv(DATA_DIR / "prices_long.csv", parse_dates=["date"])
        .sort_values(["ticker", "date"])
        .reset_index(drop=True)
    )
    tickers = pd.read_csv(DATA_DIR / "tickers.csv")
    pdf = add_features(prices, tickers).set_index(["ticker", "date"]).sort_index()

    con = duckdb.connect(str(DATA_DIR / "liora.duckdb"))
    con.execute((STRUCTURE / "src" / "features.sql").read_text())
    sdf = con.execute("SELECT * FROM features").df()
    sdf["date"] = pd.to_datetime(sdf["date"])
    sdf = sdf.set_index(["ticker", "date"]).sort_index()
    con.close()

    if len(pdf) != len(sdf):
        print(f"ROW COUNT MISMATCH pandas={len(pdf)} sql={len(sdf)}")
        return 1

    ok = True
    print(f"{'column':18s} {'nan_pattern':11s} {'values':8s} {'max_abs_diff'}")
    for c in FEATURE_COLS:
        a = pdf[c].to_numpy(dtype=float)
        b = sdf[c].to_numpy(dtype=float)
        nan_match = np.array_equal(np.isnan(a), np.isnan(b))
        mask = ~np.isnan(a) & ~np.isnan(b)
        max_diff = float(np.max(np.abs(a[mask] - b[mask]))) if mask.any() else 0.0
        values_ok = np.allclose(a, b, rtol=1e-7, atol=1e-9, equal_nan=True)
        ok = ok and nan_match and values_ok
        print(f"{c:18s} {str(nan_match):11s} {str(values_ok):8s} {max_diff:.3e}")

    print("\nFEATURE PARITY PASSED" if ok else "\nFEATURE PARITY FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

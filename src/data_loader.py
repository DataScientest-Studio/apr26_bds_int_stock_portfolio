"""Load CSV files used in the Streamlit app."""

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_tickers() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "tickers.csv")


def load_prices() -> pd.DataFrame:
    df = pd.read_csv(DATA_DIR / "prices_long.csv", parse_dates=["date"])
    df = df.sort_values(["ticker", "date"])
    df["daily_return"] = df.groupby("ticker")["adj_close"].pct_change()
    return df


def load_prices_wide() -> pd.DataFrame:
    """Wide adj_close matrix (date index × ticker columns) for correlations."""
    df = pd.read_csv(DATA_DIR / "prices_close_wide.csv", parse_dates=["date"])
    return df.set_index("date")


def compute_root_audit(prices: pd.DataFrame, tickers: pd.DataFrame) -> dict:
    """Compute data-quality metrics live from the CURRENT root dataset.

    The committed ``DATA_AUDIT.md`` describes an older Alpaca snapshot
    (503 tickers / 726k rows); the live root is now yfinance (543 tickers incl.
    DAX 40). Always derive the KPIs from the loaded CSV, never from the doc.
    """
    history = prices.groupby("ticker")["date"].count()
    ohlc_violation = (
        (prices["high"] < prices["low"])
        | (prices["open"] > prices["high"])
        | (prices["open"] < prices["low"])
        | (prices["close"] > prices["high"])
        | (prices["close"] < prices["low"])
    )
    return {
        "rows": len(prices),
        "tickers": prices["ticker"].nunique(),
        "trading_dates": prices["date"].nunique(),
        "date_min": prices["date"].min(),
        "date_max": prices["date"].max(),
        "hist_min": int(history.min()),
        "hist_median": float(history.median()),
        "hist_max": int(history.max()),
        "duplicates": int(prices.duplicated(subset=["date", "ticker"]).sum()),
        "ohlc_violations": int(ohlc_violation.sum()),
        "zero_volume_rows": int((prices["volume"] == 0).sum()),
        "history_per_ticker": history,
        "sector_counts": tickers["sector"].value_counts(),
        "index_counts": tickers["index"].value_counts() if "index" in tickers.columns else None,
    }

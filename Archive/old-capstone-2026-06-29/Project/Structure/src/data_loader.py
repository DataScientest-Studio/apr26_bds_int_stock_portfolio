"""Load the active run's price/ticker data for the Streamlit app and EDA.

Reads exclusively from the single ``liora.duckdb`` (via src/db.py) — no CSV.
Function signatures and return shapes are unchanged from the CSV era so every
caller (app.py, reports/make_figures.py) keeps working untouched.
"""

import pandas as pd

from . import db


def load_tickers() -> pd.DataFrame:
    """Ticker metadata: ticker, name, sector, industry, index, country."""
    return db.query(
        'SELECT ticker, name, sector, industry, "index", country '
        "FROM tickers ORDER BY ticker"
    )


def load_prices() -> pd.DataFrame:
    """Long OHLCV sorted by (ticker, date) with a per-ticker daily_return.

    daily_return = adj_close.pct_change() within each ticker — computed in SQL
    (LAG window) to match the old pandas groupby().pct_change() exactly.
    """
    df = db.query(
        "SELECT date, ticker, open, high, low, close, adj_close, volume, "
        "adj_close / LAG(adj_close) OVER (PARTITION BY ticker ORDER BY date) - 1 "
        "  AS daily_return "
        "FROM ohlcv ORDER BY ticker, date"
    )
    df["date"] = pd.to_datetime(df["date"])
    return df


def load_prices_wide() -> pd.DataFrame:
    """Wide adj_close matrix (date index × ticker columns) for correlations."""
    long = db.query("SELECT date, ticker, adj_close FROM ohlcv")
    long["date"] = pd.to_datetime(long["date"])
    return long.pivot(index="date", columns="ticker", values="adj_close").sort_index()


def compute_root_audit(prices: pd.DataFrame, tickers: pd.DataFrame) -> dict:
    """Compute data-quality metrics live from the loaded DuckDB dataset.

    Operates on the already-loaded frames (no I/O), so the KPIs always reflect
    whatever ``liora.duckdb`` currently holds rather than any stale document.
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

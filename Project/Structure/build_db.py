#!/usr/bin/env python3
"""DuckDB builder for the pipeline input: upstream store → liora.duckdb.

Copies EVERY ticker of the upstream S&P 500 store (path single-homed in bars.py; set
SP500_DUCKDB to override) into a single table `bars_1h(ticker, timestamp, open, high,
low, close, volume)` inside liora.duckdb — one frame per ticker through the canonical
bars.load_bars() transform, so the table is byte-identical with what the search plane
reads. That DuckDB is the only input L4 reads. No cleaning, no calendar, no QC here
(L4 asserts the clean-OHLCV contract when it reads). Re-run `make build-db` after the
upstream store changes.
"""
from pathlib import Path

import duckdb

import bars

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "liora.duckdb"
COLUMNS = ["ticker", "timestamp", "open", "high", "low", "close", "volume"]


def build_db(db_path=DB_PATH):
    tickers = bars.upstream_tickers()
    con = duckdb.connect(str(db_path))
    con.execute("DROP TABLE IF EXISTS bars_1h")
    con.execute("CREATE TABLE bars_1h(ticker VARCHAR, timestamp TIMESTAMPTZ, "
                "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE)")
    total = 0
    for t in tickers:
        df = bars.load_bars(t)
        df["ticker"] = t
        con.register("bars_df", df[COLUMNS])
        con.execute("INSERT INTO bars_1h SELECT * FROM bars_df")
        con.unregister("bars_df")
        total += len(df)
    con.close()
    print(f"built {db_path}: {total} bars over {len(tickers)} ticker(s) from {bars.upstream_path()}")


if __name__ == "__main__":
    build_db()

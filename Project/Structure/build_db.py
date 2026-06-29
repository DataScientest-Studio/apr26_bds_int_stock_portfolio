#!/usr/bin/env python3
"""Minimal, self-contained DuckDB builder for the pipeline input.

Loads every raw 1h OHLCV parquet in data/seed/ into a single table `bars_1h(ticker, timestamp, open, high, low,
close, volume)` inside liora.duckdb. That DuckDB is the only input Layer 1.6 reads. To add a ticker: drop its
`<TICKER>_ohlcv_1h.parquet` into data/seed/ and re-run `make build-db`.

The seed parquets already carry a UTC `timestamp` column (datetime64[us, UTC]) + the 5 OHLCV columns, so this is a
plain load — no cleaning, no calendar, no QC here (Layer 1.6 asserts the clean-OHLCV contract when it reads).
"""
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parent
SEED_DIR = ROOT / "data" / "seed"
DB_PATH = ROOT / "liora.duckdb"
COLUMNS = ["ticker", "timestamp", "open", "high", "low", "close", "volume"]


def build_db(seed_dir=SEED_DIR, db_path=DB_PATH):
    seeds = sorted(Path(seed_dir).glob("*_ohlcv_1h.parquet"))
    if not seeds:
        raise SystemExit(f"no *_ohlcv_1h.parquet seeds in {seed_dir}")
    con = duckdb.connect(str(db_path))
    con.execute("DROP TABLE IF EXISTS bars_1h")
    con.execute("CREATE TABLE bars_1h(ticker VARCHAR, timestamp TIMESTAMPTZ, "
                "open DOUBLE, high DOUBLE, low DOUBLE, close DOUBLE, volume DOUBLE)")
    for p in seeds:
        ticker = p.name.split("_ohlcv_1h")[0]
        df = pd.read_parquet(p)
        df["ticker"] = ticker
        con.register("seed_df", df[COLUMNS])
        con.execute("INSERT INTO bars_1h SELECT * FROM seed_df")
        con.unregister("seed_df")
        print(f"  loaded {ticker}: {len(df)} bars")
    con.close()
    print(f"built {db_path} from {len(seeds)} ticker(s)")


if __name__ == "__main__":
    build_db()

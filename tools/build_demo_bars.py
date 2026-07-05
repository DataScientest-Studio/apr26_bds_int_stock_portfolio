#!/usr/bin/env python3
"""Build the committed demo bars store: data/bars_demo.duckdb (table bars_1h) holding only a
handful of recognizable tickers, sliced from the full local data/liora.duckdb. It ships in the
repo (~a few MB) so a fresh clone can REPRODUCE those tickers' one-shot OOS rows via `make verify`
without the 160 MB full store or the external upstream. The app + dashboard still show all sealed
results; only reproduction is limited to these demo tickers. Rebuild after re-running the universe.
"""
import sqlite3
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "data" / "liora.duckdb"
OUT = ROOT / "data" / "bars_demo.duckdb"
OOS = ROOT / "data" / "oos_metrics.db"

PREFERRED = ["AAPL", "MSFT", "NVDA", "AMZN", "GOOGL", "META", "TSLA", "JPM",
             "XOM", "KO", "WMT", "HD", "PG", "JNJ", "V"]


def main():
    if not FULL.exists():
        raise SystemExit(f"{FULL} not found — run `make build-db` (needs the external upstream) first")
    have = {r[0] for r in duckdb.connect(str(FULL), read_only=True)
            .execute("select distinct ticker from bars_1h").fetchall()}
    scored = set()
    if OOS.exists():
        scored = {r[0] for r in sqlite3.connect(f"file:{OOS}?mode=ro", uri=True)
                  .execute("select ticker from oos_metrics").fetchall()}
    # demo = preferred order, keep only tickers that both have bars AND a sealed OOS row
    demo = [t for t in PREFERRED if t in have and (not scored or t in scored)]
    if not demo:
        raise SystemExit("no preferred demo tickers are present in both stores")
    OUT.unlink(missing_ok=True)
    con = duckdb.connect(str(OUT))
    con.execute(f"attach '{FULL}' as srcdb (read_only)")
    placeholders = ",".join("?" * len(demo))
    con.execute(f"create table bars_1h as select * from srcdb.bars_1h where ticker in ({placeholders})", demo)
    n = con.execute("select count(*) from bars_1h").fetchone()[0]
    con.close()
    mb = OUT.stat().st_size / 2**20
    print(f"demo bars: {len(demo)} tickers, {n} rows, {mb:.1f} MB -> {OUT}")
    print("tickers:", ", ".join(demo))


if __name__ == "__main__":
    main()

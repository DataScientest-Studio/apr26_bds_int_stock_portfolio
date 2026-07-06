#!/usr/bin/env python3
"""One-time provenance: upstream 1h store -> data/sp500_1d.duckdb (table bars_1d).

The upstream Alpaca S&P 500 1h DuckDB keeps naive NY-local timestamps, so grouping by
CAST(ts AS DATE) IS the ET session day. Aggregation: O=first / H=max / L=min / C=last /
V=sum per (symbol, day). The result ships committed in the repo — cloners never run this;
it stays here so the roll-up rule is auditable. Atomic publish (temp + os.replace).

Checks: symbol/row counts, date range, size < 95 MB (GitHub hard limit is 100), and
row-for-row parity against the parent project's independently derived AAPL daily parquet.
"""
import os
import sys
from pathlib import Path

import duckdb

UPSTREAM = "/opt/to_liora_school/qc-raw-ohlcv-data-sp500-alpaca/endproduct/ohlcv_1h_sp500_alpaca.duckdb"
PARITY_PARQUET = ("/opt/to_liora_school/liora-project-ml-engineering/"
                  "Project/Structure/Assets/AAPL/AAPL_ohlcv_1d.parquet")
OUT = Path(__file__).resolve().parents[1] / "data" / "sp500_1d.duckdb"

ROLLUP_SQL = """
CREATE TABLE bars_1d AS
SELECT symbol,
       CAST(ts AS DATE)            AS date,
       arg_min(open,  ts)          AS open,
       max(high)                   AS high,
       min(low)                    AS low,
       arg_max(close, ts)          AS close,
       CAST(sum(volume) AS BIGINT) AS volume
FROM up.ohlcv_1h
GROUP BY symbol, CAST(ts AS DATE)
ORDER BY symbol, date
"""


def build():
    if not Path(UPSTREAM).exists():
        sys.exit(f"upstream store not found: {UPSTREAM}\n"
                 "(provenance script — the repo already ships data/sp500_1d.duckdb)")
    tmp = OUT.parent / f"{OUT.name}.{os.getpid()}.tmp"
    if tmp.exists():
        tmp.unlink()
    con = duckdb.connect(str(tmp))
    try:
        con.execute(f"ATTACH '{UPSTREAM}' AS up (READ_ONLY)")
        con.execute(ROLLUP_SQL)
        rows, syms = con.execute("select count(*), count(distinct symbol) from bars_1d").fetchone()
        dmin, dmax = con.execute("select min(date), max(date) from bars_1d").fetchone()
    except BaseException:
        con.close()
        if tmp.exists():
            tmp.unlink()
        raise
    con.close()
    os.replace(tmp, OUT)
    print(f"built {OUT}: {rows} rows, {syms} symbols, {dmin} -> {dmax}, "
          f"{OUT.stat().st_size / 2**20:.1f} MB")
    assert OUT.stat().st_size < 95 * 2**20, "store would exceed GitHub's file-size limit"
    return rows, syms


def parity_check():
    """Exact-value parity vs the parent project's per-asset daily parquet (independent
    derivation: 1h -> UTC -> ET calendar-day roll-up in pandas). Dates and all five
    value columns must match row for row."""
    if not Path(PARITY_PARQUET).exists():
        print("parity: parent parquet not found — skipped (informational only)")
        return
    import pandas as pd
    old = pd.read_parquet(PARITY_PARQUET)
    old_dates = old["timestamp"].dt.tz_convert("America/New_York").dt.date.tolist()
    con = duckdb.connect(str(OUT), read_only=True)
    new = con.execute("select date, open, high, low, close, volume from bars_1d "
                      "where symbol='AAPL' order by date").fetchall()
    con.close()
    assert len(new) == len(old), f"AAPL row count {len(new)} != parquet {len(old)}"
    for i, (d, o, h, l, c, v) in enumerate(new):
        assert d == old_dates[i], f"row {i}: date {d} != {old_dates[i]}"
        for col, val in (("open", o), ("high", h), ("low", l), ("close", c), ("volume", v)):
            assert float(val) == float(old[col].iloc[i]), \
                f"row {i} ({d}) {col}: {val} != {old[col].iloc[i]}"
    print(f"parity: AAPL {len(new)} daily bars — exact match vs the parent parquet")


if __name__ == "__main__":
    build()
    parity_check()

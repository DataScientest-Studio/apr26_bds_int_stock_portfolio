#!/usr/bin/env python3
"""Single home of the bar-acquisition transform (L2 upstream store → canonical frame).

Every consumer of raw 1h OHLCV — build_db.py (L3 full copy into liora.duckdb) and the
feature-search worker's TickerContext — loads bars through load_bars() below, so all of
them see the identical frame: UTC timestamps (localized from the store's America/New_York
clock), float64 volume, exactly timestamp/open/high/low/close/volume.

The upstream store path is single-homed here; set SP500_DUCKDB only to override it.
The store is opened read-only — nothing in this repo ever writes to it.
"""
import os

import pandas as pd

DEFAULT_UPSTREAM = "/opt/to_liora_school/qc-raw-ohlcv-data-sp500-alpaca/endproduct/ohlcv_1h_sp500_alpaca.duckdb"


def upstream_path():
    return os.environ.get("SP500_DUCKDB") or DEFAULT_UPSTREAM


def upstream_tickers(db=None):
    import duckdb
    con = duckdb.connect(db or upstream_path(), read_only=True)
    try:
        return [r[0] for r in con.execute(
            "select distinct symbol from ohlcv_1h order by symbol").fetchall()]
    finally:
        con.close()


def load_bars(ticker, db=None):
    """The canonical transform — the pipeline's only entry point to raw bars."""
    import duckdb
    path = db or upstream_path()
    con = duckdb.connect(path, read_only=True)
    try:
        d = con.execute("select ts as timestamp, open, high, low, close, volume "
                        "from ohlcv_1h where symbol=? order by ts", [ticker]).fetchdf()
    finally:
        con.close()
    if d.empty:
        raise RuntimeError(f"ticker {ticker} not found in upstream {path}")
    d["timestamp"] = (pd.to_datetime(d["timestamp"])
                      .dt.tz_localize("America/New_York", ambiguous="infer", nonexistent="shift_forward")
                      .dt.tz_convert("UTC"))
    d["volume"] = d["volume"].astype("float64")
    return d[["timestamp", "open", "high", "low", "close", "volume"]]

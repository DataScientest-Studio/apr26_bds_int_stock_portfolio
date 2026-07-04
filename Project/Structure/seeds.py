#!/usr/bin/env python3
"""Single home of the bar-acquisition transform (L2 seed export + S.1 upstream reads).

Two consumers need identical OHLCV frames: the Makefile seed export (ensure-seeds /
make loop) and the feature-search worker's universe mode (which reads bars straight
from the upstream SP500 DuckDB without materializing a seed). The transform below is
the contract: a frame loaded from an existing seed parquet and one loaded from the
upstream store are identical (export_seed asserts the round-trip on every write).

Seeds materialize on demand: search reads upstream-direct; a seed file is written
only when an asset is APPLIED (run_asset needs liora.duckdb, which builds from
data/seed/). Runtime-exported seeds sit untracked until the user commits a batch
(together with the n_assets_seed / duckdb_rows_bars_1h registry bump — the docs
gate counts git-tracked seeds, not on-disk files).

CLI (drop-in for the old Makefile ENSURE_SEEDS_PY define):
    LOOP_TICKERS="AAPL TSLA" [SP500_DUCKDB=...] python3 seeds.py
"""
import os
from pathlib import Path

import pandas as pd

DEFAULT_UPSTREAM = "/opt/to_liora_school/qc-raw-ohlcv-data-sp500-alpaca/endproduct/ohlcv_1h_sp500_alpaca.duckdb"
SEED_DIR = Path(__file__).resolve().parent / "data" / "seed"


def upstream_path():
    return os.environ.get("SP500_DUCKDB") or DEFAULT_UPSTREAM


def load_bars_from_upstream(ticker, db=None):
    """The EXACT historical seed-export transform — byte-for-byte contract with seeds."""
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


def seed_path(ticker):
    return SEED_DIR / f"{ticker}_ohlcv_1h.parquet"


def load_bars(ticker):
    """Dual source: seed parquet if present, else the upstream transform (identical frames)."""
    p = seed_path(ticker)
    if p.exists():
        return pd.read_parquet(p)
    return load_bars_from_upstream(ticker)


def export_seed(ticker):
    """Apply-time materialization. No-op if the seed exists (seeds are never overwritten)."""
    p = seed_path(ticker)
    if p.exists():
        return p
    SEED_DIR.mkdir(parents=True, exist_ok=True)
    d = load_bars_from_upstream(ticker)
    tmp = p.with_suffix(".parquet.tmp")
    d.to_parquet(tmp, index=False)
    pd.testing.assert_frame_equal(pd.read_parquet(tmp), d)   # seed == upstream parity, forever
    os.replace(tmp, p)
    print(f"exported seed {p} ({len(d)} bars)")
    return p


def ensure_seeds(tickers):
    missing = [t for t in tickers if not seed_path(t).exists()]
    for t in missing:
        export_seed(t)
    if not missing:
        print("all requested seeds already present")


if __name__ == "__main__":
    ensure_seeds(os.environ.get("LOOP_TICKERS", "AAPL TSLA XOM").split())

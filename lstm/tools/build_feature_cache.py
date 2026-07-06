#!/usr/bin/env python3
"""make build-cache: precompute the frozen CORE+OPTIONAL feature superset for every bundled
ticker into cache/features/<T>.parquet (gitignored). The search and run_asset then LOAD these
instead of recomputing the ~30 indicators per ticker on every pass — a real win for the
continuous loop, where a ticker is re-searched each time the Sonnet agent adds a feature. The
cache is small (~1 MB/ticker) and the OS keeps it resident in RAM (page cache), so reads are
RAM-speed. A version token (hash of the CORE/OPTIONAL names) invalidates it automatically if
the feature bank changes; PROPOSED DSL features are always computed fresh, so proposals never
stale the cache. Parquet round-trips float64 exactly -> the cached frame is byte-identical.
"""
import os
import sys
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import features as F          # noqa: E402
import pipeline as P          # noqa: E402

CACHE_DIR = ROOT / "cache" / "features"


def _one(ticker):
    df = P.load_bars(ticker)
    frame = pd.concat([F.core_frame(df, P.CONFIG), F.optional_frame(df)], axis=1)
    frame.to_parquet(CACHE_DIR / f"{ticker}.parquet", engine="pyarrow", compression="zstd", index=False)
    return ticker, len(frame)


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(ROOT / "data" / "sp500_1d.duckdb"), read_only=True)
    tickers = [r[0] for r in con.execute("select distinct symbol from bars_1d order by symbol").fetchall()]
    con.close()
    jobs = max(1, (os.cpu_count() or 2) - 1)
    print(f"building feature cache for {len(tickers)} tickers ({jobs} parallel) -> {CACHE_DIR}", flush=True)
    done = 0
    with ProcessPoolExecutor(max_workers=jobs) as ex:
        for fut in as_completed([ex.submit(_one, t) for t in tickers]):
            fut.result()
            done += 1
            if done % 100 == 0:
                print(f"  {done}/{len(tickers)}", flush=True)
    (ROOT / "cache" / "VERSION").write_text(P.cache_token() + "\n", encoding="utf-8")
    size = sum(p.stat().st_size for p in CACHE_DIR.glob("*.parquet")) / 2**20
    print(f"feature cache built: {done} tickers, {size:.0f} MB (token {P.cache_token()})", flush=True)


if __name__ == "__main__":
    main()

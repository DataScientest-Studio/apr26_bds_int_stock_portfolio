"""Parallel feature-cache warm-up for the full-universe run.

Building the per-1h-bar feature frame for ~498 tickers is the one heavy I/O + CPU step. Doing it
ONCE up front, fanned out over all cores, means every downstream stage reads the parquet cache at
page-cache (RAM) speed instead of recomputing. Also touches the bars DuckDB so the OS keeps it hot.

Usage: python -m fs.warm --universe full [--workers N]
"""
import argparse
import os
import time
from concurrent.futures import ProcessPoolExecutor, as_completed

from . import CONFIG
from . import data


def _warm_one(args):
    universe, ticker = args
    try:
        bars, feats = data.bar_frame(ticker, universe, use_cache=True)  # builds + caches if missing
        return (ticker, len(bars), None)
    except Exception as e:  # noqa: BLE001 — report, don't abort the whole warm
        return (ticker, 0, f"{type(e).__name__}: {e}")


def page_cache_bars(universe):
    """Read the bars store once so the OS keeps it in RAM (page cache)."""
    path = data.bars_1h_db(universe)
    try:
        with open(path, "rb") as f:
            while f.read(1 << 24):
                pass
    except OSError:
        pass


def warm(universe, workers=None):
    want = workers or int(CONFIG.get("PARALLEL", {}).get(universe, {}).get("warm_workers", 8))
    workers = min(want, max(1, (os.cpu_count() or 2) - 1))  # cap so a smaller server auto-adapts
    page_cache_bars(universe)
    tickers = data.tickers(universe)
    print(f"[warm/{universe}] {len(tickers)} tickers on {workers} workers", flush=True)
    t0 = time.time()
    done, failed = 0, []
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(_warm_one, (universe, t)): t for t in tickers}
        for fut in as_completed(futs):
            tk, n, err = fut.result()
            done += 1
            if err:
                failed.append((tk, err))
            if done % 50 == 0 or done == len(tickers):
                print(f"  {done}/{len(tickers)} ({time.time() - t0:.0f}s)", flush=True)
    if failed:
        print(f"[warm/{universe}] {len(failed)} FAILED (skipped): {failed[:10]}", flush=True)
    print(f"[warm/{universe}] done in {time.time() - t0:.0f}s; "
          f"{len(tickers) - len(failed)} cached", flush=True)
    return [t for t in tickers if t not in {f[0] for f in failed}]


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--universe", choices=["demo", "full"], default="full")
    ap.add_argument("--workers", type=int, default=None)
    a = ap.parse_args()
    # keep BLAS single-threaded inside each warm worker (many processes already)
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        os.environ.setdefault(v, "1")
    warm(a.universe, a.workers)


if __name__ == "__main__":
    main()

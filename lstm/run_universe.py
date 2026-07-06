#!/usr/bin/env python3
"""Universe loop: run every bundled ticker through run_asset.py (core-only), resumably.

Parallel across JOBS run_asset subprocesses (each bounded to the configured torch threads),
resumable (tickers already in oos_metrics.db skip), fail-soft (a thin/IPO ticker is logged and
the loop continues), STOP.flag-aware. This produces the core-only baseline fast; the full
self-improving loop is feature_search.py (which also does per-asset feature selection).
"""
import os
import sqlite3
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parent
OOS_DB = ROOT / "oos_metrics.db"
STOP_FLAG = ROOT / "logs" / "search" / "STOP.flag"
_TT = str(__import__("json").loads((ROOT / "config.json").read_text())["TRAIN"]["torch_threads"])


def _jobs():
    return max(1, int(os.environ.get("JOBS") or max(1, (os.cpu_count() or 2) - 2) // int(_TT)))


def universe():
    con = duckdb.connect(f"{ROOT / 'data' / 'sp500_1d.duckdb'}", read_only=True)
    try:
        return [r[0] for r in con.execute(
            "select distinct symbol from bars_1d order by symbol").fetchall()]
    finally:
        con.close()


def done_tickers():
    if not OOS_DB.exists():
        return set()
    con = sqlite3.connect(f"file:{OOS_DB}?mode=ro", uri=True)
    try:
        return {r[0] for r in con.execute("select ticker from oos_metrics").fetchall()}
    except sqlite3.OperationalError:
        return set()
    finally:
        con.close()


def _run_one(t):
    return t, subprocess.run([sys.executable, str(ROOT / "run_asset.py"), f"TICKER={t}"],
                             env=dict(os.environ, OMP_NUM_THREADS=_TT), cwd=str(ROOT)).returncode


def main():
    tickers = universe()
    todo = [t for t in tickers if t not in done_tickers()]
    j = _jobs()
    print(f"universe: {len(tickers)} tickers, {len(todo)} to run, {j} parallel", flush=True)
    t_start, ok, failed, done = time.time(), 0, [], 0
    with ThreadPoolExecutor(max_workers=j) as ex:
        futs = {ex.submit(_run_one, t): t for t in todo}
        for fut in as_completed(futs):
            t, rc = fut.result()
            done += 1
            if rc == 0:
                ok += 1
            else:
                failed.append(t)
                print(f"{t}: SKIPPED (rc={rc})", flush=True)
            if done % 20 == 0:
                subprocess.run([sys.executable, str(ROOT / "build_dashboard.py")], cwd=str(ROOT))
                el = time.time() - t_start
                print(f"--- {done}/{len(todo)} ({ok} ok, {len(failed)} skipped, {el/60:.0f} min, "
                      f"~{el/done*(len(todo)-done)/60:.0f} min left)", flush=True)
            if STOP_FLAG.exists():
                for f2 in futs:
                    f2.cancel()
                break
    subprocess.run([sys.executable, str(ROOT / "build_dashboard.py")], cwd=str(ROOT))
    print(f"universe done: {ok} ok, {len(failed)} skipped"
          + (f" ({' '.join(failed)})" if failed else ""), flush=True)


if __name__ == "__main__":
    main()

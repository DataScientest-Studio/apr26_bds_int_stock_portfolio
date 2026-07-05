#!/usr/bin/env python3
"""make verify — prove the sealed repo reproduces: re-run demo tickers through the pipeline from
the COMMITTED manifest (data/per_asset_feature_overrides.json) and the bundled mini bars
(data/bars_demo.duckdb), and assert each matches its committed data/oos_metrics.db row. Forces the
mini-bars (LIORA_DB) + a scratch results db (OOS_METRICS_DB) so the sealed store is never mutated —
this is exactly the fresh-clone path (no full liora.duckdb, no external upstream).

  python3 tools/verify_repro.py                # default: first 2 demo tickers
  python3 tools/verify_repro.py AAPL KO XOM    # explicit
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import duckdb

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "data" / "oos_metrics.db"
DEMO_BARS = ROOT / "data" / "bars_demo.duckdb"
SCRATCH = ROOT / "data" / "verify_scratch.db"
FIELDS = ["end_capital", "return_pct", "trades", "profit_factor", "cv_auc_pr"]
TOL = 1e-6


def rows(db):
    c = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    c.row_factory = sqlite3.Row
    try:
        return {r["ticker"]: dict(r) for r in c.execute("select * from oos_metrics")}
    finally:
        c.close()


def close(a, b):
    if a is None or b is None:
        return a == b
    try:
        return abs(float(a) - float(b)) <= TOL + TOL * abs(float(b))
    except (TypeError, ValueError):
        return str(a) == str(b)


def main():
    committed = rows(COMMITTED)
    demo_bars = {r[0] for r in duckdb.connect(str(DEMO_BARS), read_only=True)
                 .execute("select distinct ticker from bars_1h").fetchall()}
    sample = [t.upper() for t in sys.argv[1:]] or [t for t in sorted(demo_bars) if t in committed][:2]
    sample = [t for t in sample if t in committed and t in demo_bars]
    if not sample:
        sys.exit("no verifiable demo tickers (need a ticker in both the sealed rows and the mini-bars)")
    print(f"verifying {len(sample)} demo ticker(s) from the bundled mini-bars: {', '.join(sample)}\n")
    env = dict(os.environ, LIORA_DB=str(DEMO_BARS), OOS_METRICS_DB=str(SCRATCH))
    SCRATCH.unlink(missing_ok=True)
    bad = []
    for t in sample:
        import shutil
        shutil.rmtree(ROOT / "Assets" / t, ignore_errors=True)
        r = subprocess.run([sys.executable, str(ROOT / "src" / "run_asset.py"), f"TICKER={t}"],
                           env=env, cwd=str(ROOT), stdout=subprocess.DEVNULL)
        repro = rows(SCRATCH).get(t, {}) if SCRATCH.exists() else {}
        if r.returncode != 0 or not repro:
            print(f"  [FAIL ] {t}: run_asset rc={r.returncode}, reproduced row={'yes' if repro else 'no'}")
            bad.append(t); continue
        diffs = [f for f in FIELDS if not close(committed[t].get(f), repro.get(f))]
        mark = "OK  " if not diffs else "DIFF"
        detail = "  ".join(f"{f}:{committed[t].get(f)}->{repro.get(f)}" for f in diffs)
        print(f"  [{mark}] {t:6} end_capital={committed[t].get('end_capital')} "
              f"ret={committed[t].get('return_pct')} trades={committed[t].get('trades')} "
              f"{('<-- ' + detail) if diffs else ''}")
        if diffs:
            bad.append(t)
        shutil.rmtree(ROOT / "Assets" / t, ignore_errors=True)
    SCRATCH.unlink(missing_ok=True)
    print(f"\n{'ALL REPRODUCE' if not bad else 'MISMATCH: ' + ', '.join(bad)} "
          f"({len(sample) - len(bad)}/{len(sample)})")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()

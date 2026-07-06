#!/usr/bin/env python3
"""make verify — prove the sealed repo is reproducible: for a diverse sample of tickers, re-run
the pipeline from the COMMITTED manifest (features_proposed.json + per_asset_feature_overrides.json)
and assert each reproduces its committed oos_metrics row. Writes to a scratch db via the
OOS_METRICS_DB override, so the sealed oos_metrics.db is never mutated. This is the credibility
core of the presentation: 'clone it and every number reproduces'.

  python3 tools/verify_repro.py                 # default diverse sample (proposed / optional / core-only)
  python3 tools/verify_repro.py AAPL MSFT KO    # explicit tickers
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMMITTED = ROOT / "oos_metrics.db"
OVERRIDES = ROOT / "per_asset_feature_overrides.json"
SCRATCH = ROOT / "cache" / "verify_oos.db"
FIELDS = ["end_capital", "return_pct", "trades", "cv_auc_pr"]
TOL = 1e-6


def rows(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return {r["ticker"]: dict(r) for r in con.execute("select * from oos_metrics")}
    finally:
        con.close()


def pick_sample(committed):
    ov = json.loads(OVERRIDES.read_text()) if OVERRIDES.exists() else {}
    proposed = sorted(t for t, ids in ov.items() if t in committed and any(int(i) >= 501 for i in ids))
    optional = sorted(t for t, ids in ov.items() if t in committed and ids and all(int(i) < 501 for i in ids))
    coreonly = sorted(t for t in committed if t not in ov)
    return proposed[:4] + optional[:4] + coreonly[:2]


def close(a, b):
    if a is None or b is None:
        return a == b
    return abs(float(a) - float(b)) <= TOL + TOL * abs(float(b))


def main():
    committed = rows(COMMITTED)
    if not committed:
        sys.exit("no committed oos_metrics rows — nothing to verify")
    sample = [t.upper() for t in sys.argv[1:]] or pick_sample(committed)
    sample = [t for t in sample if t in committed]
    SCRATCH.parent.mkdir(parents=True, exist_ok=True)
    SCRATCH.unlink(missing_ok=True)
    print(f"verifying {len(sample)} tickers against the committed sealed rows: {', '.join(sample)}\n")
    env = dict(os.environ, OMP_NUM_THREADS="2", OOS_METRICS_DB=str(SCRATCH))
    bad = []
    for t in sample:
        subprocess.run([sys.executable, str(ROOT / "run_asset.py"), f"TICKER={t}"],
                       env=env, cwd=str(ROOT), stdout=subprocess.DEVNULL).check_returncode()
        repro = rows(SCRATCH).get(t, {})
        diffs = [f for f in FIELDS if not close(committed[t].get(f), repro.get(f))]
        ok = not diffs
        mark = "OK  " if ok else "STALE"
        detail = "  ".join(f"{f}={committed[t].get(f)}→{repro.get(f)}" for f in diffs)
        print(f"  [{mark}] {t:6} end_capital={committed[t].get('end_capital'):.2f} "
              f"ret={committed[t].get('return_pct'):+.2f}% trades={committed[t].get('trades')} "
              f"cv={committed[t].get('cv_auc_pr'):.4f}  {('<-- ' + detail) if diffs else ''}")
        if not ok:
            bad.append(t)
        import shutil
        shutil.rmtree(ROOT / "Assets" / t, ignore_errors=True)
    SCRATCH.unlink(missing_ok=True)
    print(f"\n{'ALL REPRODUCE' if not bad else 'STALE: ' + ', '.join(bad)} "
          f"({len(sample) - len(bad)}/{len(sample)} match)")
    sys.exit(0 if not bad else 1)


if __name__ == "__main__":
    main()

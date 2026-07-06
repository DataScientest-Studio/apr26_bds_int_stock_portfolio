#!/usr/bin/env python3
"""make stats — a read-only, honest snapshot of the current sealed results. OOS numbers + the
buy-and-hold benchmark come from the dashboard feed (the canonical presentation numbers); the
feature-search state comes from search_state.db. Nothing is mutated and the OOS window is NOT
re-read — this only summarizes rows already produced by the one-shot pipeline. Run it any time
to regenerate the figures quoted in the README/presentation, so no number is ever hand-copied."""
import json
import sqlite3
import statistics as st
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    feed = ROOT / "dashboard" / "data" / "dashboard.json"
    if not feed.exists():
        print("no dashboard feed yet — run `make dashboard` after at least one `make run-asset`.")
        return
    d = json.loads(feed.read_text())
    rows = d["rows"] if isinstance(d, dict) and "rows" in d else \
        (next((v for v in d.values() if isinstance(v, list)), []) if isinstance(d, dict) else d)
    if not rows:
        print("dashboard feed is empty.")
        return
    n = len(rows)
    ret = [r["return_pct"] for r in rows]
    hodl = [r["hodl_return_pct"] for r in rows if r.get("hodl_return_pct") is not None]
    beat = [r for r in rows if r.get("beats_hodl")]
    trades = [r["trades"] for r in rows]
    zero = [r for r in rows if r["trades"] == 0]
    pf = [r["profit_factor"] for r in rows if r.get("profit_factor") and r["trades"] > 0]
    cv = [r["cv_auc_pr"] for r in rows if r.get("cv_auc_pr") is not None]
    dd = [r["max_drawdown_pct"] for r in rows if r.get("max_drawdown_pct") is not None]
    pos = [r for r in rows if r["return_pct"] > 0]

    print(f"=== OOS — ONE-SHOT read, 2024-01-01..2026-04-30 — {n} assets ===")
    print(f"  return %          median {st.median(ret):+.2f}   mean {st.mean(ret):+.2f}"
          f"   range [{min(ret):+.1f}, {max(ret):+.1f}]")
    print(f"  positive return   {len(pos)}/{n} ({100*len(pos)/n:.0f}%)")
    if hodl:
        print(f"  beat buy & hold   {len(beat)}/{n} ({100*len(beat)/n:.0f}%)"
              f"   [HODL median {st.median(hodl):+.2f}% — the OOS is a strong bull]")
    print(f"  trades            median {st.median(trades):.0f}"
          f"   zero-trade HODL-fallbacks {len(zero)}/{n} ({100*len(zero)/n:.0f}%)")
    if pf:
        print(f"  profit factor     median {st.median(pf):.3f}   (traded assets: {len(pf)})")
    if dd:
        print(f"  max drawdown %    median {st.median(dd):.1f}")
    if cv:
        print(f"  cv_auc_pr         median {st.median(cv):.4f}"
              f"   (base rate ~0.50; >0.50 = weak-but-real Train ranking)")

    sdb = ROOT / "search_state.db"
    if sdb.exists():
        sc = sqlite3.connect(f"file:{sdb}?mode=ro", uri=True)
        ap = dict(sc.execute("select applied, count(*) from searched group by applied").fetchall())
        cnt = Counter()
        for (subset,) in sc.execute("select subset from searched where applied=1"):
            for i in json.loads(subset or "[]"):
                cnt[i] += 1
        print(f"\n=== FEATURE SEARCH — Train-only selection (OOS never consulted) ===")
        print(f"  applied a searched subset (beat core past the overfit gate)   {ap.get(1, 0)}")
        print(f"  core-only kept (no robust edge found — reported honestly)      {ap.get(0, 0)}")
        if cnt:
            print("  most-selected feature ids   "
                  + ", ".join(f"{i}×{c}" for i, c in cnt.most_common(10)))

    print("\nIntegrity: every figure above is a one-shot OOS read. Model/feature/operating-point "
          "selection is Train-only; OOS is never used to choose anything.")


if __name__ == "__main__":
    main()

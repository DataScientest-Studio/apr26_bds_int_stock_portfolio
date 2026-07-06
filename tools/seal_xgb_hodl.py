#!/usr/bin/env python3
"""make seal-xgb-hodl: enrich xgb/plan/data/dashboard.json with the per-ticker buy-and-hold
benchmark (hodl_return_pct / beats_hodl) over the XGB OOS window — the same convention the LSTM
dashboard uses (lstm/build_dashboard.py: first open -> last close, %), computed from the COMMITTED
daily store lstm/data/sp500_1d.duckdb. One-shot offline producer; the enriched JSON ships committed
so the app renders the benchmark without any runtime computation.

Honest note: bars are RAW prices (corporate actions deferred, documented) — a HODL return that
crosses a split (e.g. NVDA 2024 10:1) is distorted; the app carries this caveat.
"""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEED = ROOT / "xgb" / "plan" / "data" / "dashboard.json"
BARS = ROOT / "lstm" / "data" / "sp500_1d.duckdb"


def hodl_returns(oos_start, oos_end):
    """Per-ticker buy-and-hold return over the OOS window (first open -> last close, %)."""
    import duckdb
    con = duckdb.connect(str(BARS), read_only=True)
    try:
        rows = con.execute(
            "select symbol, (last(close order by date) / first(open order by date) - 1) * 100 "
            "from bars_1d where date >= ? and date <= ? group by symbol", [oos_start, oos_end]).fetchall()
    finally:
        con.close()
    return {s: r for s, r in rows}


def main():
    doc = json.loads(FEED.read_text(encoding="utf-8"))
    assets = doc["assets"]
    if not assets:
        raise SystemExit("seal-xgb-hodl: empty feed — nothing to enrich")
    windows = {str(a["oos_window"]) for a in assets}
    assert len(windows) == 1, f"non-uniform OOS windows: {windows}"
    start, _, end = windows.pop().partition("->")
    hodl = hodl_returns(start.strip(), end.strip())

    covered = beat = 0
    for a in assets:
        h = hodl.get(a["ticker"])
        if h is None:
            a["hodl_return_pct"] = None
            a["beats_hodl"] = None
            continue
        a["hodl_return_pct"] = round(h, 2)
        a["beats_hodl"] = bool(a["return_pct"] > a["hodl_return_pct"])
        covered += 1
        beat += a["beats_hodl"]

    tmp = FEED.with_suffix(".json.tmp")                    # atomic: a live reader never sees a partial file
    tmp.write_text(json.dumps(doc, indent=2), encoding="utf-8")
    os.replace(tmp, FEED)
    print(f"seal-xgb-hodl: hodl on {covered}/{len(assets)} assets, model beats buy-and-hold on {beat}/{covered}")
    print(f"seal-xgb-hodl: window {start.strip()} -> {end.strip()}, source {BARS.name} (raw prices — split caveat applies)")


if __name__ == "__main__":
    main()

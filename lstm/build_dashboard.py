#!/usr/bin/env python3
"""make dashboard: export the OOS results store (oos_metrics.db) to dashboard/data/dashboard.json,
which the static dashboard page (dashboard/dashboard.html) fetches. Adds an honest per-ticker
buy-and-hold benchmark (hodl_return_pct) over the OOS window, computed from the bundled daily
store — so the dashboard shows the model NEXT TO the simplest baseline. Empty/absent DB -> []."""
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "oos_metrics.db"
BARS = HERE / "data" / "sp500_1d.duckdb"
OUT = HERE / "dashboard" / "data" / "dashboard.json"


def hodl_returns(oos_start, oos_end):
    """Per-ticker buy-and-hold return over the OOS window (first open -> last close, %),
    the transparent benchmark the model is judged against."""
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
    assets = []
    if DB.exists():
        con = sqlite3.connect(str(DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute("select * from oos_metrics order by ticker").fetchall()
            assets = [dict(r) for r in rows]
        except sqlite3.OperationalError:
            assets = []
        finally:
            con.close()
    if assets and BARS.exists():
        win = str(assets[0].get("oos_window", "2024-01-01 -> 2026-04-30")).split("->")
        hodl = hodl_returns(win[0].strip(), win[-1].strip())
        beat = 0
        for a in assets:
            a["hodl_return_pct"] = round(hodl.get(a["ticker"], float("nan")), 2)
            a["beats_hodl"] = bool(a["return_pct"] > a["hodl_return_pct"])
            beat += a["beats_hodl"]
        print(f"dashboard: model beats buy-and-hold on {beat}/{len(assets)} assets")
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".json.tmp")                    # atomic: a live HTTP GET never sees a partial file
    tmp.write_text(json.dumps({"assets": assets}, indent=2), encoding="utf-8")
    import os
    os.replace(tmp, OUT)
    print(f"dashboard: {len(assets)} asset(s) -> {OUT}")


if __name__ == "__main__":
    main()

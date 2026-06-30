#!/usr/bin/env python3
"""make dashboard: export the L9 OOS results store (oos_metrics.db) to Plan/data/dashboard.json, which the
static Dashboard page (Plan/dashboard.html) fetches. stdlib only — runs without the .venv. Empty/absent DB -> []."""
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB = HERE / "oos_metrics.db"
OUT = HERE / ".." / ".." / "Plan" / "data" / "dashboard.json"


def main():
    assets = []
    if DB.exists():
        con = sqlite3.connect(str(DB))
        con.row_factory = sqlite3.Row
        try:
            rows = con.execute("select * from oos_metrics order by ticker").fetchall()
            assets = [dict(r) for r in rows]
        except sqlite3.OperationalError:
            assets = []                                                       # table not created yet
        finally:
            con.close()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"assets": assets}, indent=2), encoding="utf-8")
    print(f"dashboard: {len(assets)} asset(s) -> {OUT}")


if __name__ == "__main__":
    main()

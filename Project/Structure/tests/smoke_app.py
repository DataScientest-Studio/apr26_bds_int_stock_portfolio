"""Headless smoke test: every Streamlit page renders without an exception.

Uses Streamlit's AppTest harness (no browser) against the DuckDB-backed app.
Run from Project/Structure:  ../.venv/bin/python tests/smoke_app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

STRUCTURE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(STRUCTURE))

from streamlit.testing.v1 import AppTest  # noqa: E402

PAGES = [
    "Overview", "Data Audit", "EDA", "Model Leaderboard", "Model Explorer",
    "Walk-Forward", "Rankings", "Recommender", "Portfolios", "Archive",
]


def main() -> int:
    app = str(STRUCTURE / "app.py")
    ok = True
    for page in PAGES:
        at = AppTest.from_file(app, default_timeout=60).run()
        if page != "Overview":
            at.sidebar.radio[0].set_value(page).run()
        exc = [f"{e.type}: {e.message}" for e in at.exception]
        ok = ok and not exc
        flag = "OK " if not exc else "FAIL"
        print(f"  [{flag}] {page:18s} exceptions={len(exc)}" + (f"  -> {exc[0][:120]}" if exc else ""))
    print("\nALL PAGES OK" if ok else "\nSOME PAGES FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Root Streamlit entry — launches the UNIFIED multi-page app (app/app.py).

Kept at the repo root so the course convention `streamlit run app.py` still works and opens the
one coherent application (Project Report · Data Explorer · Risk Profile · Recommender (Track B) ·
Basket Simulator (Track A) · Methodology & Integrity). Equivalent: `make app` (port 8503).

Robust to being launched by a streamlit from OUTSIDE this repo's .venv (e.g. a user-level or
another project's install): if the app's third-party deps are missing from the running
interpreter, the repo venv's site-packages are appended to sys.path (appended, not prepended —
the host's own packages keep priority). If even that can't satisfy the imports, a clear
instruction is raised instead of a bare ModuleNotFoundError.

The original menu app this file used to hold lives in git history; its Exploration / DataViz /
Risk Assessment pages live on inside the unified app, and the original final recommender remains
runnable standalone from mac-2026-06-09-full-6y/.
"""
import importlib.util
import runpy
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEPS = ("seaborn", "matplotlib", "duckdb", "pandas")          # the unified app's third-party imports


def _ensure_deps() -> None:
    missing = [m for m in DEPS if importlib.util.find_spec(m) is None]
    if not missing:
        return
    site = ROOT / ".venv" / "lib" / f"python{sys.version_info.major}.{sys.version_info.minor}" / "site-packages"
    if site.is_dir() and str(site) not in sys.path:
        sys.path.append(str(site))                            # append: host packages keep priority
        missing = [m for m in DEPS if importlib.util.find_spec(m) is None]
    if missing:
        raise ModuleNotFoundError(
            f"The app needs {', '.join(missing)} which this interpreter does not have and the repo "
            f"venv could not provide. Run once:  make deps   — then start the app with  make app  "
            f"(or  .venv/bin/streamlit run app.py)."
        )


_ensure_deps()
runpy.run_path(str(ROOT / "app" / "app.py"), run_name="__main__")

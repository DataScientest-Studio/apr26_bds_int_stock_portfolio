#!/usr/bin/env python3
"""Root Streamlit entry — launches the UNIFIED multi-page app (app/app.py).

Kept at the repo root so the course convention `streamlit run app.py` still works and opens the
one coherent application (Project Report · Data Explorer · Risk Profile · Recommender (Track B) ·
Basket Simulator (Track A) · Methodology & Integrity). Equivalent: `make app` (port 8503).

The original menu app this file used to hold lives in git history; its Exploration / DataViz /
Risk Assessment pages live on inside the unified app, and the original final recommender remains
runnable standalone from mac-2026-06-09-full-6y/.
"""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent / "app" / "app.py"), run_name="__main__")

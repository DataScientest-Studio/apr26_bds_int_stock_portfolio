"""Data Pipeline Lego Plan — the procedure as an 18-brick ladder, with the reasoning kept.

The plan is a self-contained HTML file at the repository root: zero dependencies, zero
network requests, and it opens in any browser on its own. This page only embeds it.

No prose here on purpose. Everything a reader needs is inside the board: each brick carries
its contract (input, transform, output, invariants, knobs, tests), the layer id the code
actually uses (XGB L4–L9, LSTM D1–D9), and a "HOW WE THOUGHT · WHAT WE LEARNED" record —
click a brick to read it. Ladder order is pipeline order, fixed by declaration.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

import components as C

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "data_pipeline_lego_plan.html"


@st.cache_data
def _load(mtime: float) -> str:
    """The self-contained plan, cached per file mtime."""
    return PLAN.read_text(encoding="utf-8")


C.page_header("Data Pipeline Lego Plan", "")
C.guard(stop=False)  # static page: banner without stopping

if not PLAN.exists():
    st.error(f"Plan not found: {PLAN.name} (expected at the repository root).")
    st.stop()

# The board is 1184x2706 and its fit is height-bound below ~1690px of frame, so 780 rendered
# every brick title at under 3px. 1500 nearly doubles the fit (0.28 -> 0.55) and stays inside
# that ceiling — past it width binds and the extra height would only add empty bands.
st.iframe(_load(PLAN.stat().st_mtime), height=1500)
st.caption("Standalone file: data_pipeline_lego_plan.html (repository root — opens in any browser).")

"""Data Flow — the per-asset build path as a standalone 2.5D canvas map.

The map is a self-contained HTML file at the repository root: zero dependencies, zero network
requests, and it opens in any browser on its own. This page only embeds it.

The map's own figures are frozen (the research snapshot is frozen too). The caption below is
DERIVED from the store on every render, so if the two ever disagree, the disagreement is on
screen rather than hidden — the same house rule the Architecture page follows.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

import components as C
import data

ROOT = Path(__file__).resolve().parents[2]
FLOW = ROOT / "data_flow_3d.html"


@st.cache_data
def _load(mtime: float) -> str:
    """The self-contained map, cached per file mtime."""
    return FLOW.read_text(encoding="utf-8")


C.page_header("Data Flow", "The per-asset build path — two independent sealed pipelines, drawn "
                           "as one ladder.")
C.guard(stop=False)  # static page: banner without stopping

_run = data.research_run()
_n_xgb, _n_lstm = _run.get("xgb_assets", 0), _run.get("lstm_assets", 0)

st.write(
    "The ladder is **one pass** of the procedure: split-adjusted bars → time split with purge and "
    "embargo → ATR Triple-Barrier labels → profit-aligned Optuna → sealed artifact → the one-shot "
    "OOS read → Train-derived interpretation. The same pass runs independently for every asset — "
    "nothing is pooled, and each ticker gets its own model."
)
st.caption(
    f"Sealed indicators in this release: {_n_xgb} XGB (1h) · {_n_lstm} LSTM (daily) — "
    f"{_n_xgb + _n_lstm} artifacts. Counts read from the store; the map's own figures are frozen. "
    "Two scenes are marked SCHEMATIC (the Optuna trial scatter and the sample OHLCV rows): they "
    "illustrate the shape of a process and are not measurements."
)
st.caption("Drag to pan · wheel to zoom · click a node for its contract · Esc closes.")

if not FLOW.exists():
    st.error(f"Flow map not found: {FLOW.name} (expected at the repository root).")
    st.stop()

st.iframe(_load(FLOW.stat().st_mtime), height=820)
st.caption("Standalone file: data_flow_3d.html (repository root — opens in any browser).")

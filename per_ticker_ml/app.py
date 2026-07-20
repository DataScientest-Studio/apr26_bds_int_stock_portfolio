"""Entry point: `streamlit run app.py` (or `make on`). Three read-only pages, flat.

A list rather than a dict: st.navigation only draws section headers when it is given
groups, and three pages do not need headers over them. Sidebar order — the thing to play
with, then the result (which opens with the build path), then the procedure in full.
Statistics stays the landing page; it is the one that answers "what came out of this".
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent / "app"))

st.set_page_config(
    page_title="S&P 500 ML Indicator Study",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = st.navigation([
    st.Page("app/pages/simulator.py", title="Basket Simulator (Recommender)", url_path="simulator"),
    st.Page("app/pages/overview.py", title="Statistics", url_path="overview", default=True),
    st.Page("app/pages/blueprint.py", title="Data Pipeline Lego Plan", url_path="blueprint"),
], expanded=True)
pages.run()

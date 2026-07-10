#!/usr/bin/env python3
"""Unified Streamlit app — S&P 500 ML portfolio project, two evaluation tiers, one coherent UX.

Pages (st.navigation):
  1. Project Report          — the two-track narrative + methodology ladder
  2. Data Explorer           — Exploration + 6 mentor-validated plots (committed daily store)
  3. Risk Profile            — the 9-question investor questionnaire (feeds both tracks)
  4. Recommender (Track B)   — exploratory ranking recommender over vendored CSVs
  5. Basket Simulator (Track A) — sealed one-shot OOS results + rule-based preset packages
  6. Methodology & Integrity — what separates the tiers; limitations stated openly

READ-ONLY by design: every page renders committed artifacts (sealed oos_metrics stores, HODL
feeds, vendored Track-B CSVs, the daily bar store, the pre-OOS inputs table). Nothing trains,
optimizes or writes at runtime.

Run:  make app    (Streamlit on :8503)
"""
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))    # app/ modules import as flat names

import page_blueprint
import page_explorer
import page_final_presentation
import page_methodology
import page_recommender
import page_report
import page_risk
import page_simulator

st.set_page_config(page_title="S&P 500 ML Portfolio — Unified App", layout="wide")

pg = st.navigation([
    st.Page(page_report.render, title="Project Report", icon="📋", url_path="report", default=True),
    st.Page(page_explorer.render, title="Data Explorer", icon="🔎", url_path="explorer"),
    st.Page(page_risk.render, title="Risk Profile", icon="🧭", url_path="risk-profile"),
    st.Page(page_recommender.render, title="Recommender (Track B)", icon="📈", url_path="recommender"),
    st.Page(page_simulator.render, title="Basket Simulator (Track A)", icon="🧺", url_path="simulator"),
    st.Page(page_blueprint.render, title="Pipeline Blueprint (Track A)", icon="🧱", url_path="blueprint"),
    st.Page(page_methodology.render, title="Methodology & Integrity", icon="🔬", url_path="methodology"),
    st.Page(page_final_presentation.render, title="Final Presentation", icon="🎤", url_path="final-presentation"),
])
pg.run()

# ── Keyboard shortcut: Ctrl / ⌘ + B hides/shows the navigation menu (sidebar) ────────
# Streamlit exposes no sidebar hotkey, so we click its own collapse/expand control from
# a 0-height component. The listener is bound to the PARENT document exactly once (a flag
# survives reruns); typing in inputs/textarea is ignored so it never fights form entry.
st.sidebar.caption("⌨️  **⌘ / Ctrl + B** — hide / show this menu")
st.iframe(
    """
    <script>
    (function () {
      const doc = window.parent.document;
      if (doc.__sbToggleBound) return;               // bind once across Streamlit reruns
      doc.__sbToggleBound = true;
      function toggleSidebar() {
        const pick = (sel) => doc.querySelector(sel + ' button') || doc.querySelector(sel);
        const collapse = pick('[data-testid="stSidebarCollapseButton"]');
        const expand   = pick('[data-testid="stExpandSidebarButton"]');
        if (collapse && collapse.offsetParent !== null) collapse.click();   // menu open -> hide
        else if (expand) expand.click();                                    // menu hidden -> show
      }
      doc.addEventListener('keydown', function (e) {
        if ((e.ctrlKey || e.metaKey) && (e.key === 'b' || e.key === 'B')) {
          const t = e.target, tag = ((t && t.tagName) || '').toLowerCase();
          if (tag === 'input' || tag === 'textarea' || (t && t.isContentEditable)) return;
          e.preventDefault();
          toggleSidebar();
        }
      }, true);
    })();
    </script>
    """,
    height=1,
)

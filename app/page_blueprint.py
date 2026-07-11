"""Pipeline Blueprint (Track B): the sealed plan behind the Basket Simulator, embedded as
end-of-project documentation. Renders the repository's single-file lego map
(learning_by_doing_OHLCV_data_processing_pipeline.html) - a read-only ladder of 17 procedure
blocks with an XGBoost/LSTM view switch and a per-block "HOW WE THOUGHT · WHAT WE LEARNED"
record. The block order is welded to the pipeline order by declaration; nothing here is
editable, persisted or trained - it is documentation meant to be remembered.
"""
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from common import ROOT, track_a_badge

BLUEPRINT = ROOT / "learning_by_doing_OHLCV_data_processing_pipeline.html"

LESSONS = """
**The five lessons to carry forward**

1. **Optimize the thing you will be judged on.** The HPO objective moved from AUC-PR to
   Train-out-of-fold trading **log-growth** replayed through the real engine - a proxy metric had
   been selecting models that ranked well and traded poorly (block C1).
2. **Degrees of freedom are earned, not granted.** Per-asset threshold calibration overfit its
   operating point (a flagship asset's OOS profit factor fell 1.89 → 0.99) and was pinned; the
   LSTM's joint calibration validated out-of-fold and kept its freedom (block C2).
3. **Purge and embargo are not optional decorations.** With horizon labels, the naive
   warm-up/train/OOS split leaks by construction; the split guard rejects any partition without
   both (blocks A4, G.1).
4. **An honest negative from a trustworthy method beats a positive from a leaky one.** The
   full-universe one-shot verdict reversed what a ~18-ticker dev sample suggested - and was
   committed with full ceremony (block D1).
5. **Byte-identity replaces trust.** `make verify-*` re-runs sample assets from committed data and
   must reproduce the sealed rows exactly - every honesty mechanism, including the buy-and-hold
   benchmark feed, carries its own gate (blocks D2, G.3).
"""


@st.cache_data
def _load_blueprint(mtime: float) -> str:
    """The welded single-file exhibit, cached per file mtime."""
    return BLUEPRINT.read_text(encoding="utf-8")


def render() -> None:
    st.title("Pipeline Blueprint — Learning by Doing (Track B)")
    track_a_badge()
    st.write(
        "The sealed plan behind the **Basket Simulator**: end-of-project documentation of how the "
        "OHLCV data processing pipeline was built - and the most durable way to remember it. "
        "Each brick is one procedure contract paired with one paid-for lesson; the ladder order "
        "**is** the pipeline order, welded by declaration (nothing can be rearranged)."
    )
    st.markdown(
        """
**How to read it**

- The ladder flows **bottom → top**: raw bars (A1) become a sealed one-shot verdict and a
  read-only product (D3), with fail-closed **GUARDS** between the stages.
- The **XGBOOST (1H) | LSTM (DAILY)** switch flips only the model-specific bricks - the two
  pipelines share one procedure and differ in the knobs shown.
- **Click a brick** to open its contract (input → transform → output → invariants → knobs) and the
  *HOW WE THOUGHT · WHAT WE LEARNED* record - copyable as a prompt.
        """
    )
    if not BLUEPRINT.exists():
        st.error(f"Blueprint file not found: {BLUEPRINT.name} (expected at the repository root).")
        return
    components.html(_load_blueprint(BLUEPRINT.stat().st_mtime), height=780, scrolling=False)
    st.markdown(LESSONS)
    st.caption("Standalone file: learning_by_doing_OHLCV_data_processing_pipeline.html (repo root) · "
               "design rationale: docs/UNIFIED_APP.md · Track-B internals: docs/PROJECT_STATE.md.")

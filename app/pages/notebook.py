"""Jupyter Notebook — the build path for one asset, once per model.

The two notebooks under examples/ are executed copies of the canonical per-asset template:
narrative, exact code, captured outputs. Same ticker for both, so the only difference a
reader sees between them is the model.

Parsed with stdlib json — not nbformat or nbconvert, neither of which this branch ships.
Rich MIME output (images, HTML) is deliberately dropped: only text/plain is rendered, so
nothing on the page can come from anywhere but the committed file.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import streamlit as st

import components as C
import data

ROOT = Path(__file__).resolve().parents[2]

# A fixed map, never a directory listing: the console's data layer is built on "no folder
# scanning, ever", and a scan would let a stray checkpoint copy appear on stage. The order
# and the labels are part of the page.
NOTEBOOKS = {
    "XGBoost (1h) — layers L4 → L9": ROOT / "examples" / "Example_XGB.ipynb",
    "LSTM (daily) — phases D2 → D9": ROOT / "examples" / "Example_LSTM.ipynb",
}

DASHED_HR = ('<hr style="border:0;border-top:1px dashed rgba(139,148,158,.45);'
             'margin:1.6rem 0 1.1rem">')


@st.cache_data
def _load(path_str, mtime):
    """Cells normalized for rendering, cached per file mtime."""
    doc = json.loads(Path(path_str).read_text(encoding="utf-8"))

    def join(x):
        return x if isinstance(x, str) else "".join(x)

    cells = []
    for c in doc.get("cells", []):
        outs = []
        for o in c.get("outputs", []):
            kind = o.get("output_type")
            if kind == "stream":
                outs.append({"kind": o.get("name", "stdout"), "text": join(o.get("text", ""))})
            elif kind in ("execute_result", "display_data"):
                outs.append({"kind": "result",
                             "text": join(o.get("data", {}).get("text/plain", ""))})
            elif kind == "error":
                outs.append({"kind": "error", "text": "\n".join(o.get("traceback", []))})
        cells.append({"type": c.get("cell_type"), "source": join(c.get("source", "")),
                      "outputs": outs})
    return {"cells": cells, "liora": doc.get("metadata", {}).get("liora", {})}


def _render_outputs(outputs):
    for out in outputs:
        if not out["text"].strip():
            continue
        if out["kind"] == "stderr":
            with st.expander("Warnings (stderr)", expanded=False):
                st.code(out["text"], language=None)
        elif out["kind"] == "error":
            st.error("This cell raised during execution:")
            st.code(out["text"], language=None)
        else:
            st.caption("Output")
            st.code(out["text"], language=None)


C.page_header("Jupyter Notebook",
              "One asset end-to-end, once per model — narrative, exact code and the outputs "
              "that actually ran.")
C.guard(stop=False)

st.markdown(
    "Both notebooks run the same asset, so the only difference between them is the model. "
    "The LSTM notebook ends by comparing its fresh run against the sealed row at 1e-6; the "
    "XGB notebook is a verbatim run of the canonical template and carries no such comparison "
    "— its gate is the research branch's `make verify-xgb`. Neither can mutate a sealed "
    "store: both wrote to a scratch metrics database.")
st.info("**Why NVDA.** Its 2024 ten-for-one split falls inside the out-of-sample window, which "
        "makes the corporate-action policy visible: splits are adjusted on the hourly bars "
        "before any roll-up, so the split is a units change rather than a price cliff. "
        "Dividends are deliberately left unadjusted, so buy & hold stays a price benchmark.",
        icon="ℹ️")

choice = st.selectbox("Pipeline", list(NOTEBOOKS), key="notebook_sel",
                      help="1h XGBoost path (L4→L9) or daily LSTM path (D2→D9).")
path = NOTEBOOKS[choice]
if not path.exists():
    st.error(f"Executed notebook not found: {path.name} (expected in examples/).")
    st.stop()

doc = _load(str(path), path.stat().st_mtime)
cells = doc["cells"]

# The notebook states which sealed row it reproduces; the store is asked the same question
# here, so a stale notebook shows up as a contradiction on screen instead of a claim.
prov = doc.get("liora") or {}
if prov.get("ticker") and prov.get("model"):
    row = data.asset(prov["ticker"], prov["model"])
    claimed = (prov.get("sealed_row") or {}).get("end_capital")
    if row and claimed is not None:
        match = abs(float(row["end_capital"]) - float(claimed)) <= 1e-6 * max(1.0, abs(claimed))
        verdict = "matches" if match else "DOES NOT MATCH"
        st.caption(f"This run is {prov['ticker']} · {prov['model'].upper()}. Its end capital "
                   f"{claimed:,.4f} USD {verdict} the sealed row in data/results.db "
                   f"({float(row['end_capital']):,.4f} USD, {row['model_trades']} model trades, "
                   f"{C.status_label(row['result_mode'])}).")

sections = [c["source"].splitlines()[0].lstrip("# ").strip()
            for c in cells if c["type"] == "markdown" and c["source"].startswith("## ")]
if sections:
    st.markdown("**Transformations in this path:**\n"
                + "\n".join(f"1. {s}" for s in sections))

for cell in cells:
    if cell["type"] == "markdown":
        if cell["source"].startswith("## "):
            st.markdown(DASHED_HR, unsafe_allow_html=True)
        st.markdown(cell["source"])
    elif cell["type"] == "code":
        with st.expander("Code", expanded=False):
            st.code(cell["source"], language="python")
        _render_outputs(cell["outputs"])

st.markdown(DASHED_HR, unsafe_allow_html=True)
st.caption("Committed, executed notebooks: examples/. Running them again needs the training "
           "stack and the raw bar stores, which live on the research branch — on this branch "
           "they are a record, and `make verify` is what you can re-run yourself.")
C.integrity_footer()

# Plan — buildable SOT, split into A_Layers (Main_Pipeline) + B_Features (feature explanation)

This package is split into two folders so the two logics are **physically separate**:

- **[`A_Layers/`](A_Layers/) — Main_Pipeline (Pipeline A), layers `L1–L11`.** The **sole build SOT**:
  the S&P 500 ML trading-strategy pipeline (Alpaca → LEAN → DuckDB → snapshot → split → detector →
  features/triple-barrier → quality → Optuna/XGBoost → OOS). Start at the canonical SOT folder
  [`A_Layers/ENG/Layers_Short_SOT/`](A_Layers/ENG/Layers_Short_SOT/) (short fact-only files that own every
  parameter/formula/schema/contract); viz
  [`A_Layers/viz/main_data_flow.html`](A_Layers/viz/main_data_flow.html). **Features fixed:** 8 transformer
  columns (7 X + `closed_through_line` audit).
- **[`B_Features/`](B_Features/) — Feature explanation ("Plan B"), Stages `F0–F14` (feature ids on F2–F6).** A
  **subordinate helper** (NOT a build SOT, decoupled from any store) explaining what the
  features are and where they come from. Doc
  [`B_Features/feature_explanation_plan_b_eng.md`](B_Features/feature_explanation_plan_b_eng.md); viz
  [`B_Features/viz/feature_dag.html`](B_Features/viz/feature_dag.html).

**Naming rule:** `layer` / `L1–L11` = **A_Layers only**; `feature-stage` / `F0–F14` / `f{stage}_…` (ids on F2–F6) = **B_Features only**. Never mix.

## A_Layers (Main_Pipeline · SOT)

- **[`A_Layers/ENG/Layers_Short_SOT/`](A_Layers/ENG/Layers_Short_SOT/)** — the canonical total SOT: short fact-only files owning every parameter/formula/schema/contract (cross-cutting `00_*` + per-layer L1–L11 + QC-01…QC-11 + 7-X manifest + Output A/B + DoD). Governance + fact-ownership map in [`A_Layers/ENG/Layers_Short_SOT/README.md`](A_Layers/ENG/Layers_Short_SOT/README.md).
- _Narrative companions (ENG index, build narrative, reference detector algorithm, L8 worked example, glossary, writing standard) were removed in the A_Layers minimalism cleanup and preserved outside the live project → [`A_Layers_archive/ENG_companions/`](A_Layers_archive/ENG_companions/)._
- [`A_Layers/config/`](A_Layers/config/) — `parameters.json` (Main params + `TOUCH_TOL`), `data_state_numbers.json` (frozen observed numbers), and `universe_tickers.txt` (the S&P 500 universe).
- [`A_Layers/viz/main_data_flow.html`](A_Layers/viz/main_data_flow.html) — interactive 3D pipeline viz (L1–L11).

## B_Features (Feature explanation · helper)

- **[`B_Features/ENG/Stages_Short_SOT/`](B_Features/ENG/Stages_Short_SOT/)** — the Plan-B SOT: short fact-only files for the Universal OHLCV→feature DAG (Stages `F0–F14`: F0,F2–F6 features · F1/F7/F8/F11 data-handling scaffold · F9 top-20 selection · F10 XGB calibration · F12 artifact · F13/F14 cross-asset); governance + fact-ownership in its [`README.md`](B_Features/ENG/Stages_Short_SOT/README.md). Companions at [`B_Features/ENG/`](B_Features/ENG/) (derivations, selection/calibration spec, glossary).
- [`B_Features/feature_explanation_plan_b_eng.md`](B_Features/feature_explanation_plan_b_eng.md) — the high-level overview; subordinate, decoupled from any store.
- [`B_Features/viz/main_feature_flow.html`](B_Features/viz/main_feature_flow.html) — 3D self-explaining viz of the F0–F14 Stages.
- [`B_Features/viz/feature_dag.html`](B_Features/viz/feature_dag.html) — 2D OHLCV → F0–F5 feature DAG (self-contained).

## Open the visualizations

**A_Layers · 3D pipeline — [`A_Layers/viz/main_data_flow.html`](A_Layers/viz/main_data_flow.html)**
- Open in any modern browser, or serve over HTTP (`python3 -m http.server`). Deep-links `#1`…`#9`, `#setup` (L6), `#dq` (L8). Controls: drag = rotate · scroll = zoom · keys `1–9` = views.

**B_Features · 3D Stages — [`B_Features/viz/main_feature_flow.html`](B_Features/viz/main_feature_flow.html)**
- Open in any modern browser. 15 Stages bottom-to-top: F0 raw → F1 time split → F2–F6 features → F7 label → F8 assemble+DQ → F9 top-20 selection → F10 XGB calibration → F11 OOS → F12 artifact → F13 cross-asset entry table (one 0/1 column per asset) → F14 cross-asset correlation → augmented XGB (above an Alpaca→DuckDB provenance prologue). Controls: drag = rotate · shift+drag = pan · scroll = zoom · keys `1–9`/`0` = views · ✎ Labels / ▦ Legend panels · click a node → facts.
- **2D DAG — [`B_Features/viz/feature_dag.html`](B_Features/viz/feature_dag.html)**: fully offline; families as columns; click a node → highlight its lineage from F0.

## Notes
- `A_Layers/` is self-contained for the Main_Pipeline build SOT (every contract / parameter / formula inlined).
- The visualizations are frozen snapshots; if you change a canonical value, update the SOT docs and the viz together.
- `layer` / `L1–L11` reserved for `A_Layers`; the feature explanation uses `F0–F14` (feature ids on F2–F6) only.

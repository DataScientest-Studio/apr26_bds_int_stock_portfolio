# Plan — buildable SOT, split into A_Layers (Main_Pipeline) + B_Features (feature explanation)

This package is split into two folders so the two logics are **physically separate**:

- **[`A_Layers/`](A_Layers/) — Main_Pipeline (Pipeline A), layers `L1–L10`.** The **sole build SOT**:
  the S&P 500 ML trading-strategy pipeline (Alpaca → LEAN → DuckDB → snapshot → split → detector →
  features/triple-barrier → quality → Optuna/XGBoost → OOS). Start at the canonical SOT folder
  [`A_Layers/ENG/Layers_Short_SOT/`](A_Layers/ENG/Layers_Short_SOT/) (short fact-only files that own every
  parameter/formula/schema/contract); viz
  [`A_Layers/viz/main_data_flow.html`](A_Layers/viz/main_data_flow.html). **Features fixed:** 8 transformer
  columns (7 X + `closed_through_line` audit).
- **[`B_Features/`](B_Features/) — Feature explanation ("Plan B"), feature-stages `F0–F5`.** A
  **subordinate helper** (NOT a build SOT, decoupled from any store) explaining what the
  features are and where they come from. Doc
  [`B_Features/feature_explanation_plan_b_eng.md`](B_Features/feature_explanation_plan_b_eng.md); viz
  [`B_Features/viz/feature_dag.html`](B_Features/viz/feature_dag.html).

**Naming rule:** `layer` / `L1–L10` = **A_Layers only**; `feature-stage` / `F0–F5` / `f{stage}_…` = **B_Features only**. Never mix.

## A_Layers (Main_Pipeline · SOT)

- **[`A_Layers/ENG/Layers_Short_SOT/`](A_Layers/ENG/Layers_Short_SOT/)** — the canonical total SOT: short fact-only files owning every parameter/formula/schema/contract (cross-cutting `00_*` + per-layer L1–L10 + QC-01…QC-11 + 7-X manifest + Output A/B + DoD). Governance + fact-ownership map in [`A_Layers/ENG/Layers_Short_SOT/README.md`](A_Layers/ENG/Layers_Short_SOT/README.md).
- [`A_Layers/ENG/readme_eng.md`](A_Layers/ENG/readme_eng.md) — ENG package index. Companion docs below are **subordinate** to the SOT (narrative only; they restate no fact).
- [`A_Layers/ENG/build_contract_eng.md`](A_Layers/ENG/build_contract_eng.md) — build narrative / reader's guide over L1–L10.
- [`A_Layers/ENG/detector_algorithm_eng.md`](A_Layers/ENG/detector_algorithm_eng.md) — reference detector algorithm (L6).
- [`A_Layers/ENG/quality_gate_spec_eng.md`](A_Layers/ENG/quality_gate_spec_eng.md) — L8 worked example + dashboard layout + rationale.
- [`A_Layers/ENG/glossary_eng.md`](A_Layers/ENG/glossary_eng.md) — term dictionary; [`A_Layers/ENG/summary_rules_eng.md`](A_Layers/ENG/summary_rules_eng.md) — the SOT writing standard.
- [`A_Layers/config/`](A_Layers/config/) — `params.json` (Main params + `TOUCH_TOL`) + `universe.txt` (503 tickers).
- [`A_Layers/viz/main_data_flow.html`](A_Layers/viz/main_data_flow.html) — interactive 3D pipeline viz (L1–L10).

## B_Features (Feature explanation · helper)

- [`B_Features/feature_explanation_plan_b_eng.md`](B_Features/feature_explanation_plan_b_eng.md) — what the features are, by feature-stage `F0–F5`; subordinate, decoupled from any store.
- [`B_Features/viz/feature_dag.html`](B_Features/viz/feature_dag.html) — OHLCV → F0–F5 feature DAG (self-contained).

## Open the visualizations

**A_Layers · 3D pipeline — [`A_Layers/viz/main_data_flow.html`](A_Layers/viz/main_data_flow.html)**
- Open in any modern browser, or serve over HTTP (`python3 -m http.server`). Deep-links `#1`…`#9`, `#setup` (L6), `#dq` (L8). Controls: drag = rotate · scroll = zoom · keys `1–9` = views.

**B_Features · feature DAG (OHLCV → F0–F5) — [`B_Features/viz/feature_dag.html`](B_Features/viz/feature_dag.html)**
- Open directly — fully offline. Flows bottom-to-top: OHLCV (F0) → F1 → F2 → F3 → F4 → F5. Click a node → highlight its lineage from F0.

## Notes
- `A_Layers/` is self-contained for the Main_Pipeline build SOT (every contract / parameter / formula inlined).
- The visualizations are frozen snapshots; if you change a canonical value, update the SOT docs and the viz together.
- `layer` / `L1–L10` reserved for `A_Layers`; the feature explanation uses `F0–F5` only.

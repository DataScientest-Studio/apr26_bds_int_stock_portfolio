# Plan — buildable SOT (S&P 500 ML pipeline + OHLCV feature DAG)

The **authoritative, self-contained single source of truth (SOT)** for building this project. Every
contract, parameter, formula, schema, and gate needed to build is inlined **inside `Plan/`** — start
at [`ENG/build_contract_eng.md`](ENG/build_contract_eng.md). It covers **two distinct pipelines**,
each with its own layer scheme — see *Layer numbering* below. All docs are English and use the
canonical terminology defined in [`ENG/glossary_eng.md`](ENG/glossary_eng.md). The visualizations
open standalone (no build step, no dependencies).

## Layer numbering (read this first)

The two pipelines both use an `L#` prefix but mean **different things** — never mix them:

- **Pipeline A — S&P 500 ML strategy · layers `L1–L10`:** Alpaca → LEAN → DuckDB → snapshot →
  split → detector → features/triple-barrier → quality → Optuna/XGBoost → OOS.
  Docs: [`ENG/`](ENG/) (glossary + `L1`–`L10` summaries + the build specs). Viz: [`viz/main_data_flow.html`](viz/main_data_flow.html).
- **Pipeline B — OHLCV → L5 feature engineering · layers `L0–L5`:** raw OHLCV (L0) → atomic
  transforms → rolling/temporal → MTF/regime → classical indicators → research representations.
  Viz: [`viz/feature_dag.html`](viz/feature_dag.html). Build spec: [`ENG/pipelineB_spec_eng.md`](ENG/pipelineB_spec_eng.md).

## Certified build scope

- **Pipeline A v1 — end-to-end** (the detector is a *reference implementation* of the §3 output
  contract; the geometric algorithm is in [`ENG/detector_algorithm_eng.md`](ENG/detector_algorithm_eng.md)).
- **Pipeline B L0–L5** — L0–L3 = the real `qc-transforms` materialization; L4/L5 = reference designs
  (one valid realization), **in the certified scope** (see [`ENG/pipelineB_spec_eng.md`](ENG/pipelineB_spec_eng.md)).
  "Reference design" means "one valid realization", not uncertified.

## Provenance

- Pipeline A docs + 3D viz (`viz/main_data_flow.html`) originate from
  `/opt/to_liora_school/liora-project-ml-pipeline-and-visualisation-sp500`
  (branch `viz/redesign-self-explaining` @ `25f06a1`); Pipeline B grids from
  `qc_raw_ohlcv_data_sp500_alpaca_transforms`.
- **`Plan/` is now the authoritative SOT for building this project** — every required fact is inlined
  here (`ENG/build_contract_eng.md`, `ENG/detector_algorithm_eng.md`, `ENG/quality_gate_spec_eng.md`,
  `ENG/pipelineB_spec_eng.md`, `config/`). The upstream paths above are **provenance / maintenance
  metadata only**; a build does not require them.
- Snapshot/baseline date: 2026-06-15.

## Contents

- [`ENG/build_contract_eng.md`](ENG/build_contract_eng.md) — **the Pipeline A build contract** (inlined,
  English): input contract, detector output contract, the 8 features / 7-X manifest, triple-barrier
  label, time splits, Output A/B schema + `label_uniqueness_weight`, strategy artifact API, full
  parameters, QC-01…QC-11, Definition of Done.
- [`ENG/detector_algorithm_eng.md`](ENG/detector_algorithm_eng.md) — a concrete **reference detector
  algorithm** (one valid realization of the §3 contract): pivots, line fit, `TOUCH_TOL`, entry, DET-09.
- [`ENG/quality_gate_spec_eng.md`](ENG/quality_gate_spec_eng.md) — the L8 quality gate: every counter,
  WARN/FAIL thresholds, the `reports/quality/summary.json` schema, and the gate-aggregation rule.
- [`ENG/pipelineB_spec_eng.md`](ENG/pipelineB_spec_eng.md) — Pipeline B build spec: L0–L3 (certified) +
  L4/L5 (reference design, certified).
- [`ENG/`](ENG/) — also: the 1:1 layer summaries `L1`–`L10`, the writing standard
  ([`ENG/summary_rules_eng.md`](ENG/summary_rules_eng.md)), and the glossary
  ([`ENG/glossary_eng.md`](ENG/glossary_eng.md)). Start at [`ENG/readme_eng.md`](ENG/readme_eng.md).
- [`config/`](config/) — `universe.txt` (503 S&P 500 tickers) and `params.json` (every parameter,
  incl. `TOUCH_TOL`).
- [`viz/main_data_flow.html`](viz/main_data_flow.html) — Pipeline A: interactive 3D pipeline viz (~147 KB, self-contained).
- [`viz/feature_dag.html`](viz/feature_dag.html) — Pipeline B: OHLCV → L5 feature-engineering wireframe (~2.3 MB, self-contained).
- [`AUDIT_BRIEF.md`](AUDIT_BRIEF.md) — the external-audit commission (acceptance criteria + method);
  [`audit/`](audit/) — the latest external audit report + evidence.

## Open the visualizations

**Pipeline A · 3D pipeline — [`viz/main_data_flow.html`](viz/main_data_flow.html)**
- Double-click it, or open it in any modern browser.
- For full interaction, serve over HTTP from this folder, e.g. `python3 -m http.server`
  then open `viz/main_data_flow.html`.
- Deep-links: `viz/main_data_flow.html#1` … `#9` (views), `#setup` (L6), `#dq` (L8), `#L6` (layer contract).
- Controls: drag = rotate · scroll = zoom · click element = details · keys `1–9` = views.

**Pipeline B · feature DAG (OHLCV → L5) — [`viz/feature_dag.html`](viz/feature_dag.html)**
- Double-click it — fully offline, no server and no internet needed (everything is inlined).
- Layout flows bottom-to-top: raw OHLCV (O H L C V) at the bottom → L1 → L2 → L3 → L4 → L5.
- Controls: drag = pan · scroll = zoom · click a node → highlight its lineage from L0 · `clear` to reset.
- Tweaks panel (edit mode): orientation (vertical/horizontal) · style (sketchy/clean) · show formulas.
- All UI/labels in English, aligned with the `ENG/` glossary (candle, rolling, resample, regime, lineage).

## Notes

- `Plan/` is self-contained: the build specs above inline every contract, parameter, formula, and
  schema. References to the source project's layer docs, master spec, or decision registers are
  **"see also" provenance pointers**, never the only source of a build-critical fact.
- The visualizations are frozen snapshots. If you change a canonical value, update it in the SOT docs
  (`ENG/`) **and** the visualizations together so they stay 1:1; propagating a change upstream is
  optional maintenance, not required for a build.

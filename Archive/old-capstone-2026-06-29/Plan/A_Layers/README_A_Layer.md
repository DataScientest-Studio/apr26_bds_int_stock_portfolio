# A_Layers — Main_Pipeline (Pipeline A, L1–L12)

The build package for the project: the S&P 500 ML trend-line meta-labeling strategy pipeline,
**layers L1–L12** (L11 = OOS test, L12 = per-asset deliverable folder). `layer` / `L1–L12` belong here only. Its canonical core — the **single source of
truth** that owns every parameter, formula, schema and contract — is the folder
[`ENG/Layers_Short_SOT/`](ENG/Layers_Short_SOT/).

- **SOT — start here (the whole core):** [`ENG/Layers_Short_SOT/`](ENG/Layers_Short_SOT/) — short, fact-only canonical files (parameters, formulas, schemas, contracts, QC); governance + fact-ownership map in [`ENG/Layers_Short_SOT/README.md`](ENG/Layers_Short_SOT/README.md).
- Config + JSON registries: [`config/parameters.json`](config/parameters.json) · [`config/data_state_numbers.json`](config/data_state_numbers.json) · [`config/universe_tickers.txt`](config/universe_tickers.txt)
- **Frozen data-state numbers (canonical):** [`config/data_state_numbers.json`](config/data_state_numbers.json) — the single home for observed counts/sizes (tickers, zip count, row count, store sizes, candles/day, price scale). Distinct from `config/parameters.json` (knobs) by meaning.
- Viz: [`viz/main_data_flow.html`](viz/main_data_flow.html) — generated from `config/main_data_flow.html.tmpl`.

This folder is a **self-contained SOT**: no acceptance cards, no audit reports, no narrative companions, no
print/PDF artifacts, no third-party dependencies.

## Data-state numbers are single-source & generated
Every data-state number (universe size, zip count, row count, store sizes, candles/day, price scale)
lives **once** in [`config/data_state_numbers.json`](config/data_state_numbers.json). It is generated into the SOT as invisible
`<!--na:…-->…<!--/na-->` marker regions, and into the viz from its `.tmpl`. **Never hand-edit a number in those
files** — edit the registry, then run the build. Tunable design knobs stay in `config/parameters.json`.
The `universe_size` value is the `config/universe_tickers.txt` line count and is documented as the quality-filtered subset of the LEAN ZIP inventory in the registry metadata.

- Build: `python3 config/data_state_gate.py build` (regenerates the SOT markers + viz). Pure standard library, no dependencies.
- Gate: `python3 config/data_state_gate.py check` — fails on any drift or stray hand-typed literal; this is the only thing an audit needs to verify.

Feature explanation (what the features *are*) is a separate, subordinate helper in
[`../B_Features/`](../B_Features/) — it uses Stages `F0–F14`, never `L#`.

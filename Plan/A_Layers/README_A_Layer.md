# A_Layers — Main_Pipeline (Pipeline A, L1–L10)

The build package for the project: the S&P 500 ML trend-line meta-labeling strategy pipeline,
**layers L1–L10**. `layer` / `L1–L10` belong here only. Its canonical core — the **single source of
truth** that owns every parameter, formula, schema and contract — is the folder
[`ENG/Layers_Short_SOT/`](ENG/Layers_Short_SOT/).

- **SOT — start here:** [`ENG/Layers_Short_SOT/`](ENG/Layers_Short_SOT/) — short, fact-only canonical files (parameters, formulas, schemas, contracts, QC); governance + fact-ownership map in [`ENG/Layers_Short_SOT/README.md`](ENG/Layers_Short_SOT/README.md).
- ENG package index: [`ENG/readme_eng.md`](ENG/readme_eng.md)
- Companion docs (subordinate to the SOT — narrative only, they restate no fact): build narrative [`ENG/build_contract_eng.md`](ENG/build_contract_eng.md) · reference detector (L6) [`ENG/detector_algorithm_eng.md`](ENG/detector_algorithm_eng.md) · L8 gate companion [`ENG/quality_gate_spec_eng.md`](ENG/quality_gate_spec_eng.md) · term dictionary [`ENG/glossary_eng.md`](ENG/glossary_eng.md) · writing standard [`ENG/summary_rules_eng.md`](ENG/summary_rules_eng.md)
- Config: [`config/params.json`](config/params.json) · [`config/universe.txt`](config/universe.txt)
- Viz: [`viz/main_data_flow.html`](viz/main_data_flow.html)

Feature explanation (what the features *are*) is a separate, subordinate helper in
[`../B_Features/`](../B_Features/) — it uses Stages `F0–F14`, never `L#`.

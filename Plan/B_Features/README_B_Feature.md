# B_Features — Feature explanation ("Plan B", Stages F0–F14)

A **subordinate helper** explaining *what the features are* and how they are derived — a Universal
OHLCV→feature DAG organized as **Stages F0–F14** (F0,F2–F6 features; F1/F7/F8/F11 data-handling scaffold;
F9/F10 single-asset model; F12 artifact; F13–F14 cross-asset / portfolio). **NOT** a build SOT, **decoupled
from any data store**, and **subordinate** to the
Main_Pipeline ([`../A_Layers/`](../A_Layers/)). Uses **Stages `F0–F14`** and ids
`f{stage}_{metric}…` (ids on the F2–F6 feature Stages; F0 raw unprefixed) — never `layer` / `L#`.

- **SOT — start here:** [`ENG/Stages_Short_SOT/`](ENG/Stages_Short_SOT/) — short, fact-only canonical files (feature-id grammar, families, formulas, guards, selection/calibration); governance + fact-ownership map in [`ENG/Stages_Short_SOT/README.md`](ENG/Stages_Short_SOT/README.md).
- ENG package index: [`ENG/readme_eng.md`](ENG/readme_eng.md)
- High-level overview: [`feature_explanation_plan_b_eng.md`](feature_explanation_plan_b_eng.md)
- Companion docs (subordinate to the SOT): derivations [`ENG/feature_formulas_eng.md`](ENG/feature_formulas_eng.md) · selection+calibration [`ENG/selection_calibration_spec_eng.md`](ENG/selection_calibration_spec_eng.md) · term dictionary [`ENG/glossary_eng.md`](ENG/glossary_eng.md) · writing standard [`ENG/summary_rules_eng.md`](ENG/summary_rules_eng.md)
- Viz: 3D Stages [`viz/main_feature_flow.html`](viz/main_feature_flow.html) · 2D DAG [`viz/feature_dag.html`](viz/feature_dag.html)

The build SOT is the Main_Pipeline — see
[`../A_Layers/ENG/build_contract_eng.md`](../A_Layers/ENG/build_contract_eng.md).

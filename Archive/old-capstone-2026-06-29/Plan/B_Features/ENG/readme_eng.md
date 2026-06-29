# ENG — Plan B documentation package (English)

The SOT for Plan B (the Universal OHLCV→feature DAG, Stages F0–F14) is the folder
**[`Stages_Short_SOT/`](Stages_Short_SOT/)** — short, fact-only files that own every fact (feature-id grammar,
families, formulas, guards, selection/calibration + cross-asset methodology). Start there; its
[`Stages_Short_SOT/README.md`](Stages_Short_SOT/README.md) carries the governance rule and the fact-ownership map.

The files in this `ENG/` root are **subordinate companions**: narrative, derivations, worked examples and term
definitions. They reference the SOT and **redefine no fact**; on any divergence, the SOT wins.

Plan B is **theoretical and decoupled from any data store**, and **subordinate** to the Pipeline-A build SOT
([`../../A_Layers/`](../../A_Layers/)). `stage`/`F0–F14` belong to Plan B only; `layer`/`L1–L10` to Pipeline A only.

## The SOT (`Stages_Short_SOT/`)

Cross-cutting: [`00_conventions_eng.md`](Stages_Short_SOT/00_conventions_eng.md) ·
[`00_families_eng.md`](Stages_Short_SOT/00_families_eng.md) ·
[`00_guards_and_windows_eng.md`](Stages_Short_SOT/00_guards_and_windows_eng.md) ·
[`00_leakage_contract_eng.md`](Stages_Short_SOT/00_leakage_contract_eng.md).

Per Stage:

| Stage | SOT file |
|---|---|
| F0 | [`Stages_Short_SOT/F0_raw_ohlcv_eng.md`](Stages_Short_SOT/F0_raw_ohlcv_eng.md) |
| F1 | [`Stages_Short_SOT/F1_time_split_eng.md`](Stages_Short_SOT/F1_time_split_eng.md) |
| F2 | [`Stages_Short_SOT/F2_atomic_transforms_eng.md`](Stages_Short_SOT/F2_atomic_transforms_eng.md) |
| F3 | [`Stages_Short_SOT/F3_rolling_temporal_eng.md`](Stages_Short_SOT/F3_rolling_temporal_eng.md) |
| F4 | [`Stages_Short_SOT/F4_mtf_regime_eng.md`](Stages_Short_SOT/F4_mtf_regime_eng.md) |
| F5 | [`Stages_Short_SOT/F5_classical_indicators_eng.md`](Stages_Short_SOT/F5_classical_indicators_eng.md) |
| F6 | [`Stages_Short_SOT/F6_research_representations_eng.md`](Stages_Short_SOT/F6_research_representations_eng.md) |
| F7 | [`Stages_Short_SOT/F7_triple_barrier_label_eng.md`](Stages_Short_SOT/F7_triple_barrier_label_eng.md) |
| F8 | [`Stages_Short_SOT/F8_assemble_x_dq_eng.md`](Stages_Short_SOT/F8_assemble_x_dq_eng.md) |
| F9 | [`Stages_Short_SOT/F9_feature_selection_eng.md`](Stages_Short_SOT/F9_feature_selection_eng.md) |
| F10 | [`Stages_Short_SOT/F10_calibration_optuna_eng.md`](Stages_Short_SOT/F10_calibration_optuna_eng.md) |
| F11 | [`Stages_Short_SOT/F11_oos_evaluation_eng.md`](Stages_Short_SOT/F11_oos_evaluation_eng.md) |
| F12 | [`Stages_Short_SOT/F12_artifact_export_eng.md`](Stages_Short_SOT/F12_artifact_export_eng.md) |
| F13 | [`Stages_Short_SOT/F13_cross_asset_entry_table_eng.md`](Stages_Short_SOT/F13_cross_asset_entry_table_eng.md) |
| F14 | [`Stages_Short_SOT/F14_cross_asset_correlation_eng.md`](Stages_Short_SOT/F14_cross_asset_correlation_eng.md) |

## Companion docs (subordinate to the SOT)

- [feature_formulas_eng.md](feature_formulas_eng.md) — extended derivations + worked examples (F2–F5 indicators, F6 methods).
- [selection_calibration_spec_eng.md](selection_calibration_spec_eng.md) — F9 SHAP-like selection + F10 Optuna calibration methodology.
- [glossary_eng.md](glossary_eng.md) — term dictionary (definitions for F0–F14 + cross-cutting concepts).
- [summary_rules_eng.md](summary_rules_eng.md) — the SOT writing standard.
- [`../feature_explanation_plan_b_eng.md`](../feature_explanation_plan_b_eng.md) — the high-level overview (build-narrative analogue, at the package root).

## Visualizations

- [`../viz/main_feature_flow.html`](../viz/main_feature_flow.html) — 3D self-explaining viz of the F0–F14 Stages (analogue of Pipeline A's `main_data_flow.html`).
- [`../viz/feature_dag.html`](../viz/feature_dag.html) — 2D feature DAG (families as columns, click→lineage).

See [`../README_B_Feature.md`](../README_B_Feature.md).

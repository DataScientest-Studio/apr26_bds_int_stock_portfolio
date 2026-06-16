# ENG — Pipeline A documentation package (English)

The build SOT for Pipeline A (S&P 500 trend-line meta-labeling strategy, layers L1–L10) is the folder
**[`Layers_Short_SOT/`](Layers_Short_SOT/)** — short, fact-only files that own every build-critical fact
(parameters, formulas, schemas, contracts, QC). Start there; its
[`Layers_Short_SOT/README.md`](Layers_Short_SOT/README.md) carries the governance rule and the
fact-ownership map.

The files in this `ENG/` root are **subordinate companions**: narrative, rationale, worked examples and
term definitions. They reference the SOT and **redefine no fact**; on any divergence, the SOT wins.

## The SOT (`Layers_Short_SOT/`)

Cross-cutting:

- [`Layers_Short_SOT/00_conventions_eng.md`](Layers_Short_SOT/00_conventions_eng.md) — notation, canonical naming forms, global numbers, cross-cutting rules.
- [`Layers_Short_SOT/00_parameters_eng.md`](Layers_Short_SOT/00_parameters_eng.md) — the single parameter registry.
- [`Layers_Short_SOT/00_input_contract_eng.md`](Layers_Short_SOT/00_input_contract_eng.md) — input OHLCV table schema + naive-ET→UTC rule.
- [`Layers_Short_SOT/00_definition_of_done_eng.md`](Layers_Short_SOT/00_definition_of_done_eng.md) — build acceptance checklist.

Per layer:

| Lv | SOT file |
|----|----------|
| L1 | [`Layers_Short_SOT/L1_source_alpaca_eng.md`](Layers_Short_SOT/L1_source_alpaca_eng.md) |
| L2 | [`Layers_Short_SOT/L2_lean_zip_store_eng.md`](Layers_Short_SOT/L2_lean_zip_store_eng.md) |
| L3 | [`Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md`](Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md) |
| L4 | [`Layers_Short_SOT/L4_snapshot_parquet_eng.md`](Layers_Short_SOT/L4_snapshot_parquet_eng.md) |
| L5 | [`Layers_Short_SOT/L5_time_split_eng.md`](Layers_Short_SOT/L5_time_split_eng.md) |
| L6 | [`Layers_Short_SOT/L6_setup_detector_eng.md`](Layers_Short_SOT/L6_setup_detector_eng.md) |
| L7 | [`Layers_Short_SOT/L7_features_x_label_y_eng.md`](Layers_Short_SOT/L7_features_x_label_y_eng.md) |
| L8 | [`Layers_Short_SOT/L8_data_quality_eng.md`](Layers_Short_SOT/L8_data_quality_eng.md) |
| L9 | [`Layers_Short_SOT/L9_optuna_xgboost_eng.md`](Layers_Short_SOT/L9_optuna_xgboost_eng.md) |
| L10 | [`Layers_Short_SOT/L10_oos_test_eng.md`](Layers_Short_SOT/L10_oos_test_eng.md) |

## Companion docs (subordinate to the SOT)

- [build_contract_eng.md](build_contract_eng.md) — build narrative / reader's guide over L1–L10.
- [detector_algorithm_eng.md](detector_algorithm_eng.md) — reference detector algorithm (L6, one valid realization).
- [quality_gate_spec_eng.md](quality_gate_spec_eng.md) — L8 worked example + dashboard layout + rationale.
- [glossary_eng.md](glossary_eng.md) — term dictionary (definitions for L1–L10 + cross-cutting concepts).
- [summary_rules_eng.md](summary_rules_eng.md) — the writing standard for the SOT.

**Feature explanation ("Plan B").** What the features *are* (families, derivation) is a separate,
subordinate helper — [feature_explanation_plan_b_eng.md](../../B_Features/feature_explanation_plan_b_eng.md)
(Stages F0–F14) — **not** part of the Pipeline-A SOT.

See [`../README_A_Layer.md`](../README_A_Layer.md).

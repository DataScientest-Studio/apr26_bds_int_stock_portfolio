# ENG — Pipeline A layer summaries (English)

English summaries, one 1:1 file per pipeline layer (L1–L10) — only concrete facts: which
files are produced, the naming conventions, what happens to the data.

These summaries are deliberately terse. The **authoritative, inlined build facts** (full
contracts, parameters, formulas, schemas) live in [build_contract_eng.md](build_contract_eng.md)
(plus [detector_algorithm_eng.md](detector_algorithm_eng.md), [quality_gate_spec_eng.md](quality_gate_spec_eng.md),
[pipelineB_spec_eng.md](pipelineB_spec_eng.md)). Any pointer in these summaries to an upstream
source (its spec sections, decision register, or original layer docs) is a **provenance pointer
only** — never the sole source of a build-critical fact. See [`../README.md`](../README.md).

The summary style is defined in [summary_rules_eng.md](summary_rules_eng.md) — actions as
bullets, one sentence = one fact, physical perspective: files / folders / data.

Term definitions for every concept (L1–L10 + cross-cutting): [glossary_eng.md](glossary_eng.md).

| Lv | Summary (EN) |
|----|--------------|
| L1 | [L1_source_alpaca_eng.md](L1_source_alpaca_eng.md) |
| L2 | [L2_lean_zip_store_eng.md](L2_lean_zip_store_eng.md) |
| L3 | [L3_duckdb_raw_view_qc_eng.md](L3_duckdb_raw_view_qc_eng.md) |
| L4 | [L4_snapshot_parquet_eng.md](L4_snapshot_parquet_eng.md) |
| L5 | [L5_time_split_eng.md](L5_time_split_eng.md) |
| L6 | [L6_setup_detector_eng.md](L6_setup_detector_eng.md) |
| L7 | [L7_features_x_label_y_eng.md](L7_features_x_label_y_eng.md) |
| L8 | [L8_data_quality_eng.md](L8_data_quality_eng.md) |
| L9 | [L9_optuna_xgboost_eng.md](L9_optuna_xgboost_eng.md) |
| L10 | [L10_oos_test_eng.md](L10_oos_test_eng.md) |

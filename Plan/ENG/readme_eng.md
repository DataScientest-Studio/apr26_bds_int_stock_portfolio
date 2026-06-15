# FLOW / streszczenie / ENG — short layer descriptions (English)

English mirror of the Polish layer summaries. Each file is a 1:1 summary of one pipeline
layer (L1–L10) — only concrete facts: which files are produced, the naming conventions,
what happens to the data.

Full versions (role, invariants, visualization views, links) are Polish-only and live in
the source project's `FLOW/L*.md`. This minimal snapshot includes the English summaries
only; see [`../README.md`](../README.md) for snapshot provenance.

The summary style is defined in [summary_rules_eng.md](summary_rules_eng.md) — actions as
bullets, one sentence = one fact, physical perspective: files / folders / data.

| Lv | Summary (EN) | Full doc (PL, in source project) |
|----|--------------|----------------------------------|
| L1 | [L1_source_alpaca_eng.md](L1_source_alpaca_eng.md) | `FLOW/L1_zrodlo_alpaca.md` |
| L2 | [L2_lean_zip_store_eng.md](L2_lean_zip_store_eng.md) | `FLOW/L2_lean_zip_store.md` |
| L3 | [L3_duckdb_raw_view_qc_eng.md](L3_duckdb_raw_view_qc_eng.md) | `FLOW/L3_duckdb_raw_view_qc.md` |
| L4 | [L4_snapshot_parquet_eng.md](L4_snapshot_parquet_eng.md) | `FLOW/L4_snapshot_sql_parquet.md` |
| L5 | [L5_time_split_eng.md](L5_time_split_eng.md) | `FLOW/L5_split_warmup_train_oos.md` |
| L6 | [L6_setup_detector_eng.md](L6_setup_detector_eng.md) | `FLOW/L6_detektor_setupu.md` |
| L7 | [L7_features_x_label_y_eng.md](L7_features_x_label_y_eng.md) | `FLOW/L7_cechy_x_etykieta_y.md` |
| L8 | [L8_data_quality_eng.md](L8_data_quality_eng.md) | `FLOW/L8_walidacja_jakosci_danych.md` |
| L9 | [L9_optuna_xgboost_eng.md](L9_optuna_xgboost_eng.md) | `FLOW/L9_optuna_xgboost_strategia.md` |
| L10 | [L10_oos_test_eng.md](L10_oos_test_eng.md) | `FLOW/L10_test_oos.md` |

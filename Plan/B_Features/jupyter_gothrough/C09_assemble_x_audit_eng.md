# C09 · Assemble X + data-quality audit (scaffold · A_Layers L8)

Join all features with the label, drop warm-up, and run a quality gate before any model is fit.

- Realizes: [F8](../ENG/Stages_Short_SOT/F8_assemble_x_dq_eng.md) — data-handling Stage (inlines A_Layers L8); single-asset, per-bar.
- Role: scaffold cell (the gate before [C10](C10_f6_feature_selection_eng.md)/[C11](C11_f7_calibration_optuna_eng.md)).
- Input: the F2–F6 columns ([C03](C03_f1_atomic_transforms_eng.md)–[C07](C07_f5_research_representations_eng.md)), `y`+`sample_weight` ([C08](C08_label_triple_barrier_eng.md)), `split` ([C02](C02_time_split_eng.md)).
- Does:
  - assemble the full candidate matrix `X` (all F2–F6 ids) aligned to `ts`; join `y` and `sample_weight`.
  - drop warm-up rows whose rolling features are still `NULL` (never impute).
  - run a per-asset audit: null-rate, near-zero variance, duplicate `(ts)`, `NaN`/`Inf` beyond documented exceptions, leakage-token scan; aggregate to an `OK / WARN / FAIL` gate.
- Produces: `X` (clean candidate matrix on Train/OOS), aligned `y`/`sample_weight`, and an `audit` report (counters + per-check level + overall status).
- Guards: a **FAIL closes the gate** — the model cells do not run; the audit *measures, fixes nothing* (fixes belong upstream); audit statistics are descriptive and never feed the model ([L8](../../A_Layers/ENG/Layers_Short_SOT/L8_data_quality_eng.md)).
- Check: `X`/`y` row-aligned with no post-warm-up `NaN`; `overall_status ≠ FAIL` before proceeding; no leakage token in column names.
- Output: clean `(X, y, sample_weight)` + `audit` → [C10](C10_f6_feature_selection_eng.md).

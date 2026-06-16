# F8 · Assemble X + data-quality gate (SOT)

A **scaffold / data-handling Stage** (produces no `f{stage}_…` ids): join all features with the label into the
candidate matrix and run a quality gate before any model is fit. Gate concept inlined from the Pipeline-A build
SOT ([A_Layers/L8](../../../A_Layers/ENG/Layers_Short_SOT/L8_data_quality_eng.md)).

- Input: the F2–F6 feature columns, `Y` + `sample_weight` from [F7](F7_triple_barrier_label_eng.md), and the
  `split` from [F1](F1_time_split_eng.md).
- **Assemble:** build the full candidate matrix `X` (all F2–F6 ids) aligned to `ts`; join `Y` and `sample_weight`.
- **Drop warm-up:** drop rows whose rolling features are still `NULL` (never impute).
- **Quality gate (per asset):** null-rate · near-zero variance · duplicate `(ts)` · `NaN`/`Inf` beyond documented
  exceptions · leakage-token scan → aggregate to an `OK / WARN / FAIL` status.
- **Gate rule:** a **FAIL closes the gate** — the model Stages (F9/F10) do not run; the audit **measures, fixes
  nothing** (fixes belong upstream) and never feeds the model.
- **Report:** a frozen `summary.json` (counters + per-check level + overall status).
- Family: none (produces a clean matrix + audit, not features).
- Output: clean `(X, Y, sample_weight)` on Train/OOS + `audit` → consumed by [F9](F9_feature_selection_eng.md).

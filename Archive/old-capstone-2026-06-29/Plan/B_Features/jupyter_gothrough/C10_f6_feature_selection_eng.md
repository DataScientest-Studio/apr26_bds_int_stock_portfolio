# C10 · F6 — Feature selection (model-facing Stage F6)

Reduce the full F2–F6 candidate space to the least-overfitting top-20 subset, inside Train CV only.

- Realizes: [F9](../ENG/Stages_Short_SOT/F9_feature_selection_eng.md).
- Role: model-facing cell (consumes features, produces a subset — no feature ids).
- Input: clean `(X, y, sample_weight)` ([C09](C09_assemble_x_audit_eng.md)) and the CV folds in `split` ([C02](C02_time_split_eng.md)).
- Does: rank by SHAP-like importance and apply the mandatory anti-overfitting filters — stability selection, permutation importance, redundancy/cluster pruning, nested CV, parsimony — exactly as owned by [F6](../ENG/Stages_Short_SOT/F9_feature_selection_eng.md) (methodology in companion [`../ENG/selection_calibration_spec_eng.md`](../ENG/selection_calibration_spec_eng.md)).
- Produces: `selected` — the robust **least-overfitting top-20** feature list; plus the per-feature importance/stability report.
- Guards: importance and the selected subset are computed **inside training folds only** (nested CV), never on the full set and never on OOS; standardization/imputation stats are per training fold ([`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md), Selection-leakage).
- Check: selection ran inside CV folds (no full-set or OOS fit); kept features pass the stability threshold; `len(selected) = 20` (or the parsimony pick within 1 SE).
- Output: `selected` (top-20) → [C11](C11_f7_calibration_optuna_eng.md); selection report → [C13](C13_artifact_export_eng.md).

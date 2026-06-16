# C11 · F7 — Calibration, Optuna (model-facing Stage F7) · THE artifact model

Tune and calibrate the per-asset XGB on the top-20 — the final Stage and the model the artifact wraps.

- Realizes: [F10](../ENG/Stages_Short_SOT/F10_calibration_optuna_eng.md) — the top single-asset model-facing Stage.
- Role: model-facing cell (produces no feature ids).
- Input: `selected` top-20 ([C10](C10_f6_feature_selection_eng.md)), `(X, y, sample_weight)` ([C09](C09_assemble_x_audit_eng.md)), CV folds in `split` ([C02](C02_time_split_eng.md)).
- Does:
  - tune an **XGBoost** on the top-20 with Optuna (TPE sampler, MedianPruner), objective = a CV metric over **purged walk-forward CV in Train only** (one model per asset × direction).
  - map raw scores → probabilities with Platt/isotonic calibration fit on a **held-out** fold (not the model-fit fold).
- Produces: `model` — the per-asset **calibrated XGB**; plus `best_params` and the `calibration_map`.
- Guards: reading OOS during tuning is a contract violation; calibration fold ≠ model-fit fold; same input + same seed → same hyperparameters + same calibration map ([`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md), Calibration-leakage + Determinism). **Stop at the single-asset stages — no cross-asset F13/F14.**
- Check: Optuna objective scored on Train CV only (no OOS read); calibrated probabilities in `[0,1]`; rerun with the same seed reproduces `best_params` + `calibration_map`.
- Output: `model` + `best_params` + `calibration_map` → [C12](C12_oos_evaluation_eng.md) (evaluate) and [C13](C13_artifact_export_eng.md) (bundle).

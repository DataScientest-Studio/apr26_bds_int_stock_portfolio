# F10 · Calibration — Optuna (SOT)

The top **single-asset model-facing Stage** (produces no feature ids): tune and calibrate the per-asset model
on the selected subset. Extended methodology + worked example: companion [../selection_calibration_spec_eng.md](../selection_calibration_spec_eng.md).

- Input: the selected **top-20** feature subset from [F9](F9_feature_selection_eng.md).
- **Estimator:** XGBoost, trained on the top-20 features (one model per asset × direction).
- **Optuna tuning:**
  - sampler: TPE (Tree-structured Parzen Estimator).
  - pruner: MedianPruner.
  - objective: a CV metric (e.g. AUC-PR) over **purged walk-forward CV in Train only** (folds from [F1](F1_time_split_eng.md)).
  - guard: reading OOS during tuning is a contract violation (see [00_leakage_contract_eng.md](00_leakage_contract_eng.md)).
- **Probability calibration:**
  - map raw scores → calibrated probabilities with Platt (sigmoid) or isotonic regression.
  - fit on a **held-out** fold (not the fold used to fit the model).
- **Determinism:** same input + same seed → same tuned hyperparameters + same calibration map (seeds + fitted-object hashes).
- Family: none.
- Output: the **per-asset calibrated XGB** (a `.b64` model artifact, one per asset × direction) → evaluated by [F11](F11_oos_evaluation_eng.md) and bundled by [F12](F12_artifact_export_eng.md).

# F12 · Artifact export (SOT)

A **terminal artifact Stage** (produces no `f{stage}_…` ids): serialize the single-asset run into one
reproducible per-asset bundle — the end of the single-asset go-through (F0→F10). Artifact contract owned here.

- Input: the calibrated XGB + `best_params` + `calibration_map` from [F10](F10_calibration_optuna_eng.md), the
  top-20 `selected` list from [F9](F9_feature_selection_eng.md), the fitted transformers (F4 regime cutoffs,
  F6 standardizer/bases), the split & label config ([F1](F1_time_split_eng.md)/[F7](F7_triple_barrier_label_eng.md)),
  and the `oos_metrics` from [F11](F11_oos_evaluation_eng.md).
- **Bundle:** the calibrated XGB (`.b64`) + the top-20 feature list + all fitted transformers + the split &
  label config + the OOS metrics + a **manifest** (`SYMBOL`, seed, library versions, fitted-object hashes).
- **Determinism:** the bundle captures only fitted-on-Train objects (no OOS-derived state); the manifest's seed
  + hashes let the same `SYMBOL` rebuild **byte-identical** (see [00_leakage_contract_eng.md](00_leakage_contract_eng.md), Determinism).
- Family: none (produces a model bundle, not features).
- Output: the per-asset **artifact** on disk + its manifest → consumed by the cross-asset phase
  ([F13](F13_cross_asset_entry_table_eng.md)).

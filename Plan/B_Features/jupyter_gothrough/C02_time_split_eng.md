# C02 · Time split — Train / OOS (scaffold · A_Layers L5)

Define the disjoint time windows up front, so every later fit touches Train only and OOS stays frozen.

- Realizes: [F1](../ENG/Stages_Short_SOT/F1_time_split_eng.md) — data-handling Stage (inlines A_Layers L5); applied per-bar here, not per-setup.
- Role: scaffold cell.
- Input: `ohlcv` from [C01](C01_f0_load_raw_ohlcv_eng.md).
- Does:
  - split the one continuous series into disjoint **Warm-up / Train / OOS** windows by integer bar position.
  - reserve a **purge + embargo** buffer at the Train→OOS boundary so a label window cannot reach across (label horizon set in [C08](C08_label_triple_barrier_eng.md)).
  - define the **purged walk-forward CV** folds *inside Train* (used by [C10](C10_f6_feature_selection_eng.md) and [C11](C11_f7_calibration_optuna_eng.md)).
- Produces: `split` — boolean masks/index ranges for Warm-up, Train, OOS; the CV fold scheme; purge/embargo sizes.
- Guards: this cell exists so the leakage contract holds — every fit downstream uses **Train only**; OOS is read once, in [C12](C12_oos_evaluation_eng.md). See [`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md) (Fit-on-Train-only).
- Check: windows disjoint and ordered; no CV fold or label window crosses a window boundary (purge/embargo assertion); OOS mask is not referenced by any later cell except C12.
- Output: `split` → all feature-fit cells ([C05](C05_f3_mtf_regime_eng.md), [C07](C07_f5_research_representations_eng.md)) and model cells ([C10](C10_f6_feature_selection_eng.md), [C11](C11_f7_calibration_optuna_eng.md)).

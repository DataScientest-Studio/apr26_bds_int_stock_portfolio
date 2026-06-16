# jupyter_gothrough — single-asset end-to-end go-through (the notebook work-order, Stages F0–F12)

This folder is the **work-order (spec) for one future Jupyter notebook**: take **one** asset (one of the 503
SP500 names, selectable at runtime), recompute it through **every single-asset Stage F0→F12 from raw OHLCV**,
and end in a real per-asset **artifact** (the F10-calibrated XGB, bundled at F12). It is **docs only** — the
`.ipynb` is future work; each file here describes exactly **one notebook cell**. Cell `C{n}` realizes Stage
`F{n−1}` (C01→F0 … C13→F12); C00 is the run harness. Cross-asset F13/F14 are out of scope (single asset only).

**One notebook Cell ↔ one spec file.** Each `C{NN}_*_eng.md` describes a single cell with the same fact-only
authoring discipline as [`../ENG/Stages_Short_SOT/README.md`](../ENG/Stages_Short_SOT/README.md).

This folder is **subordinate** to the SOT, like the companions: it owns *only* "how the notebook runs each
step" facts (cell role, inputs, operations, outputs, acceptance checks). All feature formulas, families,
guards, selection and calibration facts stay owned by [`../ENG/Stages_Short_SOT/`](../ENG/Stages_Short_SOT/);
the cell files **reference** them, never restate them.

## Governance (the canonical rule)

1. **The SOT is canonical.** This folder, like the companions at [`../ENG/`](../ENG/), is **subordinate**: it
   demonstrates the DAG on real data, owns no canonical feature facts, and **references** the SOT, never
   redefines it.
2. **Each fact has exactly one home.** A cell file links to the SOT/Layer that owns its underlying facts (the
   cell-ownership map below); it never copies a formula, family, guard or threshold.
3. **On any divergence, the SOT wins** — fix this folder (or the viz) to match
   [`../ENG/Stages_Short_SOT/`](../ENG/Stages_Short_SOT/).
4. **Style:** facts only — dense bullets, one fact per line, no narrative or worked examples (those live in the
   companions). English-only.

## Notebook contract

- **One selectable asset.** `SYMBOL` ∈ the 503-name universe (`A_Layers/config/universe.txt`); change one
  variable → the whole notebook re-runs for a different ticker. No cross-asset logic.
- **Recompute every Stage from raw OHLCV.** F2–F6 are computed in-notebook from the F0 channels; the
  pre-built transforms parquet is used (if at all) only as an **optional cross-check**, never as the source.
- **Single-asset Stages F0–F12 only.** No cross-asset F13/F14. The data-handling Stages (F1 split, F7 label,
  F8 assemble+DQ, F11 OOS) and the F12 artifact are now first-class SOT Stages, interleaved with the features.
- **Deterministic.** One seed → identical features, selected subset, calibrated model, and artifact bytes
  (per the SOT determinism rule, [`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md)).
- **Leakage contract is the backbone of the cell order.** Split (C02 = F1) precedes every fit-on-Train cell (F4
  regimes, F6 bases, F9 selection, F10 tuning/calibration); the OOS window is read **once**, in C12 (F11).
- **Final artifact.** The bundle defined in [C13](C13_artifact_export_eng.md) (F12): calibrated XGB (`.b64`) +
  selected feature list + fitted transformers (F4 cutoffs, F6 standardizer/bases) + split & label config +
  OOS metrics + a reproducibility manifest (`SYMBOL`, seed, versions, hashes).

## Files

| Cell | File | Role | Realizes |
|---|---|---|---|
| C00 | [C00_setup_and_asset_select_eng.md](C00_setup_and_asset_select_eng.md) | run harness | setup · `SYMBOL` (1 of 503) · seed (no Stage) |
| C01 | [C01_f0_load_raw_ohlcv_eng.md](C01_f0_load_raw_ohlcv_eng.md) | feature Stage | [F0](../ENG/Stages_Short_SOT/F0_raw_ohlcv_eng.md) |
| C02 | [C02_time_split_eng.md](C02_time_split_eng.md) | data-handling Stage | [F1](../ENG/Stages_Short_SOT/F1_time_split_eng.md) |
| C03 | [C03_f1_atomic_transforms_eng.md](C03_f1_atomic_transforms_eng.md) | feature Stage | [F2](../ENG/Stages_Short_SOT/F2_atomic_transforms_eng.md) |
| C04 | [C04_f2_rolling_temporal_eng.md](C04_f2_rolling_temporal_eng.md) | feature Stage | [F3](../ENG/Stages_Short_SOT/F3_rolling_temporal_eng.md) |
| C05 | [C05_f3_mtf_regime_eng.md](C05_f3_mtf_regime_eng.md) | feature Stage | [F4](../ENG/Stages_Short_SOT/F4_mtf_regime_eng.md) |
| C06 | [C06_f4_classical_indicators_eng.md](C06_f4_classical_indicators_eng.md) | feature Stage | [F5](../ENG/Stages_Short_SOT/F5_classical_indicators_eng.md) |
| C07 | [C07_f5_research_representations_eng.md](C07_f5_research_representations_eng.md) | feature Stage | [F6](../ENG/Stages_Short_SOT/F6_research_representations_eng.md) |
| C08 | [C08_label_triple_barrier_eng.md](C08_label_triple_barrier_eng.md) | data-handling Stage | [F7](../ENG/Stages_Short_SOT/F7_triple_barrier_label_eng.md) |
| C09 | [C09_assemble_x_audit_eng.md](C09_assemble_x_audit_eng.md) | data-handling Stage | [F8](../ENG/Stages_Short_SOT/F8_assemble_x_dq_eng.md) |
| C10 | [C10_f6_feature_selection_eng.md](C10_f6_feature_selection_eng.md) | model-facing Stage | [F9](../ENG/Stages_Short_SOT/F9_feature_selection_eng.md) |
| C11 | [C11_f7_calibration_optuna_eng.md](C11_f7_calibration_optuna_eng.md) | model-facing Stage | [F10](../ENG/Stages_Short_SOT/F10_calibration_optuna_eng.md) |
| C12 | [C12_oos_evaluation_eng.md](C12_oos_evaluation_eng.md) | data-handling Stage | [F11](../ENG/Stages_Short_SOT/F11_oos_evaluation_eng.md) |
| C13 | [C13_artifact_export_eng.md](C13_artifact_export_eng.md) | artifact Stage | [F12](../ENG/Stages_Short_SOT/F12_artifact_export_eng.md) |

Cells **C01–C13 each realize one SOT Stage F0–F12** (C00 is the run harness, no Stage). The data-handling
Stages F1/F7/F8/F11 inline the matching A_Layers facts (L5/L7/L8/L10); cross-asset Stages F13/F14 are out of
scope for this single-asset notebook.

## Cell-ownership map

Each cell file owns only its "how the notebook runs this step" facts; the underlying facts live in:

| Underlying fact a cell needs | Home (linked, never restated) |
|---|---|
| Feature-id grammar · F-Stage scheme · causality | [`00_conventions_eng.md`](../ENG/Stages_Short_SOT/00_conventions_eng.md) |
| The 6 families + legend colours | [`00_families_eng.md`](../ENG/Stages_Short_SOT/00_families_eng.md) |
| `ε`, `safe_div/safe_max/safe_log_ratio`, `σ=0→0`, windows | [`00_guards_and_windows_eng.md`](../ENG/Stages_Short_SOT/00_guards_and_windows_eng.md) |
| Causality · backward-only · Train-only fit · selection/calibration leakage · determinism | [`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md) |
| F0,F2–F6 formulas / families / methods | the matching feature-stage file in [`../ENG/Stages_Short_SOT/`](../ENG/Stages_Short_SOT/) |
| F9 selection · F10 calibration | [`F9`](../ENG/Stages_Short_SOT/F9_feature_selection_eng.md) · [`F10`](../ENG/Stages_Short_SOT/F10_calibration_optuna_eng.md) (methodology: [`../ENG/selection_calibration_spec_eng.md`](../ENG/selection_calibration_spec_eng.md)) |
| Time split (purge/embargo) · triple-barrier label · quality gate · one-shot OOS | [`F1`](../ENG/Stages_Short_SOT/F1_time_split_eng.md) · [`F7`](../ENG/Stages_Short_SOT/F7_triple_barrier_label_eng.md) · [`F8`](../ENG/Stages_Short_SOT/F8_assemble_x_dq_eng.md) · [`F11`](../ENG/Stages_Short_SOT/F11_oos_evaluation_eng.md) (each inlines the matching A_Layers L5/L7/L8/L10 facts) |

## Cross-references

- SOT (canonical): [`../ENG/Stages_Short_SOT/`](../ENG/Stages_Short_SOT/) · governance + fact-ownership in its [README.md](../ENG/Stages_Short_SOT/README.md).
- Companions: derivations [`../ENG/feature_formulas_eng.md`](../ENG/feature_formulas_eng.md) · selection+calibration [`../ENG/selection_calibration_spec_eng.md`](../ENG/selection_calibration_spec_eng.md).
- High-level overview: [`../feature_explanation_plan_b_eng.md`](../feature_explanation_plan_b_eng.md).
- Viz: 3D Stages [`../viz/main_feature_flow.html`](../viz/main_feature_flow.html) — renders this notebook's C00→C13 path as the main **F0–F12** single-asset stack (data-handling Stages F1/F7/F8/F11 shown dim, F12 artifact gold), with the cross-asset F13/F14 phase on top · 2D DAG [`../viz/feature_dag.html`](../viz/feature_dag.html).
- Folder framing: [`../README_B_Feature.md`](../README_B_Feature.md) · writing standard [`../ENG/summary_rules_eng.md`](../ENG/summary_rules_eng.md).

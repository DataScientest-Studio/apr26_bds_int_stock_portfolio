# C13 · Artifact export (scaffold)

Bundle the run into one reproducible per-asset artifact — the notebook's final effect.

- Realizes: [F12](../ENG/Stages_Short_SOT/F12_artifact_export_eng.md) — the artifact bundle Stage (contract in [README.md](README.md)).
- Role: scaffold cell (terminal).
- Input: `model`/`best_params`/`calibration_map` ([C11](C11_f7_calibration_optuna_eng.md)), `selected` ([C10](C10_f6_feature_selection_eng.md)), fitted `regime_cutoffs` ([C05](C05_f3_mtf_regime_eng.md)) + `standardizer`/bases ([C07](C07_f5_research_representations_eng.md)), `label_config` ([C08](C08_label_triple_barrier_eng.md)), `audit` ([C09](C09_assemble_x_audit_eng.md)), `oos_metrics` ([C12](C12_oos_evaluation_eng.md)), `versions`/`SEED` ([C00](C00_setup_and_asset_select_eng.md)).
- Does: serialize one artifact bundle for `SYMBOL` — the calibrated XGB (`.b64`), the top-20 feature list, all fitted transformers (F3 cutoffs, F5 standardizer/bases), the split + label config, the OOS metrics, and a manifest (`SYMBOL`, `SEED`, library versions, fitted-object hashes).
- Produces: the per-asset **artifact** on disk + its manifest.
- Guards: the artifact captures exactly the fitted-on-Train objects (no OOS-derived state); determinism — the manifest's seed + hashes let the same `SYMBOL` rebuild byte-identical ([`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md), Determinism).
- Check: bundle re-loads and reproduces `oos_metrics` from C12; manifest hashes match the fitted objects; no cross-asset (F13/F14) content.
- Output: the saved artifact — the end of the single-asset go-through (Stages F0→F12).

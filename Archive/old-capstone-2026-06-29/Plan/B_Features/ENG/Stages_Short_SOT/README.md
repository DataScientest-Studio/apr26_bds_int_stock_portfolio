# Stages_Short_SOT — the total SOT for Plan B (Universal feature DAG, F-Stages)

This folder is the **single source of truth** for the Plan-B pipeline: the Universal OHLCV→feature DAG plus the
data-handling and model stages, organized as **Stages F0–F14** — F0,F2–F6 feature stages; F1/F7/F8/F11
data-handling scaffold; F9/F10 single-asset model; F12 artifact; F13–F14 cross-asset / portfolio. Every fact —
feature-id grammar, families, formulas, guards, the data split/label/assemble/OOS chunking, selection,
calibration, and cross-asset methodology — is defined here, **once**, in short fact-only files. The data stages
F1/F7/F8/F11 inline the matching Pipeline-A facts (L5/L7/L8/L10) so a single asset has the data **in chunks** to
build its XGB artifact.

Plan B is **theoretical and decoupled from any data store**, and **subordinate** to the Pipeline-A build SOT
([`../../../A_Layers/`](../../../A_Layers/)). It explains *what features are and how they are derived*; it is
not a build pipeline and Pipeline A does not depend on it.

## Governance (the canonical rule)

1. **This folder is canonical.** The companion docs at [`../`](..) (`feature_formulas_eng.md`,
   `selection_calibration_spec_eng.md`, `glossary_eng.md`, `readme_eng.md`, `summary_rules_eng.md`) and the
   root [`../../feature_explanation_plan_b_eng.md`](../../feature_explanation_plan_b_eng.md) are **subordinate**:
   narrative, derivations, worked examples, definitions. They **reference** the facts here, never redefine them.
2. **Each fact has exactly one home** (the fact-ownership map below).
3. **On any divergence, the SOT wins** — fix the companion or the viz to match this folder.
4. **Style:** facts only — dense bullets/tables, one fact per line, no narrative or worked examples (those
   live in the companions). This is what keeps the *total* SOT *short*.

## Files

Cross-cutting (own facts that span Stages):

- [00_conventions_eng.md](00_conventions_eng.md) — notation · feature-id grammar · the F0–F14 Stage scheme · causality.
- [00_families_eng.md](00_families_eng.md) — the 6 feature families + their legend colours.
- [00_guards_and_windows_eng.md](00_guards_and_windows_eng.md) — `ε`, guard functions, `σ=0→0`, illustrative windows.
- [00_leakage_contract_eng.md](00_leakage_contract_eng.md) — causality · backward-only · Train-only fit · selection/calibration leakage.

Per Stage (own that Stage's facts):

| Stage | File | Kind |
|---|---|---|
| F0 | [F0_raw_ohlcv_eng.md](F0_raw_ohlcv_eng.md) | feature Stage (raw input) |
| F1 | [F1_time_split_eng.md](F1_time_split_eng.md) | scaffold (Warm-up / Train / OOS · purge + embargo · CV) |
| F2 | [F2_atomic_transforms_eng.md](F2_atomic_transforms_eng.md) | feature Stage |
| F3 | [F3_rolling_temporal_eng.md](F3_rolling_temporal_eng.md) | feature Stage |
| F4 | [F4_mtf_regime_eng.md](F4_mtf_regime_eng.md) | feature Stage |
| F5 | [F5_classical_indicators_eng.md](F5_classical_indicators_eng.md) | feature Stage |
| F6 | [F6_research_representations_eng.md](F6_research_representations_eng.md) | feature Stage |
| F7 | [F7_triple_barrier_label_eng.md](F7_triple_barrier_label_eng.md) | scaffold (triple-barrier label Y + sample weight) |
| F8 | [F8_assemble_x_dq_eng.md](F8_assemble_x_dq_eng.md) | scaffold (assemble X F2–F6 + data-quality gate) |
| F9 | [F9_feature_selection_eng.md](F9_feature_selection_eng.md) | model-facing (SHAP-like → least-overfitting top-20) |
| F10 | [F10_calibration_optuna_eng.md](F10_calibration_optuna_eng.md) | model-facing (Optuna + calibration of an XGB on the top-20) |
| F11 | [F11_oos_evaluation_eng.md](F11_oos_evaluation_eng.md) | scaffold (one-shot OOS · PF · Sharpe · MDD · TIM · WR) |
| F12 | [F12_artifact_export_eng.md](F12_artifact_export_eng.md) | artifact (per-asset XGB bundle + manifest) |
| F13 | [F13_cross_asset_entry_table_eng.md](F13_cross_asset_entry_table_eng.md) | cross-asset (503 binary 0/1 entry columns) |
| F14 | [F14_cross_asset_correlation_eng.md](F14_cross_asset_correlation_eng.md) | cross-asset (correlated peers' entries → augmented XGB) |

## Fact-ownership map

| Canonical fact | Home |
|---|---|
| Notation; feature-id grammar; F0–F14 Stage scheme; causality | `00_conventions_eng.md` |
| The 6 families + legend colours | `00_families_eng.md` |
| `ε`, `safe_div/safe_max/safe_log_ratio`, `σ=0→0`, illustrative windows | `00_guards_and_windows_eng.md` |
| Causality / backward-only / Train-only fit / selection & calibration & cross-asset leakage | `00_leakage_contract_eng.md` |
| Raw channels | `F0` |
| Time split (Warm-up/Train/OOS · purge + embargo · CV folds) | `F1` |
| F2 atomic formulas | `F2` |
| F3 rolling/temporal formulas | `F3` |
| F4 MTF/regime/session | `F4` |
| F5 indicator canonical short forms | `F5` |
| F6 representation methods | `F6` |
| Triple-barrier label Y + sample weight | `F7` |
| Assemble X (F2–F6) + data-quality gate | `F8` |
| F9 SHAP-like importance + anti-overfitting selection (→ top-20) | `F9` |
| F10 Optuna tuning + probability calibration (XGB on top-20) | `F10` |
| One-shot OOS evaluation (PF · Sharpe · MDD · TIM · WR) | `F11` |
| Per-asset artifact bundle + manifest | `F12` |
| F13 cross-asset entry table (503 binary 0/1 entry columns) | `F13` |
| F14 cross-asset correlation + peer-entry augmentation + cross-asset XGB | `F14` |

## Companions (subordinate)

- [../feature_formulas_eng.md](../feature_formulas_eng.md) — extended derivations + worked examples (F2–F5 indicators, F6 methods).
- [../selection_calibration_spec_eng.md](../selection_calibration_spec_eng.md) — F9 selection + F10 calibration methodology, worked example, anti-leakage rationale.
- [../glossary_eng.md](../glossary_eng.md) — term dictionary.
- [../readme_eng.md](../readme_eng.md) — ENG package index.
- [../summary_rules_eng.md](../summary_rules_eng.md) — the SOT writing standard.
- [../../feature_explanation_plan_b_eng.md](../../feature_explanation_plan_b_eng.md) — the high-level overview (build-narrative analogue).

The interactive viz are [`../../viz/main_feature_flow.html`](../../viz/main_feature_flow.html) (3D Stages) and
[`../../viz/feature_dag.html`](../../viz/feature_dag.html) (2D DAG).

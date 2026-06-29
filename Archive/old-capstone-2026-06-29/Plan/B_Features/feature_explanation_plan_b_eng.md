# Feature explanation ("Plan B") — Universal OHLCV→feature DAG (overview)

> **Subordinate helper, not a build SOT.** This is the high-level **overview** of Plan B — the Universal
> OHLCV→feature DAG. It is **not** the build source of truth and is **decoupled from any specific data store**
> (no materialization plan, no parquet layout). The build SOT is **Pipeline A**
> ([`A_Layers/ENG/build_contract_eng.md`](../A_Layers/ENG/build_contract_eng.md)).
>
> **Canonical detail lives in the SOT.** Every grammar, family, formula, guard and method is owned by the
> short fact-only files in [`ENG/Stages_Short_SOT/`](ENG/Stages_Short_SOT/) (start at its
> [`README.md`](ENG/Stages_Short_SOT/README.md)); the `ENG/` companions add derivations and worked examples.
> This page restates no fact — it points there.
>
> **Naming reserved.** Plan B uses **Stages `F0–F14`** and feature ids `f{stage}_{metric}[_{params}][_{timeframe}]`
> (ids on the F2–F6 feature Stages; F0 raw channels unprefixed); `layer`/`L1–L10` belong to **Pipeline A**.

## The DAG in one screen

OHLCV flows bottom→top through **15 Stages**. F0,F2–F6 are **feature Stages** (they produce features); F1/F7/F8/F11
are **data-handling scaffold** (split, label, assemble+DQ, OOS — they chunk the data Train-only); F9/F10 are
single-asset **model-facing Stages**; F12 is the per-asset **artifact**; F13–F14 are **cross-asset / portfolio
Stages** (across the 503 per-asset models). Every feature is a causal function of its inputs back to F0.

| Stage | What it adds | SOT file |
|---|---|---|
| **F0** Raw OHLCV | the five channels + `ts` | [F0](ENG/Stages_Short_SOT/F0_raw_ohlcv_eng.md) |
| **F1** Time split | Warm-up / Train / OOS · purge + embargo · CV folds | [F1](ENG/Stages_Short_SOT/F1_time_split_eng.md) |
| **F2** Atomic transforms | per-bar range/body/wicks/returns/gap/CLV/volume | [F2](ENG/Stages_Short_SOT/F2_atomic_transforms_eng.md) |
| **F3** Rolling / temporal | momentum, realized vol, z-score, drawdown over windows `n` | [F3](ENG/Stages_Short_SOT/F3_rolling_temporal_eng.md) |
| **F4** MTF / regime | resample 1h→1d, vol/volume regimes, session phase | [F4](ENG/Stages_Short_SOT/F4_mtf_regime_eng.md) |
| **F5** Classical indicators | RSI, MACD, ATR, OBV, ADL, Stoch, ADX, MFI, VWAP-distance | [F5](ENG/Stages_Short_SOT/F5_classical_indicators_eng.md) |
| **F6** Research representations | PCA, wavelet, autoencoder, sequence embedding | [F6](ENG/Stages_Short_SOT/F6_research_representations_eng.md) |
| **F7** Triple-barrier label | label `Y ∈ {0,1}` + `sample_weight` | [F7](ENG/Stages_Short_SOT/F7_triple_barrier_label_eng.md) |
| **F8** Assemble X + DQ gate | candidate matrix (F2–F6) + data-quality gate | [F8](ENG/Stages_Short_SOT/F8_assemble_x_dq_eng.md) |
| **F9** Feature selection | SHAP-like importance + anti-overfitting → least-overfitting **top-20** | [F9](ENG/Stages_Short_SOT/F9_feature_selection_eng.md) |
| **F10** Calibration | Optuna tuning (Train-only CV) + probability calibration of an **XGB on the top-20** | [F10](ENG/Stages_Short_SOT/F10_calibration_optuna_eng.md) |
| **F11** OOS evaluation | one-shot · PF · Sharpe · MDD · TIM · WR | [F11](ENG/Stages_Short_SOT/F11_oos_evaluation_eng.md) |
| **F12** Artifact export | per-asset XGB bundle (`.b64`) + transformers + manifest | [F12](ENG/Stages_Short_SOT/F12_artifact_export_eng.md) |
| **F13** Cross-asset entry table | 503 binary enter/no-enter columns (0/1) stacked across the universe | [F13](ENG/Stages_Short_SOT/F13_cross_asset_entry_table_eng.md) |
| **F14** Cross-asset correlation | correlated peers' 0/1 entries appended to the top-20 → cross-asset XGB | [F14](ENG/Stages_Short_SOT/F14_cross_asset_correlation_eng.md) |

Features carry one of **6 families** (price · returns · range · candle · volume · meta) — the legend colour in
the DAG; see [`ENG/Stages_Short_SOT/00_families_eng.md`](ENG/Stages_Short_SOT/00_families_eng.md).

The model-facing Stages are the theoretical "gate" of Plan B: a feature or model that cannot survive
**anti-overfitting selection** (F9) and **leakage-free calibration** (F10) does not proceed; the **cross-asset**
Stages (F13–F14) then let correlated peers' entry signals augment the per-asset top-20
([`ENG/selection_calibration_spec_eng.md`](ENG/selection_calibration_spec_eng.md)).

## Visualizations

- [`viz/main_feature_flow.html`](viz/main_feature_flow.html) — 3D self-explaining viz of the F0–F14 Stages.
- [`viz/feature_dag.html`](viz/feature_dag.html) — 2D feature DAG (families as columns, click→lineage).

## Relationship to Pipeline A

Pipeline A's **L7** uses a small hand-crafted set of trend-line-geometry features — the 8 transformer columns
(7 in `FEATURE_MANIFEST` + `closed_through_line` audit), specified in
[`build_contract_eng.md`](../A_Layers/ENG/build_contract_eng.md). That is **not** this general feature library.
This document explains the broader OHLCV feature space for understanding only; it is **not** a build
dependency of Pipeline A.

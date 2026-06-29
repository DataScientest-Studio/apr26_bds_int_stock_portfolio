# GLOSSARY — Plan B feature DAG (term dictionary)

> **Subordinate to the SOT.** This is a **term dictionary** — concise definitions of the concepts in the
> Universal feature DAG. It is **not** the canonical source: the authoritative grammar, families, formulas,
> guards and methodology are owned by [`Stages_Short_SOT/`](Stages_Short_SOT/). Where an entry needs a
> formula or value, it **points to the SOT**; on any divergence, the SOT wins.

`stage`/`F0–F14` belong to Plan B only; `layer`/`L1–L10` to Pipeline A. Notation, the feature-id grammar and
the family colours are owned by [`Stages_Short_SOT/00_conventions_eng.md`](Stages_Short_SOT/00_conventions_eng.md)
and [`Stages_Short_SOT/00_families_eng.md`](Stages_Short_SOT/00_families_eng.md).

## Cross-cutting

- **Universal feature DAG** — the OHLCV→feature graph; every node is a causal function of its inputs back to F0.
- **Feature Stage** — a level of the DAG that produces features: `F0` raw + `F2…F6`. (`F1/F7/F8/F11` are data-handling scaffold; `F9` selection, `F10` calibration are single-asset model-facing; `F12` is the artifact; `F13` entry table, `F14` correlation are cross-asset / portfolio Stages.)
- **feature-id** — `f{stage}_{metric}[_{params}][_{timeframe}]` (ids on F2–F6; F0 raw unprefixed).
- **family** — one of `price · returns · range · candle · volume · meta`; a separate attribute (the legend colour).
- **causality / no look-ahead** — a feature at `t` uses only bars `≤ t`; windows are backward-only.
- **guard** — `safe_div`, `safe_max`, `safe_log_ratio`, `σ=0→0` with `ε=1e-9` (owned by `00_guards_and_windows_eng.md`).
- **Train-only fit** — fitted objects (F4 regime cutoffs, F6 representations, F9 selection, F10 calibration, F14 cross-asset correlation + peer selection) are fit on Train only, applied forward (see `00_leakage_contract_eng.md`).

## Stages

- **F0 · Raw OHLCV** — `open/high/low/close/volume` + `ts`; the base channels.
- **F1 · Time split** — disjoint Warm-up / Train / OOS windows + purge + embargo + purged walk-forward CV folds (scaffold; inlines A_Layers L5).
- **F2 · Atomic transforms** — point-wise features on one bar / adjacent pair (range, body, wicks, returns, gap, CLV, volume); formulas in the F2 SOT.
- **F3 · Rolling / temporal** — lags + rolling windows of length `n` (momentum, realized vol, z-score, drawdown).
- **F4 · MTF / regime** — resample 1h→1d, regime buckets (vol/volume), session phase; conditions other features (dashed context edges).
- **F5 · Classical indicators** — textbook indicators (RSI, MACD, ATR, OBV, ADL, Stochastic, ADX, MFI, VWAP-distance); derivations in [feature_formulas_eng.md](feature_formulas_eng.md).
- **F6 · Research representations** — learned/applied representations of the F2–F5 stack (PCA, wavelet, autoencoder, sequence embedding).
- **F7 · Triple-barrier label** — supervised target `Y ∈ {0,1}` (TP/SL/time) + `sample_weight` (scaffold; inlines A_Layers L7).
- **F8 · Assemble X + DQ gate** — join F2–F6 into the candidate matrix + a data-quality gate (scaffold; inlines A_Layers L8).
- **F9 · Feature selection** — choose the robust, non-overfitting subset (SHAP-like importance + stability selection + permutation importance + redundancy pruning + nested CV + parsimony) → the least-overfitting **top-20**.
- **F10 · Calibration** — Optuna tuning (TPE + MedianPruner, purged walk-forward CV, Train-only) + probability calibration (Platt / isotonic on held-out) of an **XGB on the top-20** (per asset × direction).
- **F11 · OOS evaluation** — one-shot run over the frozen OOS window → PF · Sharpe · MDD · TIM · WR (scaffold; inlines A_Layers L10).
- **F12 · Artifact export** — one reproducible per-asset bundle: XGB `.b64` + top-20 + transformers + split/label config + OOS metrics + manifest.
- **F13 · Cross-asset entry table** — the per-asset XGBs' binary enter/no-enter signals stacked across the universe into a 503-column 0/1 table (rows = time).
- **F14 · Cross-asset correlation** — correlated peers' 0/1 entries (selected Train-only) appended to the top-20 → a cross-asset XGB augments the per-asset model.

## Method terms (F9 / F10 / F14)

- **cross-asset entry table** — a wide 0/1 matrix: rows = time, columns = the 503 assets' enter/no-enter signals.
- **peer selection** — per target asset, the most correlated other assets whose entry columns are added as features (Train-only, causal `≤ t`).

- **SHAP-like importance** — per-feature Shapley-value-style additive attribution of the model output.
- **stability selection** — keep a feature only if it is important across resamples (selection frequency ≥ threshold).
- **permutation importance** — importance estimated by the score drop when a feature is randomly permuted.
- **redundancy / cluster pruning** — collapse correlated features to one representative per cluster.
- **nested CV** — selection/tuning performed inside training folds only (no selection leakage).
- **parsimony (1-SE rule)** — prefer the smallest subset within one standard error of the best CV score.
- **Optuna / TPE / MedianPruner** — the tuner, its Bayesian sampler, and its pruner.
- **probability calibration** — mapping raw scores to calibrated probabilities (Platt sigmoid / isotonic).

## Representation terms (F6)

- **PCA** — principal components of the standardized feature stack.
- **wavelet (DWT, db4)** — multi-resolution energies (Daubechies-4).
- **autoencoder** — a learned low-dimensional code.
- **sequence embedding** — a recurrent (LSTM) embedding of the recent feature sequence.

## Relationship to Pipeline A

Pipeline A's L7 uses a small hand-crafted trend-line-geometry feature set (8 transformer columns). This DAG
is the **broader, theoretical** feature space — a helper for understanding, **not** a build dependency of
Pipeline A. Full framing: [`../feature_explanation_plan_b_eng.md`](../feature_explanation_plan_b_eng.md).

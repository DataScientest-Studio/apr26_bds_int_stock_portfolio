# 00 · Conventions (SOT)

Canonical home for notation, the feature-id grammar, the F-Stage scheme and the causality rule of the
Universal OHLCV→feature DAG ("Plan B"). Owned here; companion docs reference this file and restate nothing.

Plan B is **theoretical and decoupled from any data store**: it explains *what features are and how they are
derived*, not a build pipeline. It is **subordinate** to the Pipeline-A build SOT and Pipeline A does not
depend on it.

## Notation

- `t` = bar index (integer position after ascending sort by time, one continuous series per asset).
- `c / o / h / l / v` = close / open / high / low / volume of bar `t`; `prev_close` = `close[t−1]`.
- `n` = rolling window length; `k` = lag. `ε = 1e-9` (division/log guard).
- All windows look **backward only** (zero look-ahead); see [00_leakage_contract_eng.md](00_leakage_contract_eng.md).

## Feature-id grammar

```
f{stage}_{metric}[_{params}][_{timeframe}]
```

- `{stage}` — the feature-stage the metric belongs to: **`f2 … f6`** (F0 raw channels are unprefixed; the scaffold F1/F7/F8/F11, model F9/F10, artifact F12 and cross-asset F13/F14 stages produce **no** feature ids).
- `{metric}` — the metric / abbreviation (`r` = close-to-close return, `mom` = momentum, `vol` = volatility, `tp` = typical price, …).
- `{params}` — optional window / lag tokens (`n` = rolling length, `k` = lag).
- `{timeframe}` — optional `1h` / `1d` / `mtf`.
- **`family` is a separate attribute, not an id token** (see [00_families_eng.md](00_families_eng.md)).
- Examples: `f2_r_cc` (returns) · `f2_tp` (price) · `f3_mom_n` (returns) · `f4_vol_regime` (meta) · `f5_atr` (range) · `f6_pca_8` (meta).

## F-Stage scheme (the 15 Stages, bottom → top)

- **Feature Stages (produce features, have `f{stage}_…` ids):**
  - **F0** — Raw OHLCV (the five channels + `ts`; channels are unprefixed).
  - **F2** — Atomic transforms (point-wise on one bar / adjacent pair).
  - **F3** — Rolling / temporal (lags + rolling windows of length `n`).
  - **F4** — MTF / regime / context (resample 1h→1d, regime buckets, session phase).
  - **F5** — Classical indicators (compressed functions of F2–F4).
  - **F6** — Research representations (stack F2–F5 → standardize → learned representation).
- **Scaffold / data-handling Stages (chunk the data; no feature ids):**
  - **F1** — Time split (Warm-up / Train / OOS · purge + embargo · CV folds).
  - **F7** — Triple-barrier label (Y ∈ {0,1} + sample weight).
  - **F8** — Assemble X (F2–F6) + data-quality gate.
  - **F11** — OOS evaluation (one-shot; PF · Sharpe · MDD · TIM · WR).
- **Model-facing Stages (single asset; consume the feature space; no feature ids):**
  - **F9** — Feature selection (SHAP-like importance + anti-overfitting → least-overfitting top-20).
  - **F10** — Calibration (Optuna tuning + probability calibration of an XGB on the top-20).
- **Artifact Stage (terminal bundle; no feature ids):**
  - **F12** — Artifact export (calibrated XGB `.b64` + top-20 + transformers + split/label config + OOS metrics + manifest).
- **Cross-asset / portfolio-facing Stages (operate across the 503 per-asset models; no feature ids):**
  - **F13** — Cross-asset entry table (503 binary enter/no-enter columns, 0/1).
  - **F14** — Cross-asset correlation → augmented model (correlated peers' entries appended to the top-20 → cross-asset XGB).

`stage` / `F0–F14` belong to **Plan B only**; `layer` / `L1–L10` belong to **Pipeline A only**. Never mix.

## Causality (the overriding rule)

Every feature at bar `t` is a **causal** function of bars `≤ t` back to F0. The only context that may
condition a feature is a regime computed from bars `≤ t` (drawn as a dashed edge in the viz). Fitted objects
(F4 regime cutoffs, F6 representations, F9 selection, F10 calibration, F14 cross-asset correlation + peer
selection) are fit on a **Train window only**. Full rules:
[00_leakage_contract_eng.md](00_leakage_contract_eng.md).

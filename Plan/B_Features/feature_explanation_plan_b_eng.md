# Feature explanation ("Plan B") — OHLCV → feature-stages F0–F5

> **Subordinate helper, not a build SOT.** This document explains *what the features are* and where
> they come from — the feature families and their derivation, organized as **feature-stages F0–F5**.
> It is **not** the build source of truth, and is **decoupled from any
> specific data store** (no materialization plan, no parquet store layout). The build SOT is
> **Pipeline A** ([`A_Layers/ENG/build_contract_eng.md`](../A_Layers/ENG/build_contract_eng.md)). The interactive
> feature DAG is [`B_Features/viz/feature_dag.html`](viz/feature_dag.html); the Pipeline-A pipeline viz is
> [`A_Layers/viz/main_data_flow.html`](../A_Layers/viz/main_data_flow.html).
>
> **Naming reserved.** This explanation never uses `layer`/`L#` — those belong to **Pipeline A**
> (`L1–L10`). It uses **feature-stages `F0–F5`** and feature ids
> **`f{stage}_{metric}[_{params}][_{timeframe}]`**.

## Conventions

### Feature-id grammar

```
f{stage}_{metric}[_{params}][_{timeframe}]
```

- `{stage}` — the feature-stage (`f0 … f5`) the metric belongs to.
- `{metric}` — the metric / abbreviation (`r` = close-to-close return, `mom` = momentum, `vol` =
  volatility, `tp` = typical price, …).
- `{params}` — optional window / lag tokens (`n` = rolling length, `k` = lag).
- `{timeframe}` — optional `1h` / `1d` / `mtf`.
- **`family` is a separate attribute, not an id token** — one of `price` · `returns` · `range`
  (range/vol) · `candle` (candle geometry) · `volume` · `meta` (synthesis / regime / embedding),
  shown by the legend colour in the DAG. Examples: `f1_r_cc` (family = returns), `f1_tp` (price),
  `f2_mom_n` (returns), `f3_vol_regime` (meta), `f4_atr` (range), `f5_pca_8` (meta).

### Guard conventions (illustrative, `ε = 1e-9`)

Divisions / logs use ε-guarded forms: `safe_div(a, b) = a / (b + ε)`; `safe_max(range, ε)`;
`safe_log_ratio(a, b) = NULL if a ≤ 0 or b ≤ 0 else ln(a/b)`. Rolling z-scores use `σ = 0 → 0` (an
explicit 0, never `NaN`/`Inf`). These are explanatory conventions for *understanding* the formulas —
not a store contract.

## Feature-stages (bottom → top)

**F0 — Raw OHLCV.** The five channels plus timestamp: `open, high, low, close, volume`, `ts`.
Everything above is a causal function of these.

**F1 — Atomic transforms** (point-wise on one candle / adjacent pair). Examples:
- `f1_candle_range` (range) = `high − low`
- `f1_candle_body_abs` (candle) = `abs(close − open)`; `f1_candle_body_signed` = `close − open`
- `f1_lower_wick` / `f1_upper_wick` (candle) = `min(open,close) − low` / `high − max(open,close)`
- `f1_volume_dollar` (volume) = `close · volume`; `f1_volume_log` = `ln(1 + volume)`
- `f1_r_cc` (returns) = `safe_log_ratio(close, prev_close)`; `f1_gap_open` = `safe_div(open − prev_close, prev_close)`
- `f1_body_pct` (candle) = `safe_div(body_abs, close)`; `f1_close_position` = `safe_div(close − low, safe_max(range, ε))`

**F2 — Rolling / temporal** (lags + rolling windows of length `n`; typical `n ∈ {5,10,20,50}` on 1h,
`{20,200}` on 1d — illustrative, not store-pinned). Examples:
- `f2_mom_n` (returns) = rolling sum of `f1_r_cc`
- `f2_vol_return_std_n` (range) = rolling std of `f1_r_cc`
- `f2_volume_z_n` (volume) = `(f1_volume_log − mean_n) / std_n` (`σ = 0 → 0`)
- `f2_path_drawdown_n` (range) = `safe_div(close, rolling_high_n) − 1`

**F3 — MTF / regime / context** (resample 1h → 1d, recompute F1/F2 on the coarser grid, bucketed
regimes + session phase). Examples:
- `f3_vol_regime` (meta) = volatility bucket {low, mid, high} from a rolling-vol metric (quantile cutoffs, e.g. `[0.33, 0.66]`)
- `f3_volume_regime` (meta) = volume bucket from `f2_volume_z` (thresholds, e.g. `[−1, 1]`)
- `f3_session_open_phase` / `f3_session_midday_phase` / `f3_session_close_phase` (meta) from minute-of-session

**F4 — Classical indicators** (compressed functions of F1–F3; textbook formulas, ε-guarded):
- `f4_rsi_14` (Wilder); `f4_macd_hist_12_26_9`
- `f4_atr` (range) = `mean_n(TR)`, `TR = max(high − low, |high − prev_close|, |low − prev_close|)`, `n = 14`
- `f4_obv`, `f4_adl`, `f4_stoch_k_14`, `f4_adx_14`, `f4_mfi_14`, `f4_vwap_distance`

**F5 — Research representations** (stack F1–F4 → standardize → learn/apply a representation):
- `f5_pca_8` (PCA, 8 components); `f5_dwt_db4_l3` (wavelet energies); `f5_ae_8` (autoencoder code); `f5_seq_lstm32` (sequence embedding)
- Standardization and every fitted object are fit on a **Train window only** (no leakage); the
  transform API is `transform(X) → features`; all windows look **backward only** (zero look-ahead).

## Edges = lineage

Every feature node is a function of its inputs back to **F0**; "regime context" edges are drawn
dashed in `viz/feature_dag.html`.

## Relationship to Pipeline A

Pipeline A's **L7** uses a **small, hand-crafted set** of trend-line-geometry features — the **8
transformer columns** (7 in `FEATURE_MANIFEST` + `closed_through_line` as an audit column), specified
in [`build_contract_eng.md`](../A_Layers/ENG/build_contract_eng.md) §4. That is **not** this general feature library.
This document explains the broader OHLCV feature space for understanding only; it is **not** a build
dependency of Pipeline A.

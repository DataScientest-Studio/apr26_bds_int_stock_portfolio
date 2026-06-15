# Pipeline B — OHLCV → L5 feature build spec (English)

> **Scope of this document.** Pipeline B is the *general feature-engineering pipeline over raw OHLCV*, layered **L0 → L5**. It is a **different** pipeline from Pipeline A (the S&P 500 trading-strategy pipeline, layered **L1 → L10**). The `L#` numbers do **not** correspond between the two — never conflate them. Native bar = **1h** (the `qc_raw_ohlcv_data_sp500_alpaca_transforms` 1h store), so the only resample is **1h → 1d** (finer bars such as 5m/15m are below the native bar and do not exist here).
>
> **What is certified.** Certified scope = **L0–L5**. **PART 1 (L0–L3)** documents the **real `qc-transforms`** code (`structure/src/.../transform/{l1,l2,l3}/_010_features.py`, driven by `structure/config/materialization_plan_1h_day.json` and `structure/config/project.toml`). **PART 2 (L4 + L5)** is a **reference design (one valid realization)** — also in the certified L0–L5 scope; the formulas, parameters and APIs are concrete and build-ready. (The current `qc-transforms` source materializes L0–L3 only; PART 2 is the certified reference spec for L4/L5, not yet materialized upstream.)

---

## 0. Conventions used throughout

### 0.1 Feature-id naming convention

```
l{layer}_{metric}[_{params}][_{timeframe}]
```

- `{layer}` — the **logical** layer the metric belongs to (`l1`, `l2`, `l3`, …). In the real store the physical files are tagged `L3` (the MTF profile recomputes L1/L2 on the resampled grid), but the **logical** layer is the second token: `l3_l1_*` is logically L1, `l3_l2_*` is logically L2, `l3_resample_*` is a raw passthrough. This document classifies by the **logical** layer.
- `{metric}` — the metric / abbreviation: e.g. `r`/`return` = close-to-close return, `mom`/`momentum` = momentum, `vol` = volatility, `tp` = typical price.
- `{params}` — optional window/lag tokens: `n` (rolling length), `k` (lag).
- `{timeframe}` — optional `1h` / `1d` / `mtf` / `session`.
- **`family` is a SEPARATE attribute**, *not* an id segment. It is carried on each node's `family:` field and takes one of: `price` · `returns` · `range` (range/vol) · `candle` (candle geometry) · `volume` · `meta` (synthesis / regime / embedding). Examples: `l1_r_cc` (family = returns), `l1_tp` (family = price), `l2_mom_n` (family = returns), `l3_vol_regime` (family = meta).

### 0.2 Real parameter grids (FIXED — from `materialization_plan_1h_day.json` + `project.toml`)

| Parameter | Value | Source |
|---|---|---|
| Native bar | `1h` | store is 1h-native |
| Resample | `1h → 1d` only | `dag_native_bar` substitution `root_*_1m → 1h` |
| 1h rolling windows `n` | `{5, 10, 20, 50}` | `[l2].windows_1h` |
| 1d rolling windows `n` | `{20, 200}` | `[l2].windows_1d` |
| Lag `k` | `1` | `l3_l1_lag_close_1_*` |
| Regime quantiles | `[0.33, 0.66]` | `[l3].regime_quantiles` |
| Volume-z regime thresholds | `[−1.0, 1.0]` | `[l3].volume_regime_thresholds` |
| Session open-minute cutoff | `60` (minutes since 09:30 ET open) | `[l3].session_open_minutes` |
| Session close-minute cutoff | `300` (minutes since 09:30 ET open) | `[l3].session_close_minutes` |
| Max history (1d) | `200` bars | `max_history_bars_per_timeframe.1d` |
| Max history (1h) | `50` bars | `max_history_bars_per_timeframe.1h` |

### 0.3 ε and the guard macros (FIXED)

All divisions/logs in Pipeline B route through the DuckDB macros defined in `schema.macros_ddl(eps)`. **Canonical project ε = `1e-9`** (the `params.json` / project value used across the SOT). *(Reference note: the `qc-transforms` `project.toml` currently ships `eps = 1e-8`; the SOT canonical guard value is `ε = 1e-9`. Treat any `eps` arithmetic below with `ε = 1e-9` for the certified spec; the only effect is the exact magnitude of the additive denominator floor.)*

```
safe_div(a, b)        = a / (b + ε)                              -- denominator floor; den=0 → a/ε (finite)
safe_max(a, b)        = greatest(a, b)                           -- used as safe_max(range, ε) → never below ε
safe_sign(x)          = sign(x)                                  -- {−1, 0, +1}
safe_log_ratio(a, b)  = (a IS NULL OR b IS NULL OR a≤0 OR b≤0) ? NULL : ln(a/b)   -- guards log of non-positive
```

- **Guard summary:** every ratio uses `safe_div` (additive `+ε` floor, so a zero denominator yields a finite value, never `Inf`/`NaN`); every log-of-ratio uses `safe_log_ratio` (returns `NULL` rather than `−Inf`/`NaN` for non-positive inputs); every "divide by candle range" first floors the range with `safe_max(range, ε)`.
- **`ln(1 + x)`** (volume / dollar-volume) is safe for `x ≥ 0` (volume ≥ 0 by QC-06), so no extra guard is needed.

### 0.4 Keys, metadata, materialization layout (FIXED)

- Row key: `(symbol, ts)`. Metadata columns appended to every layer parquet: `transform_version`, `built_at_utc`.
- Materialization = **one parquet file per logical layer per ticker**, joined by `(symbol, ts)`: `data/parquet/<TICKER>/{l1,l2,l3}.parquet`, `zstd` compression. The model "feed" is a JOIN of selected columns across layer files.
- Column counts (this profile, from the plan): ROOT/RESAMPLE = 6, L1 = 21, L2 = 38, L3 = 9; `materialize_count = 74`; `feed_columns_count = 34`.

---

# PART 1 — CERTIFIED v1 (L0 → L3, the REAL `qc-transforms`)

This part mirrors the **real `qc-transforms`** code; the formulas state **certified SOT behavior** (which may refine the source — e.g. the z-score zero guard below). Source files for provenance: `transform/l1/_010_features.py`, `transform/l2/_010_features.py`, `transform/l3/_010_features.py`, and the column lists from `schema.py`.

## L0 — Raw OHLCV roots

The roots are the five OHLCV channels + the timestamp. In the 1m-native DAG spec they are `root_{field}_1m`; under the **1h native-bar substitution** they read the 1h store directly, so `l3_resample_*_1h ≡ raw 1h OHLCV` and `l3_resample_close_1d` is the daily resample.

| Root | Meaning |
|---|---|
| `root_open_1m` → `open` | candle open (USD, from `VIEW ohlcv_1h`) |
| `root_high_1m` → `high` | candle high |
| `root_low_1m` → `low` | candle low |
| `root_close_1m` → `close` | candle close |
| `root_volume_1m` → `volume` | candle volume (≥ 0 by QC-06) |
| `root_timestamp` → `ts` | ET-naive timestamp (`America/New_York`); session features derive from it |

- **Input contract.** The roots come from Pipeline A's analytical store via the `ohlcv_1h` USD `VIEW` (price_view `raw_usd_view`); the 11 quality gates `QC-01…QC-11` already hold on this input (prices > 0, volume ≥ 0, no duplicate `(symbol, ts)`, ts strictly increasing per symbol). Pipeline B does **not** re-validate; it consumes the gated store.
- **Resample passthrough columns** (`family = resample`, carried in the L1 parquet): `l3_resample_{open,high,low,close,volume}_1h`, `l3_resample_close_1d`. The 1d close is `arg_max(close, ts)` per `(symbol, ts::DATE)` (last close of the day).

## L1 — Atomic transforms (21 features; point-wise on one candle / adjacent pair)

Computed per `(symbol, ts)` in `build_l1_sql`. All 21 ids are in `schema.L1_FEATURES`. Lag `k = 1` (`lag(...) OVER (PARTITION BY symbol ORDER BY ts)` for 1h; over the per-day series for 1d).

| Feature id | family | Formula (certified SOT) | Guard |
|---|---|---|---|
| `l3_l1_lag_close_1_1h` | price | `lag(close, 1)` over `(symbol, ts)` | — (NULL on first row) |
| `l3_l1_lag_close_1_1d` | price | `lag(close_1d, 1)` over per-day series | — (NULL on first day) |
| `l3_l1_candle_range_1h` | range | `high − low` | — (≥ 0; QC-01 `high ≥ low`) |
| `l3_l1_candle_body_abs_1h` | candle | `abs(close − open)` | — |
| `l3_l1_candle_body_signed_1h` | candle | `close − open` | — |
| `l3_l1_candle_lower_wick_1h` | candle | `least(open, close) − low` | — |
| `l3_l1_candle_upper_wick_1h` | candle | `high − greatest(open, close)` | — |
| `l3_l1_volume_dollar_1h` | volume | `close · volume` | — |
| `l3_l1_volume_log_1h` | volume | `ln(1 + volume)` | safe (`volume ≥ 0`) |
| `l3_l1_gap_open_1h` | returns | `safe_div(open − lag_close_1_1h, lag_close_1_1h)` | `safe_div` (`den=0 → /ε`) |
| `l3_l1_return_log_cc_1h` | returns | `safe_log_ratio(close, lag_close_1_1h)` | `safe_log_ratio` (non-pos → NULL) |
| `l3_l1_return_log_cc_1d` | returns | `safe_log_ratio(close_1d, lag_close_1_1d)` | `safe_log_ratio` |
| `l3_l1_candle_safe_range_1h` | range | `safe_max(candle_range_1h, ε)` | floor at ε |
| `l3_l1_price_range_pct_1h` | range | `safe_div(candle_range_1h, close)` | `safe_div` |
| `l3_l1_candle_body_pct_1h` | candle | `safe_div(candle_body_abs_1h, close)` | `safe_div` |
| `l3_l1_candle_body_direction_1h` | candle | `safe_sign(candle_body_signed_1h)` → {−1,0,+1} | — |
| `l3_l1_micro_rejection_balance_1h` | candle | `safe_div(lower_wick − upper_wick, candle_body_abs_1h)` | `safe_div` (`den=0 → /ε`) |
| `l3_l1_volume_dollar_log_1h` | volume | `ln(1 + volume_dollar_1h)` | safe (`≥ 0`) |
| `l3_l1_candle_close_position_1h` | candle | `safe_div(close − low, candle_safe_range_1h)` | `safe_div` over ε-floored range |
| `l3_l1_candle_wick_imbalance_1h` | candle | `safe_div(lower_wick − upper_wick, candle_safe_range_1h)` | `safe_div` over ε-floored range |
| `l3_l1_volume_directional_pressure_1h` | volume | `volume · candle_body_direction_1h` | — |

## L2 — Rolling / temporal (38 features; gated rolling windows)

Computed per ticker in `build_l2_sql`. **Window gating (warm-up guard):** every rolling aggregate is wrapped so it is `NULL` until the window has exactly `n` rows:

```
_gated(agg, col, n) =
  CASE WHEN count(*) OVER (ORDER BY ts ROWS BETWEEN n-1 PRECEDING AND CURRENT ROW) = n
       THEN agg(col) OVER (same window) END
```

This is the **warm-up** rule for Pipeline B: a feature emits no value until its full lookback is present (1h features over the 1h grid; 1d features over the distinct-date series, broadcast back to 1h rows by date). Sample std uses `stddev_samp` (n−1 denominator).

**Base rolling, 1h grid** (windows `n ∈ {5,10,20,50}` as applicable):

| Feature id | family | agg | input | windows |
|---|---|---|---|---|
| `l3_l2_path_rolling_high_{10,20}_1h` | range | `max` | `l3_resample_close_1h` | 10, 20 |
| `l3_l2_path_rolling_high_price_10_1h` | range | `max` | `l3_resample_high_1h` | 10 |
| `l3_l2_path_rolling_low_price_10_1h` | range | `min` | `l3_resample_low_1h` | 10 |
| `l3_l2_volume_mean_{10,20}_1h` | volume | `avg` | `l3_l1_volume_log_1h` | 10, 20 |
| `l3_l2_volume_std_{10,20}_1h` | volume | `stddev_samp` | `l3_l1_volume_log_1h` | 10, 20 |
| `l3_l2_momentum_sum_{5,10,20,50}_1h` | returns | `sum` | `l3_l1_return_log_cc_1h` | 5,10,20,50 |
| `l3_l2_vol_return_std_{10,20}_1h` | range | `stddev_samp` | `l3_l1_return_log_cc_1h` | 10, 20 |
| `l3_l2_vol_range_mean_{10,20}_1h` | range | `avg` | `l3_l1_price_range_pct_1h` | 10, 20 |
| `l3_l2_vol_range_std_{10,20}_1h` | range | `stddev_samp` | `l3_l1_price_range_pct_1h` | 10, 20 |
| `l3_l2_candle_body_mean_20_1h` | candle | `avg` | `l3_l1_candle_body_pct_1h` | 20 |
| `l3_l2_candle_body_std_20_1h` | candle | `stddev_samp` | `l3_l1_candle_body_pct_1h` | 20 |
| `l3_l2_dollar_volume_mean_20_1h` | volume | `avg` | `l3_l1_volume_dollar_log_1h` | 20 |
| `l3_l2_dollar_volume_std_20_1h` | volume | `stddev_samp` | `l3_l1_volume_dollar_log_1h` | 20 |
| `l3_l2_volume_pressure_sum_20_1h` | volume | `sum` | `l3_l1_volume_directional_pressure_1h` | 20 |

**Base rolling, 1d grid** (over distinct-date series of `l3_l1_return_log_cc_1d`):

| Feature id | family | agg | windows |
|---|---|---|---|
| `l3_l2_momentum_sum_{20,200}_1d` | returns | `sum` | 20, 200 |
| `l3_l2_vol_return_std_20_1d` | range | `stddev_samp` | 20 |

**Derived (from base rolling + L1):**

| Feature id | family | Formula | Guard |
|---|---|---|---|
| `l3_l2_path_drawdown_{10,20}_1h` | range | `safe_div(close, path_rolling_high_n_1h) − 1` | `safe_div` |
| `l3_l2_path_breakout_high_10_1h` | range | `safe_div(close, path_rolling_high_price_10_1h) − 1` | `safe_div` |
| `l3_l2_path_breakout_low_10_1h` | range | `safe_div(close, path_rolling_low_price_10_1h) − 1` | `safe_div` |
| `l3_l2_volume_z_{10,20}_1h` | volume | `(volume_log − volume_mean_n) / volume_std_n` | `σ=0 → 0` |
| `l3_l2_ratio_momentum_5_20_1h` | returns | `safe_div(momentum_sum_5_1h, abs(momentum_sum_20_1h))` | `safe_div` |
| `l3_l2_ratio_momentum_10_50_1h` | returns | `safe_div(momentum_sum_10_1h, abs(momentum_sum_50_1h))` | `safe_div` |
| `l3_l2_vol_range_z_{10,20}_1h` | range | `(price_range_pct − vol_range_mean_n) / vol_range_std_n` | `σ=0 → 0` |
| `l3_l2_candle_body_z_20_1h` | candle | `(candle_body_pct − candle_body_mean_20) / candle_body_std_20` | `σ=0 → 0` |
| `l3_l2_dollar_volume_z_20_1h` | volume | `(volume_dollar_log − dollar_volume_mean_20) / dollar_volume_std_20` | `σ=0 → 0` |

> **Guard note on z-scores.** Every z-score divides by a rolling std. When the std is 0 (a flat window) the z-score is defined as **0** (neutral): `z = (x−μ)/σ` if `σ>0` else `0`. This matches the viz and Pipeline A's `std=0 → 0` guard. Never `NaN`/`Inf`; the result is an explicit `0`, **not** an ε-floor, for z-scores.

## L3 — MTF / regime / session (9 features)

Computed per ticker in `build_l3_sql`. Inputs are four L2 columns + `ts`. Two bucketers:

```
_bucket_q(col, q33, q66)   = col IS NULL ? NULL : (col < q33 ? 0 : (col < q66 ? 1 : 2))
_bucket_thr(col, lo, hi)   = col IS NULL ? NULL : (col < lo  ? 0 : (col <= hi ? 1 : 2))
```

Quantile cutoffs `q33`, `q66` are **per-symbol over the symbol's full history** (`quantile_cont(col, 0.33|0.66) OVER ()`) → a documented mild look-ahead; the volume regime uses **fixed** z-thresholds `[−1.0, 1.0]`.

**Session features** (`family = session`, timeframe `session`) — `minute_of_day = datediff('minute', day_start + 9h30m, ts)` (minutes since the 09:30 ET open; 1h-adapted phase cutoffs `open_min=60`, `close_min=300`):

| Feature id | type | Definition |
|---|---|---|
| `l3_session_day_of_week` | category | `dayofweek(ts)` |
| `l3_session_minute_of_day` | int | minutes since 09:30 ET |
| `l3_session_open_phase` | bool | `minute_of_day < 60 → 1 else 0` |
| `l3_session_midday_phase` | bool | `60 ≤ minute_of_day < 300 → 1 else 0` |
| `l3_session_close_phase` | bool | `minute_of_day ≥ 300 → 1 else 0` |

**Regime features** (`family = regime` / `meta`):

| Feature id | tf | Bucketer | Input | Cutoffs |
|---|---|---|---|---|
| `l3_regime_volatility_low_mid_high_1h` | 1h | `_bucket_q` | `l3_l2_vol_return_std_20_1h` | per-symbol [0.33, 0.66] |
| `l3_regime_volume_low_mid_high_1h` | 1h | `_bucket_thr` | `l3_l2_volume_z_20_1h` | fixed [−1.0, 1.0] |
| `l3_regime_trend_flat_directional_1d` | 1d | `_bucket_q` | `abs(l3_l2_momentum_sum_200_1d)` | per-symbol [0.33, 0.66] |
| `l3_regime_volatility_low_mid_high_1d` | 1d | `_bucket_q` | `l3_l2_vol_return_std_20_1d` | per-symbol [0.33, 0.66] |

- **Bucket semantics:** `0 = low`, `1 = mid`, `2 = high` (for volatility/volume); for trend, `0 = flat … 2 = directional` (high `|momentum|`). `NULL` propagates (a row with no underlying value → `NULL` regime).
- **Guard:** the `NULL` short-circuit in both bucketers means no comparison is ever made against a missing value; there is no division here.

---

# PART 2 — L4 / L5 (reference design — one valid realization; in the certified L0–L5 scope)

> The whole of PART 2 is a **reference design (one valid realization)** of L4/L5 — **in the certified L0–L5 scope**. The formulas, parameters and APIs below are concrete and build-ready (one valid realization). The current `qc-transforms` source materializes L0–L3 only; PART 2 is the certified spec for L4/L5, not yet materialized upstream.

## L4 — Classical indicators (reference design — certified L0–L5)

Each indicator is given with its textbook formula **with guards** (ε = 1e-9, `max(ε, …)` floors). `Wilder` smoothing of a series `x` with period `n`: `S_t = S_{t−1} + (x_t − S_{t−1})/n`, seeded by the first `n`-mean. `TP` = typical price `(high + low + close)/3`. `TR` (true range) = `max(high − low, |high − close_{t−1}|, |low − close_{t−1}|)`.

| Indicator | id (reference) | Formula (with guards) |
|---|---|---|
| **RSI** (Wilder) | `l4_rsi_14_1h` | `RS = Wilder(gain, n) / max(ε, Wilder(loss, n))`; `RSI = 100 − 100/(1 + RS)`. `gain = max(0, Δclose)`, `loss = max(0, −Δclose)`. `n = 14`. |
| **MACD** | `l4_macd_hist_12_26_9_1h` | `MACD = EMA_12(close) − EMA_26(close)`; `signal = EMA_9(MACD)`; `hist = MACD − signal`. |
| **ATR** | `l4_atr` | canonical **`l4_atr = mean_n(TR)`** (matches viz/glossary), `n = W_ATR = 14`; pct form `ATR_pct = ATR_14 / max(ε, close)`. *(ADX below may use an internal Wilder-smoothed TR for ±DI; that internal series is **not** the canonical `l4_atr`.)* |
| **OBV** | `l4_obv_1h` | `OBV_t = OBV_{t−1} + sign(close_t − close_{t−1}) · volume_t`, `OBV_0 = 0`. |
| **ADL** (accumulation/distribution line) | `l4_adl_1h` | `MFM = ((close − low) − (high − close)) / max(ε, high − low)`; `MFV = MFM · volume`; `ADL_t = ADL_{t−1} + MFV_t`. |
| **Stochastic %K** | `l4_stoch_k_14_1h` | `%K = 100 · (close − min_low_n) / max(ε, max_high_n − min_low_n)`, `n = 14`; `%D = SMA_3(%K)`. |
| **ADX** (corrected) | `l4_adx_14_1h` | `+DI = 100 · Wilder(+DM, n) / max(ε, ATR_n)`; `−DI = 100 · Wilder(−DM, n) / max(ε, ATR_n)`; **`DX = 100 · |+DI − −DI| / max(ε, +DI + −DI)`**; `ADX = Wilder(DX, n)`, `n = 14`. `+DM/−DM` per Wilder directional-movement rules. |
| **MFI** | `l4_mfi_14_1h` | `TP = (high+low+close)/3`; `MF = TP · volume`; split into positive/negative MF by `Δ TP` sign; `MR = ΣposMF_n / max(ε, ΣnegMF_n)`; `MFI = 100 − 100/(1 + MR)`, `n = 14`. |
| **VWAP** | `l4_vwap_distance_1h` | `VWAP = Σ(TP·V) / max(ε, ΣV)` over the chosen window/session; reported as distance `safe_div(close − VWAP, VWAP)`. |

- **Global L4 guard rule:** every quotient denominator is floored with `max(ε, …)`; every recursive series (OBV, ADL) is seeded at `0`; Wilder seeds use the first available `n`-mean and emit `NULL` before warm-up (`n` bars), consistent with L2 window gating.

## L5 — Research representations (reference design — certified L0–L5)

L5 stacks the L0–L4 feature matrix, standardizes it, and learns/applies a representation. **All L5 methods share these contract rules (FIXED):**

- **Inputs:** `X_raw` = the assembled, JOINed Pipeline-B feature matrix (L1–L4 columns) per `(symbol, ts)`, after dropping warm-up rows that are still `NULL`.
- **Fit scope = Train only.** Every fitted object (scaler stats, PCA components, AE/LSTM weights) is fit **exclusively on the Train window** — no warm-up, no OOS — exactly mirroring Pipeline A's L5 split discipline. This is the **no-leakage** invariant: fitting on Train, transforming everywhere.
- **Standardization:** fit a `StandardScaler` on `X_raw` (Train-only mean/std); persist `mean_`, `scale_`; `transform = (X − mean_)/max(ε, scale_)` (guard against a zero-variance column).
- **Transform API:** `transform(X) -> features` (deterministic; pure projection/encode, no re-fit).
- **Persist format:** as specified per method below; each artifact carries `schema_version`, `built_at_utc`, `inputs_hash`.

| Method | id (reference) | Library / config | Fit (Train-only) | Persist | `transform(X)` |
|---|---|---|---|---|---|
| **PCA** | `l5_pca_8` | `sklearn.decomposition.PCA`, `n_components = 8`, on standardized `X_raw` | fit components on Train | `components_`, `mean_`, `explained_variance_` via `joblib` | project `X` onto the 8 components |
| **DWT** | `l5_dwt_db4_l3` | `pywt.wavedec`, wavelet `db4`, `level = 3`, **causal** rolling window `W = 64` | (stateless transform; no learned weights) | wavelet name + level + `W` (config only) | per-level **energy** (Σ of squared coeffs per level) over each causal window |
| **Autoencoder** | `l5_ae_8` | MLP encoder dims `[64, 32, 8]`, ReLU, MSE loss, Adam, **50 epochs** | fit on Train (`X_raw` standardized) | `torch` `state_dict` | run the **encoder** → 8-dim code |
| **Sequence** | `l5_seq_lstm32` | LSTM `hidden = 32`, `1` layer, input window = **24 bars** of `X_raw` | fit on Train | `torch` `state_dict` | last hidden state `h_t ∈ R^32` for each row's trailing 24-bar window |

- **Causality (DWT / Sequence):** the rolling/sequence windows look **backward only** (`[t−W+1, t]` / last 24 bars ending at `t`) — zero look-ahead, consistent with the cross-cutting causality rule.
- **Guards:** standardization denominator `max(ε, scale_)`; DWT energy is a sum of squares (no division); AE/LSTM forward passes have no division by data.

---

## Appendix A — L8-style validation thresholds (FIXED; reference for the Pipeline-B quality gate)

These are the dashboard thresholds and the `summary.json` contract used by the quality gate that guards Pipeline B's outputs (the L8 analog: it **measures and reports, fixes nothing**; any **FAIL blocks the next stage**).

| Check | Level rule |
|---|---|
| in-session gaps | `> 0` → **FAIL** |
| filled gaps | `> 0` → **FAIL** (we fill nothing; the counter proves it) |
| duplicates `(symbol, ts)` | `> 0` → **FAIL** |
| prices ≤ 0 | `> 0` → **FAIL** |
| NaN/Inf in Output B (undocumented) | `> 0` → **FAIL** |
| parity (zip → DuckDB → parquet → Output B) | any mismatch → **FAIL** |
| `volume = 0` bars | `> 0.5%` → **WARN**, `> 2%` → **FAIL** |
| zero-range bars (`high == low`) | `> 0.5%` → **WARN**, `> 2%` → **FAIL** |
| DET-09 rejection rate | `> 20%` → **WARN** (diagnostic, **never FAIL**) |

**Aggregation:** any **FAIL** → dashboard **FAIL** → next stage blocked; **WARN** with no FAIL → proceed.

Quality gating for this materialization uses the **canonical L8 gate** — there is exactly one frozen `summary.json` schema (`schema_version "1.0"`) and all thresholds live in `config/params.json` (`l8`). See [quality_gate_spec_eng.md](quality_gate_spec_eng.md); do not redefine the schema here.

## Appendix B — Detector reference algo & TOUCH_TOL (cross-link to Pipeline A §3)

Pipeline B feeds Pipeline A's L6 detector. The detector is a **reference impl of the §3 output contract** (one valid realization) and the following constants are FIXED reference values:

- **`TOUCH_TOL = 0.25`** (units: ×`ATR(t)`, ATR = Wilder, `W_ATR=14`). A swing point touches a line iff `|price − line(t)| ≤ TOUCH_TOL · ATR(t)`.
- **Causal pivots** of strength `k = 3`: a local extremum over `[i−3, i+3]`, confirmed at `i+3` (zero look-ahead).
- **`L_trend`** = least-squares line through the `≥ MIN_TOUCHES (=2)` most-recent qualifying swing highs (long) / lows (short). **`L_opp`** = least-squares line through `≥ 2` opposite swings in the same window; else **reject → DET-09 (missing `L_opp`)**.
- **`direction`** `+1` = break **up** through resistance; `−1` = break **down** through support.
- **`entry_candle t0`** = first close with `sign·(close[t] − L_trend(t)) > 0` after line validation.
- **Dedup / cooldown:** after an entry, suppress new entries on the same line for `COOLDOWN = H (=24)` bars.
- **DET-09 reject + count:** `R0 ≤ 0`, `ATR(t0) ≤ 0`, or missing `L_opp` → rejected and counted in the audit (never silently dropped). DET-09 rejection rate is WARN-only (`> 20%`), never FAIL.

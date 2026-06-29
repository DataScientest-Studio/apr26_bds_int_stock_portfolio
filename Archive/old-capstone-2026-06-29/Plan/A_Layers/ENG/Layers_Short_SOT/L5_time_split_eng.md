# L5 · Time split (SOT)

Time hygiene: three disjoint windows per asset with hard buffer zones at the boundaries. Boundary dates are
parameters in `config/parameters.json` → `splits` (defaults for this project's universe); not hardcode.

- We split each ticker's series into three disjoint windows (indices on one continuous series).
- **WARM-UP** window: `2016-01-04 → 2016-10-14`.
  - rolls in the rolling windows: `max(W_ATR=14, W_VOL=20) = 20` candles
  - no training and no detection; rows with NULL features are dropped
- **TRAIN** window: `2016-10-17 → 2023-12-29`.
  - the only window touched repeatedly: detection, features, Optuna (CV), model training
- **OOS** window: `2024-01-02 → 2026-05-29`, frozen.
  - one test run; zero tuning after looking at the results
- **Purge** (`PURGE_CANDLES = H = 24`): a training row whose label window `[t0, t0+H]` crosses a window boundary is **removed** (the label must not reach into OOS).
  - the purge operates on **setups**, not on candles
- **Embargo** (`EMBARGO_SESSIONS = 5` ≈ 35 candles): after the Train→OOS boundary, skip an extra buffer.
  - covers the rolling-feature autocorrelation: `5 sessions ≈ 35 candles ≥` max feature lookback (20 candles)
- Indices, `H` and the purge are computed by integer candle position, not by timestamp.
- **Purged walk-forward CV** (`CV_SCHEME`) separates the folds inside Train; folds are also separated by purge + embargo.
- The windows are indices on one continuous series, not separate parquet files (a fixed design decision).
  - reason: the rolling windows (20 candles) and the label windows `[t0, t0+24]` cross the window boundaries
- Boundary assertion (CI): no `[t0, t0+H]` window crosses a window boundary.
- Parameter values: see [00_parameters_eng.md](00_parameters_eng.md).

# L5 · Time split (summary)

- We split each ticker's series into three windows (dates = parameters, spec §5a).
- WARM-UP window: `2016-01-04 → 2016-10-14`.
  - used to roll-in the rolling windows: max(W_ATR=14, W_VOL=20) = 20 candles
  - in warm-up there is no training and no detection
- TRAIN window: `2016-10-17 → 2023-12-29`.
  - the only window touched repeatedly (detection, features, Optuna, training)
- OOS window: `2024-01-02 → 2026-05-29`, frozen.
  - one test run
  - zero tuning after looking at the results
- At the window boundaries a purge runs.
  - a row whose label window `[t0, t0+24]` crosses a boundary is removed
- After the Train→OOS boundary an embargo of ≈ 5 sessions (~35 candles) runs.
  - the embargo fully covers the max feature lookback (20 candles)
- Indices, `H` and the purge are computed by integer candle position, not by timestamp.
- The same rules separate the CV folds inside Train.
- The windows are indices on one continuous series, not separate parquet files (register C-71).
  - reason: the rolling windows (20 candles) and the label windows `[t0, t0+24]` cross the window boundaries

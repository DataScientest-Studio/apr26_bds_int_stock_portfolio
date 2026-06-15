# L10 · OOS test (summary)

- Before the test, the hash of each strategy file goes into the hash register.
  - from that moment the strategy files are immutable
- We run a single run over the OOS window `2024-01-02 → 2026-05-29`.
  - the detector generates setups
  - the strategy computes the 7 X features at `t0`
  - the model returns `p = model(x)`
  - entry rule: `p ≥ 0.60 → ENTRY`
  - exits per TB: fixed TP from R0 · SL = moving `L_opp(t)` · time barrier 24 candles
- Result: a matrix `503 assets × {PF, Sharpe, MDD%, TIM%, WR%, trades}`.
  - the matrix is joined by a distribution report across the universe (we look for a distribution, not a single star)
  - storage: parquet/CSV + run manifest
- The OOS result never goes back into tuning (one-shot).

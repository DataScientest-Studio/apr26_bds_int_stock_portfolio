# L11 · OOS test (SOT)

The final verdict: a one-time run of the frozen strategies on the untouched OOS window and a results matrix.
Input = the frozen `strategy_<TICKER>.py` artifacts from [L10](L10_xgboost_strategy_eng.md).

- Before the test, the hash of each strategy file goes into the hash register.
  - from that moment the strategy files are immutable
- We run a single run over the OOS window `2024-01-02 → 2026-05-29`.
  - the detector generates setups
  - the strategy assembles the 8 X manifest (7 geometric features at `t0` + `direction` from the setup)
  - the model returns `p = model(x)`
  - entry rule: `p ≥ 0.60 → ENTRY`
  - exits per triple barrier: fixed TP from `R0` · SL = moving `L_opp(t)` · time barrier 24 candles
- Result: a matrix `<!--na:universe_size-->503<!--/na--> assets × {PF · Sharpe · MDD% · TIM% · WR% · trades}`.
  - **OOS metrics canonical order: PF · Sharpe · MDD · TIM · WR** (= `METRICS`)
  - PF (profit factor) = gross profits / gross losses
  - Sharpe — informational; treat with caution at low TIM
  - MDD % — maximum drawdown
  - TIM % — time in market (% of candles with an open position)
  - WR % — win-rate (% of winning trades)
  - trades — number of trades (the denominator of significance)
- The matrix is joined by a distribution report across the universe (distributions, top/bottom assets, the share with PF > 1) — we look for a **distribution**, not a single star.
- Storage: parquet/CSV + run manifest.
- **One-shot:** the OOS result never goes back into tuning (the next iteration = a new cycle from Train with a later OOS).

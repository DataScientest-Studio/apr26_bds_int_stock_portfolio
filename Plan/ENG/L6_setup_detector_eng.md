# L6 · Trend-line setup detector (summary)

- Input: files `parquet/<TICKER>/ohlcv.parquet` in the Train window from [L5](L5_time_split_eng.md).
- The detector returns setup objects (contract spec §3).
  - direction: `direction ±1`
  - lines: `L_trend(t)` and `L_opp(t)` as functions of the candle index
  - touchpoints: touches strictly before `t0` (minimum: MIN_TOUCHES=2)
  - `t0`: the first close that breaks through `L_trend`
  - risk: `R0 = |close[t0] − L_opp(t0)|`
  - a setup with `R0 ≤ 0` or `ATR(t0) ≤ 0` is rejected and counted in the audit (DET-09)
- ATR = Wilder(14), window up to and including `t`; it serves only as a feature normalizer (L7).
- Output: setup objects → features X + label Y ([L7](L7_features_x_label_y_eng.md)).

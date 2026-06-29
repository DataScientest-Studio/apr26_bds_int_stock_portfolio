# F2 · Atomic transforms (SOT)

Point-wise features on one bar or an adjacent pair (`t`, `t−1`). Guards (`safe_div`, `safe_max`,
`safe_log_ratio`, `ε`) are owned by [00_guards_and_windows_eng.md](00_guards_and_windows_eng.md); families by
[00_families_eng.md](00_families_eng.md).

| Feature id | Family | Formula |
|---|---|---|
| `f2_candle_range` | range | `high − low` |
| `f2_candle_body_abs` | candle | `abs(close − open)` |
| `f2_candle_body_signed` | candle | `close − open` |
| `f2_lower_wick` | candle | `min(open, close) − low` |
| `f2_upper_wick` | candle | `high − max(open, close)` |
| `f2_body_pct` | candle | `safe_div(f2_candle_body_abs, close)` |
| `f2_close_position` | candle | `safe_div(close − low, safe_max(f2_candle_range, ε))` |
| `f2_r_cc` | returns | `safe_log_ratio(close, prev_close)` (close-to-close log return) |
| `f2_gap_open` | returns | `safe_div(open − prev_close, prev_close)` |
| `f2_tp` | price | `(high + low + close) / 3` (typical price) |
| `f2_ohlc4` | price | `(open + high + low + close) / 4` |
| `f2_volume_dollar` | volume | `close · volume` |
| `f2_volume_log` | volume | `ln(1 + volume)` |

- All F2 features use only bar `t` and (for returns/gap) `t−1` — causal by construction.
- Output: F2 features feed [F3](F3_rolling_temporal_eng.md) (rolling), [F5](F5_classical_indicators_eng.md) (indicators) and [F6](F6_research_representations_eng.md) (stack).

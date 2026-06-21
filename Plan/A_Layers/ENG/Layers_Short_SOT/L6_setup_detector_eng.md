# L6 · Trend-line setup detector — OUTPUT contract (SOT)

The bridge between raw candles and feature rows. This file owns the **detector output contract** (what every
setup must provide), not the geometric algorithm: any geometry that produces setups satisfying the contract
below (the 5 invariants + DET-09) is a valid realization.

- Input: files `<TICKER>/<TICKER>_ohlcv_1h.parquet` in the Train window from [L5](L5_time_split_eng.md).
- The detector evaluates both directions and returns setup objects **causally** (fits use only candles `≤ t0`).

## Output objects (per setup)

| Object | Definition / requirement |
|---|---|
| `direction` (±1) | `+1` long (break **up** through resistance) / `−1` short (break **down** through support) |
| `L_trend(t)` | traded line = linear fit `a_t·t + b_t` through the touchpoints (resistance for long, support for short) |
| `L_opp(t)` | opposing line (the stop loss sits on it) = linear fit `a_o·t + b_o` |
| `topo_candles` | set of touchpoint candle indices on `L_trend`; touches **strictly before `t0`** (break ≠ touch; audit reports `pre_entry_touch_count`) |
| `entry_candle` (`t0`) | the **first** candle with `sign·(close[t] − L_trend(t)) > 0` after line qualification (≥ `MIN_TOUCHES` touches), close-based break |
| `R0` | `R0 = abs(close[t0] − L_opp(t0))` — one geometric unit of risk |
| `take_profit_level` | `take_profit_level = close[t0] + direction · R0` (fixed level) |
| `time_barrier_candle` | `time_barrier_candle = t0 + H` (`H = 24` candles) |

## The 5 invariants the detector must satisfy

1. A qualified line has at least `MIN_TOUCHES` (= 2) touches **before** `t0`.
2. `entry_candle` is the **first** close that breaks `L_trend` in the `direction` (close-based, strict `>`).
3. `L_opp` exists before `t0` (the stop has a reference at entry time).
4. The `L_trend` and `L_opp` fits use **only** touchpoints from candles `≤ t0` (causality).
5. **DET-09:** a setup with `R0 ≤ 0`, `ATR(t0) ≤ 0`, or a missing `L_opp` is **rejected and counted in the detector audit** — never silently dropped.

## DET-09 (reject + count)

A setup is rejected and incremented in `det09_rejected` when **any** of: `R0 ≤ 0`, `ATR(t0) ≤ 0`, or `L_opp`
missing. Ordering guard: `missing_L_opp` is checked **before** `R0 ≤ 0` (no abs on a missing line). The
rejection rate is a **WARN-only diagnostic** on the L8 dashboard (WARN if `> 20%`, never FAIL — see
[L8](L8_data_quality_eng.md)).

## ATR in L6

`ATR(t)` = Wilder, window `W_ATR = 14`, causal, candle `t` inclusive. In L6 it appears **only** inside the
touch test (`TOUCH_TOL · ATR(s)`) and the DET-09 guard `ATR(t0) > 0`. Barriers are geometric (`R0` from
`L_opp`, time in candles) and do **not** depend on ATR — no "ATR ↔ label" leakage. ATR is a feature
normalizer in [L7](L7_features_x_label_y_eng.md). Touch tolerance `TOUCH_TOL`, `MIN_TOUCHES`, `W_ATR`,
`H`: see [00_parameters_eng.md](00_parameters_eng.md).

- Output: setup objects → features X + label Y ([L7](L7_features_x_label_y_eng.md)).

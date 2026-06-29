# L7 · Features X + label Y (SOT)

Transformation of setup objects into a training matrix: row = setup, features computed at `t0`, target =
outcome per triple barrier. This file owns the 8 transformer columns (7 geometric + `closed_through_line` audit),
the **8-X manifest** (7 geometric + `direction`), the label, Output A/B and the sample weight.

- Input: setup objects from the detector ([L6](L6_setup_detector_eng.md)) in the Train window.
- At `t0` the transformer computes **exactly 8 columns** (Feature Set v1): 7 geometric features + the
  `closed_through_line` audit. The **model input** (`FEATURE_MANIFEST`) is **8 X** = the 7 geometric features +
  `direction` (carried from the L6 setup); it drops the audit column and adds `direction`.

## Transformer columns (8 = 7 X + closed_through_line audit)

Per candle `t`: `c=close[t]`, `o=open[t]`, `h=high[t]`, `l=low[t]`, `v=volume[t]`, `sign=direction`,
`ATR(t)` = Wilder, window `W_ATR=14`, causal, candle `t` **inclusive**. Volume `mean_W`/`std_W` window
(`W_VOL=20`) also ends at `t` inclusive. `ε = 1e-9`.

| Column | Formula | Unit | dtype | Guard / note |
|---|---|---|---|---|
| `distance_to_trend_line` | `sign·(c − L_trend(t)) / ATR(t)` | ×ATR | float | `< 0` before break, `> 0` after; denominator `max(ε, ATR(t))` |
| `distance_to_opposing_line` | `sign·(c − L_opp(t)) / ATR(t)` | ×ATR | float | headroom to SL (larger = farther from stop); denominator `max(ε, ATR(t))` |
| `risk_if_entered_pct` | `abs(c − L_opp(t)) / c · 100` | % | float | scale-independent; `c > 0` by QC-05, guard `c → max(ε, c)`. **Also a parameter of the Y geometry (defines R0) → mandatory ablation (guardrail R7)** |
| `bar_return_pct` | `(c − close[t−1]) / close[t−1] · 100` | % | float | continuous series ⇒ `t−1` exists; `close[t−1] = 0 → 0` (den=0→0) |
| `body_to_range_ratio` | `abs(c − o) / max(ε, h − l)` | [0,1] | float | `ε = 1e-9` explicit guard; `high == low → 0` |
| `volume_z_score` | `(v − mean_W) / std_W` | dimensionless | float | `mean_W, std_W` from `W_VOL = 20`; **`std = 0 → 0`** (never NaN/Inf) |
| `touch_count` | `count(topo_candles ≤ t)` | count | int | confirmed line touches up to candle `t` |
| `closed_through_line` | `1 if sign·(c − L_trend(t)) > 0 else 0` | flag {0,1} | int | break signal; in Output B (row = `t0`) definitionally `= 1` → **audit/invariant column, NOT part of `FEATURE_MANIFEST`** |

`distance_*` normalization reference choice: `DISTANCE_NORM = atr` (multiples of ATR). Parameter values:
see [00_parameters_eng.md](00_parameters_eng.md).

## FEATURE_MANIFEST (the 8 X), order frozen

```
1 distance_to_trend_line
2 distance_to_opposing_line
3 risk_if_entered_pct
4 bar_return_pct
5 body_to_range_ratio
6 volume_z_score
7 touch_count
8 direction
```

= the transformer's 7 geometric X (its 8 columns **minus `closed_through_line`**) + `direction`, the setup side
∈ {−1, +1} carried from the L6 setup (not transformer-computed, copied through). `closed_through_line` stays in
Output B as an audit column, always `= 1` at `t0`, outside X. The geometric features stay **sign-normalized**
(`sign·…`, so the same geometry is comparable across sides), and `direction` is an explicit input so the single
per-asset model can learn long/short asymmetry.

## Label Y

| Label | Definition | dtype | Where |
|---|---|---|---|
| `Y_entry` | `1 if t == entry_candle else 0` | int {0,1} | per-candle table (entry signal) |
| `Y_outcome` | triple barrier, close-based (below) | int {0,1} | training matrix (prediction target) |

`Y_outcome` — for the row at `t0`, iterate `t` from `t0+1` to `time_barrier_candle`; **first touch wins**:

- **TP → `Y = 1`:** first `t` with `sign·close[t] ≥ sign·take_profit_level` (i.e. `sign·close[t] ≥ sign·(close[t0] + direction·R0)`).
- **SL → `Y = 0`:** first `t` with `sign·close[t] < sign·L_opp(t)` — `L_opp(t)` is **moving** (the line value at `t`; decision v1.2).
- **Time → `Y = 0`:** none of the above resolves by `time_barrier_candle = t0 + H` (timeout).

`BARRIER_MODE = close` is the reference realization. X features at `t0` use `L_opp(t0)`; the moving `L_opp(t)`
is used only for the SL evaluation in the label. `LABEL_CONTRACT` annotation: `SL = L_opp(t) moving`.

## label_uniqueness_weight (average uniqueness)

For overlapping triple-barrier windows, setups with overlapping `[t0, time_barrier]` windows must not count
as independent. For setup `i` with window `W_i = [t0_i, tb_i]` within an `asset_id` partition (both directions together):

- `c_t = |{ j : t ∈ W_j }|` — the number of windows covering candle `t`.
- `weight_i = mean_{t ∈ W_i} (1 / c_t)`, with `c_t ≥ 1` by construction (the window covers itself), so the denominator is **never zero**.

## Outputs

**Output A** (optional, inspection) — one row per candle inside the setup window: `candle_index`, the 8
transformer columns (7 geometric + `closed_through_line`), `Y_entry`. (`direction` is setup-level and is added in Output B.)

**Output B** (the ML deliverable) — **one row per setup**, features computed at `t0`, target = `Y_outcome`.
Schema **frozen** (any change = hard fail):

| Column | Type | Role |
|---|---|---|
| `asset_id` | string | partition |
| `direction` | int {−1, +1} | **X** (8th manifest feature; from L6 setup) |
| `setup_id` | string/int | setup key |
| `entry_timestamp` | datetime | `timestamp[t0]` |
| `distance_to_trend_line` | float | X |
| `distance_to_opposing_line` | float | X |
| `risk_if_entered_pct` | float | X |
| `bar_return_pct` | float | X |
| `body_to_range_ratio` | float | X |
| `volume_z_score` | float | X |
| `touch_count` | int | X |
| `closed_through_line` | int {0,1} | **audit (invariant = 1)** |
| `Y_outcome` | int {0,1} | **target** |
| `label_uniqueness_weight` | float | sample weight |

Partitioning: a separate dataset / artifact per `asset_id` (one per asset; long and short setups share the asset's dataset and model).

## Anti-leakage (hard requirements)

- `L_trend`, `L_opp` fits are **causal** (candles `≤ t0` only).
- `ATR(t)` (feature normalizer) is causal; barriers are geometric, so ATR↔barrier separation holds by definition.
- No label leakage into features: no feature at `t0` may depend on candles `> t0`.
- `volume_z_score` uses the rolling window `W_VOL = 20` (not the full history) — regime stability.

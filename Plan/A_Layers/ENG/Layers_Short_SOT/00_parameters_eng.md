# 00 · Parameters (SOT)

The **only** configuration site is `config/params.json` (canonical file: `Plan/config/params.json`,
mirror of the source `config/params.json`); zero thresholds are hardcoded in code. This file owns every
parameter value; companion docs reference it and restate no number.

## Contract parameters (17 keys from `params.json`)

| Parameter | Default | Description |
|---|---|---|
| `TF` | `1h` | candle timeframe |
| `H` (`HORIZON_CANDLES`) | `24` | time-barrier length in candles (1h ⇒ 1 day); tuned |
| `MIN_TOUCHES` | `2` | minimum touches that validate a line |
| `W_VOL` | `20` | rolling window for `volume_z_score` |
| `W_ATR` | `14` | ATR window (feature normalizer) |
| `ATR_VARIANT` | `wilder` | ATR variant (Wilder); window `W_ATR`, causal, candle `t` inclusive |
| `PRICE_VIEW` | `raw_usd_view` | named input price view; corporate-actions policy out of scope for v1 (R1) |
| `EPS` | `1e-9` | division-by-zero guard (`ε`) |
| `BARRIER_MODE` | `close` | `close` (recommended) / `intrabar` |
| `DISTANCE_NORM` | `atr` | `atr` (recommended) / `pct` / `raw` |
| `THRESHOLD_ENTRY` | `0.60` | strategy decision threshold; tuned in Train, never on OOS |
| `PURGE_CANDLES` | `H` (= 24) | purge at window boundaries |
| `EMBARGO_SESSIONS` | `5` | embargo after the Train→OOS boundary (≈ 35 candles) |
| `N_TRIALS` | `200` | Optuna trial budget |
| `CV_SCHEME` | `purged_walk_forward` | CV inside Train (folds with purge+embargo) |
| `ESTIMATOR` | `xgboost_binary_logistic` | meta-labeling: setup-signal filter |
| `TUNER` | `optuna_tpe_median_pruner` | hyperparameter tuning (TPE + MedianPruner) |

All timeframe dependence is confined to `H` (and optionally `W_VOL`/`W_ATR`); changing `TF` needs only
reconfiguration of parameters, not logic changes.

## Detector reference-design values (`detector` block + top-level `TOUCH_TOL`)

Reference design (one valid realization) — F2 may replace these without breaking the L6 output contract.
Mirrored in `config/params.json` (`detector` block, plus top-level `TOUCH_TOL`).

| Symbol | Value | Units | Status |
|---|---|---|---|
| `k` (pivot strength) | `3` | candles each side | reference design (one valid realization) |
| `TOUCH_TOL` | `0.25` | × `ATR(t)` | reference design (one valid realization); name reserved by the L6 output contract |
| `LOOKBACK` (fit window) | `120` | candles | reference design (one valid realization) |
| `COOLDOWN` | `H` (= 24) | candles | reference design (one valid realization) |

Touch test: a swing point at index `s` with price `p_s` **touches** a line `L(·)` iff
`|p_s − L(s)| ≤ TOUCH_TOL · ATR(s)`. Dedup: **one swing-touch counts once**, not every adjacent candle.

## L8 threshold constants (the `l8` block)

Reference design (one valid realization) pending roadmap item F4b; the comparison operators and structure
are frozen, the numbers may be re-pinned in `config/params.json`. Applied to the counters in
[L8_data_quality_eng.md](L8_data_quality_eng.md).

| Counter / parity | OK iff | WARN iff | FAIL iff | Ceiling |
|---|---|---|---|---|
| `gaps_in_session` | `== 0` | — | `> 0` | FAIL |
| `gaps_filled` | `== 0` | — | `> 0` | FAIL |
| `duplicates` | `== 0` | — | `> 0` | FAIL |
| `prices_nonpos` | `== 0` | — | `> 0` | FAIL |
| `nan_inf_outputB` (undocumented only) | `== 0` | — | `> 0` | FAIL |
| parity P1 / P2 / P3 | equal | — | any mismatch | FAIL |
| `volume_zero_bars` / `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL |
| `zero_range_bars` / `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL |
| `det09_rejected` rate | `≤ 20%` | `> 20%` | never | **WARN max** (diagnostic) |

Zero-denominator guards (mandatory): fractions use `den = max(1, rows)`; the DET-09 rate uses
`det09_rejected / max(1, setups_total + det09_rejected)`; any internal float ratio uses `max(ε, …)`,
`ε = 1e-9`; `den = 0 → 0`.

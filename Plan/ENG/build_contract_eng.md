# Build contract — Pipeline A (v1)

This is the **authoritative, inlined English build contract** for **Pipeline A** (the S&P 500
trend-line meta-labeling strategy pipeline). It is the build-from-`Plan/`-alone copy of the master
contract: every fact below is authoritative and self-contained — the input, detector-output, feature, label, split, output,
parameter, QC and Definition-of-Done contracts (decision version 1.2) — plus the fixed reference values pinned for this single-source-of-truth
(SOT) package. Canonical terms follow `glossary_eng.md` verbatim (DuckDB, `VIEW ohlcv_1h`,
QC-01…QC-11, PF · Sharpe · MDD · TIM · WR, ATR = Wilder, warm-up, triple barrier,
`raw_usd_view`).

Sibling documents in this package (cross-linked by filename, not as the only source):
`glossary_eng.md`, `detector_algorithm_eng.md` (the reference detector algorithm),
`quality_gate_spec_eng.md` (the full L8 dashboard thresholds and `summary.json`), and the
per-layer summaries `L1…L10_*_eng.md`.

**Notation.** `t` = candle index (integer position after ascending sort by time). `t0` =
`entry_candle`. `sign` = `direction`. `c/o/h/l/v` = close/open/high/low/volume of candle `t`.
`ε = 1e-9` (`EPS`). All line functions (`L_trend(t)`, `L_opp(t)`), `H` and the purge operate on the
**index**, never on the timestamp.

---

## 1. Scope & the two pipelines

This project contains **two pipelines that must never be conflated**. **Pipeline A** is the S&P 500
trading-strategy pipeline, levels **L1–L10**: source candles → LEAN ZIP store → DuckDB
(`raw_ohlcv_1h` + `VIEW ohlcv_1h`, QC-01…QC-11) → parquet snapshot → time split → trend-line setup
**detector** (L6) → features X + label Y (L7) → quality dashboard (L8) → Optuna→XGBoost strategy
artifact (L9) → one-shot OOS test (L10). **Pipeline B** is a separate OHLCV→L5 feature DAG with its
own layer scheme **L0–L5** (documented elsewhere; native bar 1h; see §9 of this document for its
contract). **Certified v1 scope = Pipeline A end-to-end** (the detector is a *reference
implementation* of the §3 output contract; the geometric algorithm lives in
`detector_algorithm_eng.md`) **plus Pipeline B L0–L3** (the real `qc-transforms` materialization).
Pipeline B **L4/L5 are reference designs (one valid realization) — in the certified scope** — see Appendix A.

The contract is **scale- and timeframe-independent**: zero hardcoded price thresholds; the only TF
dependency lives in `H` (and optionally `W_VOL`/`W_ATR`). Default `TF = 1h`.

---

## 2. Input contract (§2)

A single OHLCV table for one Asset, **sorted ascending by time**, with **no gaps inside a session**.

### 2.1 Table schema (columns, types, invariants)

| Column | Type | Invariant / note |
|---|---|---|
| `timestamp` | datetime (UTC, tz-aware) | step = `TF`; **UTC tz-aware** — the naive-ET→UTC conversion is performed only by the F1 reader at the read boundary (§2.3) |
| `open` | float | — |
| `high` | float | `high ≥ max(open, close)` |
| `low` | float | `low ≤ min(open, close)` |
| `close` | float | — |
| `volume` | float, `≥ 0` | for the S&P 500 universe **volume is required; missing volume = hard fail QC**. Generic path for other Assets without volume → `volume_z_score = NaN` with an explicit flag (§4) |

Additional cross-bar invariant: `high ≥ low` (QC-01).

### 2.2 Input metadata (manifest — NOT table columns)

| Field | Type | Note |
|---|---|---|
| `price_view` | string | the named input price view. **v1 value = `raw_usd_view`** (the DuckDB `VIEW ohlcv_1h` in USD, prices = `raw/10000.0`). **Required** for repeatability. **One value per dataset** (snapshot manifest), never a per-row column. Corporate-actions policy is out of scope for v1 (open risk R1). |

In this project the canonical source of the contract is the DuckDB `VIEW ohlcv_1h` (USD)
materialized to one `parquet/<TICKER>/ohlcv.parquet` per ticker (503 files, `zstd`). The contract
itself stays source-independent: any table satisfying the schema above is a valid input.

### 2.3 Naive-ET → UTC-at-F1-reader rule

In the LEAN ZIP archive (L2), timestamps are stored as **naive ET** (`America/New_York`, no
timezone). The conversion **naive ET → UTC tz-aware is performed only by the F1 reader at the read
boundary** — never in the archive, never as a table edit. Because DST changes occur outside the
RTH session (09:00–16:00 ET), the conversion is unambiguous. Downstream layers see only UTC
tz-aware `timestamp`.

---

## 3. Detector OUTPUT contract (§3)

The features in §4 assume that for every **setup** the objects below are available. This document
defines the **detector output contract**, not the geometric algorithm (the reference algorithm is in
`detector_algorithm_eng.md`). The detector returns, **per setup, causally** (fits use only candles
`≤ t0`):

| Object | Definition / requirement |
|---|---|
| `direction` | `+1` (long, break **up** through resistance) / `−1` (short, break **down** through support) |
| `L_trend(t)` | the traded line value at candle `t` = linear fit `a_t·t + b_t` through the touchpoints (resistance for long, support for short) |
| `L_opp(t)` | the opposing line value at `t` (the stop loss sits on it) = linear fit `a_o·t + b_o` |
| `topo_candles` | set of touchpoint candle indices on `L_trend`; touches are **strictly before `t0`** (the break candle is not a touchpoint; audit reports `pre_entry_touch_count`) |
| `entry_candle` (`t0`) | the **first** candle with `sign·(close[t] − L_trend(t)) > 0` **after** line validation (≥ `MIN_TOUCHES` touches), close-based break |
| `R0` | `R0 = abs(close[t0] − L_opp(t0))` — one geometric unit of risk |
| `take_profit_level` | `take_profit_level = close[t0] + direction · R0` (fixed level) |
| `time_barrier_candle` | `time_barrier_candle = t0 + H` (`H = 24` candles, §7) |

### 3.1 The 5 invariants the detector must satisfy

1. A validated line has at least `MIN_TOUCHES` (= 2) touches **before** `t0`.
2. `entry_candle` is the **first** close that breaks `L_trend` in the `direction` (close-based).
3. `L_opp` exists before `t0` (the stop has a reference at entry time).
4. The `L_trend` and `L_opp` fits use **only** touchpoints from candles `≤ t0` (causality).
5. **DET-09:** a setup with `R0 ≤ 0`, `ATR(t0) ≤ 0`, or a missing `L_opp` is **rejected and counted
   in the detector audit** — never silently dropped.

### 3.2 DET-09 (reject + count)

DET-09 is the named rejection invariant. A setup is rejected and incremented in the audit counter
`det09_rejected` when **any** of: `R0 ≤ 0`, `ATR(t0) ≤ 0`, or `L_opp` is missing. The rejection rate
is a **diagnostic** signal on the L8 dashboard (WARN if `> 20%`, never FAIL — see §10 and
`quality_gate_spec_eng.md`).

Line-touch tolerance is a detector-contract parameter named **`TOUCH_TOL`** (see §9 of the source,
defined here in §9 of this document): a swing point touches a line iff
`abs(price − line(t)) ≤ TOUCH_TOL · ATR(t)`. Deduplication: **one swing-touch**, not every adjacent
candle.

> The barriers are **geometric** (`R0` from `L_opp`, time in candles) and do **not** depend on ATR,
> so the classic "ATR ↔ label" leakage does not occur here. ATR appears **only as a feature
> normalizer** (§4, §6).

---

## 4. Features X (§4)

Per candle `t`: `c=close[t]`, `o=open[t]`, `h=high[t]`, `l=low[t]`, `v=volume[t]`, `sign=direction`,
`ATR(t)` = average true range (window `W_ATR`, causal). The transformer computes **exactly 8
columns** at `t0` (Feature Set v1):

| Column | Formula | Unit | dtype | Guard / note |
|---|---|---|---|---|
| `distance_to_trend_line` | `sign·(c − L_trend(t)) / ATR(t)` | ×ATR | float | `< 0` before break, `> 0` after. Denominator: `ATR(t) > 0` (DET-09 rejects `ATR(t0) ≤ 0`); to be safe use `max(ε, ATR(t))`, ε=1e-9 |
| `distance_to_opposing_line` | `sign·(c − L_opp(t)) / ATR(t)` | ×ATR | float | headroom to SL (larger = farther from stop). Denominator guard `max(ε, ATR(t))`, ε=1e-9 |
| `risk_if_entered_pct` | `abs(c − L_opp(t)) / c · 100` | % | float | scale-independent. Denominator `c > 0` by QC-05; guard `c → max(ε, c)`, ε=1e-9. **Also a parameter of the Y geometry (defines R0) → mandatory ablation (guardrail R7)** |
| `bar_return_pct` | `(c − close[t−1]) / close[t−1] · 100` | % | float | continuous series ⇒ `t−1` exists; `close[t−1] = 0 → 0` (guard `den=0 → 0`), QC-05 makes this unreachable |
| `body_to_range_ratio` | `abs(c − o) / max(ε, h − l)` | dimensionless [0,1] | float | **ε = 1e-9** explicit guard; `high == low → 0` |
| `volume_z_score` | `(v − mean_W) / std_W` | dimensionless | float | `mean_W, std_W` from the rolling window `W_VOL = 20`. **`std = 0 → 0`** (return 0, never NaN/Inf) |
| `touch_count` | `count(topo_candles ≤ t)` | count | int | confirmed line touches up to candle `t` |
| `closed_through_line` | `1 if sign·(c − L_trend(t)) > 0 else 0` | flag | int {0,1} | break signal. **In Output B (row = `t0`) this is definitionally = 1 → it is an audit/invariant column and is NOT part of `FEATURE_MANIFEST`** (`test_entry_break_invariant`) |

**ATR definition (v1.2):** `ATR(t)` = **Wilder ATR** with window `W_ATR = 14`, computed causally on
candles ending at `t` **inclusive** (the break candle is intentionally included for feature
reactivity). Likewise the volume `mean_W`/`std_W` window ends at `t` inclusive.

**`distance_*` normalization (reference design — primary realization):** in multiples of **ATR**
(comparable across Assets and volatility regimes). `DISTANCE_NORM = atr` is the reference choice;
alternatives `/c` (price fraction) and `raw` (raw price units, single-Asset only) are documented
but not used in v1.

### 4.1 FEATURE_MANIFEST (the 7 X)

`FEATURE_MANIFEST` v1 = the transformer's 8 columns **minus `closed_through_line`** = **7 X
features**, order **frozen**:

```
1 distance_to_trend_line
2 distance_to_opposing_line
3 risk_if_entered_pct
4 bar_return_pct
5 body_to_range_ratio
6 volume_z_score
7 touch_count
```

`closed_through_line` stays in Output B as an **audit column, always = 1 at `t0`**, outside X.

---

## 5. Label Y (§5)

Two labels:

| Label | Definition | dtype | Where |
|---|---|---|---|
| `Y_entry` | `1 if t == entry_candle else 0` | int {0,1} | per-candle table (entry signal) |
| `Y_outcome` | **triple barrier, close-based** (below) | int {0,1} | training matrix (prediction target) |

**`Y_outcome` — for the row at `t0`:** iterate `t` from `t0+1` to `time_barrier_candle`. **First
touch wins:**

- **Take profit → `Y = 1`:** first `t` with `sign·close[t] ≥ sign·take_profit_level`
  (i.e. `sign·close[t] ≥ sign·(close[t0] + direction·R0)`).
- **Stop loss → `Y = 0`:** first `t` with `sign·close[t] < sign·L_opp(t)` — `L_opp(t)` is **moving**
  (the line value at `t`; decision v1.2, consistent with close-based line invalidation).
- **Time barrier → `Y = 0`:** none of the above resolves by `time_barrier_candle = t0 + H` (timeout).

`BARRIER_MODE = close` is the reference (recommended) realization; the `intrabar` (high/low)
alternative is documented but not used in v1. Note: X features at `t0` use `L_opp(t0)`; the moving
`L_opp(t)` is used only for the SL evaluation in the label, and `LABEL_CONTRACT` carries the explicit
annotation `SL = L_opp(t) moving`.

---

## 6. Splits (§5a)

Three disjoint time windows per Asset (boundaries are parameters in `config/params.json` → `splits`, not hardcode; default dates for
this project's universe):

| Window | Default | Role |
|---|---|---|
| **Warm-up** | `2016-01-04 → 2016-10-14` | roll-in of the rolling windows (`max(W_ATR, W_VOL) = 20` candles); rows with NULL features are dropped; **no training, no detection**. Default dates kept (conservative buffer — a parameter, not hardcode) |
| **Train** | `2016-10-17 → 2023-12-29` | the only repeatedly-touched window: setup detection, features, Optuna (purged walk-forward CV), model training |
| **OOS** | `2024-01-02 → 2026-05-29` | **frozen**: one test run of the strategy artifacts; zero tuning after looking at results |

### 6.1 Hard rules

1. **Purge** (`PURGE_CANDLES = H = 24`): a training row whose label window `[t0, t0+H]` crosses a
   window boundary is **removed** (the label must not reach into OOS). The purge operates on
   **setups**, not on candles.
2. **Embargo** (`EMBARGO_SESSIONS = 5` ≈ 35 candles): after the Train→OOS boundary skip an extra
   buffer covering rolling-feature autocorrelation (`5 sessions ≈ 35 candles ≥` max feature lookback
   = 20 candles).
3. **Optuna/CV only inside Train** (`CV_SCHEME = purged walk-forward`); folds are also separated by
   purge + embargo.
4. **OOS one-shot:** artifacts are frozen (hashed) first, then exactly one OOS run; the OOS result
   never returns to tuning.

---

## 7. Outputs (§6)

Two artifacts. **Output B is the actual ML deliverable; Output A is for inspection / feeds the
visualization.**

### 7.1 Output A — per-candle table (optional, inspection)

One row per candle inside the setup window. Columns: `candle_index`, the 8 feature columns (§4),
`Y_entry`.

### 7.2 Output B — training matrix (deliverable), full schema

**One row per setup**, features computed at `t0`, target = `Y_outcome`. Schema **frozen** (any
change = hard fail).

| Column | Type | Role |
|---|---|---|
| `asset_id` | string | partition |
| `direction` | int {−1, +1} | partition |
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
| `label_uniqueness_weight` | float | sample weight (§7.3) |

**Partitioning:** a separate dataset / artifact per `{asset_id} × {direction}` pair. `asset_id` is
generic — the same pipeline runs for every Asset.

### 7.3 `label_uniqueness_weight` (average uniqueness)

For overlapping triple-barrier windows, setups with overlapping `[t0, time_barrier]` windows must
not count as independent. For setup `i` with window `W_i = [t0_i, tb_i]` within a
`{asset_id} × {direction}` partition:

- `c_t = |{ j : t ∈ W_j }|` — the number of windows covering candle `t`.
- `weight_i = mean_{t ∈ W_i} (1 / c_t)`.

A setup with no overlap → `weight = 1.0`. Guard: every window covers at least itself, so `c_t ≥ 1`
and the `1/c_t` denominator is never zero.

### 7.4 Anti-leakage hard requirements

- `L_trend`, `L_opp` fits are **causal** (candles `≤ t0` only).
- `ATR(t)` (feature normalizer) is causal; barriers are geometric, so ATR↔barrier separation holds by
  definition.
- No label leakage into features: no feature at `t0` may depend on candles `> t0`.
- `volume_z_score` uses the rolling window `W_VOL = 20` (not the full history) — regime stability.

---

## 8. Strategy artifact (§6a)

Final deliverable of the ML pipeline: **one self-contained `strategy_<ASSET>.py` per Asset**
(target ×503). Mandatory sections:

| Section | Content |
|---|---|
| `MODEL_B64` | the XGBoost (`binary:logistic`) model serialized and **base64**-encoded (~180 kB), decoded and loaded at import |
| `FEATURE_MANIFEST` | the **7 X columns** in frozen order (without `closed_through_line` — audit; exactly the columns the model was trained on; see §4.1) |
| `LABEL_CONTRACT` | the label-semantics identifier: `TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24` |
| `THRESHOLD_ENTRY` | decision threshold; rule: `p = model(x)`, `p ≥ THRESHOLD_ENTRY → ENTRY`, else FLAT (`THRESHOLD_ENTRY = 0.60`) |
| `selfcheck()` | golden vectors (input → expected `p`) verified at import; any divergence → hard error |

**Requirements:** the file imports **standalone** (no access to training data); the build is
**deterministic** (same run → same file hash); `THRESHOLD_ENTRY` is tuned only in Train, never on
OOS. The model's role is **meta-labeling**: it *filters* the trend-line setup signal (the primary
signal comes from the detector); it does not search for trades.

---

## 9. Parameters (§7)

The **only** place for configuration. In this SOT package the canonical file lives at
**`Plan/config/params.json`** (mirror of the source `config/params.json`); zero thresholds are
hardcoded in code. Full table (all 17 keys from `params.json`):

| Parameter | Default | Description |
|---|---|---|
| `TF` | `1h` | candle timeframe |
| `H` (`HORIZON_CANDLES`) | `24` | time-barrier length in candles (1h ⇒ 1 day); tuned |
| `MIN_TOUCHES` | `2` | minimum touches that validate a line |
| `W_VOL` | `20` | rolling window for `volume_z_score` |
| `W_ATR` | `14` | ATR window (feature normalizer) |
| `ATR_VARIANT` | `wilder` | ATR variant (**Wilder**); window `W_ATR`, causal, candle `t` inclusive (§4) |
| `PRICE_VIEW` | `raw_usd_view` | named input price view (§2); corporate-actions policy out of scope for v1 (R1) |
| `EPS` | `1e-9` | division-by-zero guard |
| `BARRIER_MODE` | `close` | `close` (recommended) / `intrabar` |
| `DISTANCE_NORM` | `atr` | `atr` (recommended) / `pct` / `raw` |
| `THRESHOLD_ENTRY` | `0.60` | strategy decision threshold (§8); tuned in Train, never on OOS |
| `PURGE_CANDLES` | `H` (= 24) | purge at window boundaries (§6) |
| `EMBARGO_SESSIONS` | `5` | embargo after the Train→OOS boundary (§6) |
| `N_TRIALS` | `200` | Optuna trial budget |
| `CV_SCHEME` | `purged_walk_forward` | CV inside Train (folds with purge+embargo) |
| `ESTIMATOR` | `xgboost_binary_logistic` | meta-labeling: setup-signal filter |
| `TUNER` | `optuna_tpe_median_pruner` | hyperparameter tuning (TPE + MedianPruner) |

### 9.1 `TOUCH_TOL` (reference design)

`TOUCH_TOL = 0.25` (units: **×ATR(t)**) is the **reference design (one valid realization)** of the
detector-contract touch tolerance: a swing point touches a line iff
`abs(price − line(t)) ≤ TOUCH_TOL · ATR(t)`. It is **not** present in the source `params.json`; it
is pinned here and **lives in `Plan/config/params.json`** alongside the 17 keys above.

> All timeframe dependence is confined to `H` (and optionally `W_VOL`/`W_ATR`). Changing `TF` needs
> only reconfiguration of parameters, not logic changes.

---

## 10. QC-01…QC-11 predicates + L8 pointer

The L3 load is gated by **11 quality predicates** (copied from `glossary_eng.md` L3). A load that
fails any QC is **not published**.

| Gate | Predicate |
|---|---|
| QC-01 | `high ≥ low` |
| QC-02 | `high ≥ max(open, close)` **and** `low ≤ min(open, close)` |
| QC-03 | no duplicate `(symbol, ts)` |
| QC-04 | zero NULL in `open/high/low/close/volume` |
| QC-05 | prices `> 0` |
| QC-06 | `volume ≥ 0` |
| QC-07 | universe complete: 503/503 symbols |
| QC-08 | candles per day `∈ [5, 9]` |
| QC-09 | `ts` within the session 09:00–16:00 ET |
| QC-10 | `ts` strictly increasing per symbol |
| QC-11 | date range and counters match `_meta` |

The **L8 quality dashboard** (the gate before training) measures and reports the quality of the whole
flow (L2–L7) and **fixes nothing**. Its thresholds, the aggregation rule (any FAIL → dashboard FAIL →
L9 blocked; WARN without FAIL → proceed) and the `summary.json` schema are specified in
**`quality_gate_spec_eng.md`**. For reference, the L8 thresholds are: in-session gaps FAIL `> 0`;
filled gaps FAIL `> 0`; duplicates `(symbol, ts)` FAIL `> 0`; prices `≤ 0` FAIL `> 0`; undocumented
NaN/Inf in Output B FAIL `> 0`; parity mismatch (zip→DuckDB→parquet→Output B) FAIL on any; `volume = 0`
bars WARN `> 0.5%` / FAIL `> 2%`; zero-range (`high == low`) bars WARN `> 0.5%` / FAIL `> 2%`; DET-09
rejection rate WARN `> 20%` (diagnostic, never FAIL).

---

## 11. Definition of Done (§8)

- [ ] The pipeline accepts raw OHLCV of any Asset (any price scale) and any `TF`; zero hardcoded price thresholds.
- [ ] Output B has exactly the schema of §7 (column names and types match by sign).
- [ ] **Causality verified:** a test detecting use of any candle `> t` when computing a feature/line for `t` (e.g. shifting the future does not change historical values).
- [ ] `closed_through_line` is `1` from `entry_candle` onward and `0` before (on a clean setup).
- [ ] `Y_outcome` matches the first-touch rule and `BARRIER_MODE`; unit cases TP/SL/time-barrier covered by tests.
- [ ] `volume_z_score` correct for `std = 0` (returns `0`, not NaN/Inf); `body_to_range_ratio` correct for `high == low`.
- [ ] No NaN/Inf in Output B beyond documented cases (e.g. an Asset without volume → `volume_z_score = NaN` with an explicit flag).
- [ ] `label_uniqueness_weight` computed for overlapping windows (formula in §7.3).
- [ ] Partitioning per `{asset_id} × {direction}`.
- [ ] Determinism: same input → same output (hash-testable).
- [ ] **Splits verified by assertion:** no label window `[t0, t0+H]` crosses a Warm-up/Train/OOS boundary (purge + embargo of §6 works).
- [ ] Strategy artifact (§8): imports standalone, `selfcheck()` PASS, deterministic build (hash).
- [ ] OOS one-shot: artifacts frozen before the test; the OOS result never returns to tuning.
- [ ] `FEATURE_MANIFEST` contains exactly the **7 X columns**; `closed_through_line` present in B as audit and constantly `= 1`.
- [ ] Setups rejected by invariant 5 of §3 (DET-09: `R0 ≤ 0` / `ATR(t0) ≤ 0` / missing `L_opp`) are counted in the audit report — they do not vanish silently.

---

## Appendix A — Pipeline B contract (separate; **L0–L5 certified**; detector & L4/L5 = reference design)

Pipeline B is the OHLCV→L5 feature DAG, layers **L0–L5** (a **different** scheme from Pipeline A's
L1–L10; never conflate). **Native bar = 1h**, so the only resample is **1h → 1d**. Certified v1 =
**L0–L5**: L0–L3 = the real `qc_raw_ohlcv_data_sp500_alpaca_transforms` materialization; **L4 and L5 below
are reference designs (one valid realization), in the certified scope.**

### A.1 Pipeline B grids (real `qc-transforms`, L0–L3)

From the `qc_raw_ohlcv_data_sp500_alpaca_transforms/structure` materialization:

- 1h rolling windows `n ∈ {5, 10, 20, 50}`; 1d rolling windows `{20, 200}`.
- lag `k = 1`.
- regime quantiles `[0.33, 0.66]`.
- volume-z thresholds `[−1.0, 1.0]`.
- native bar `1h`; resample `1h → 1d`; session phases (1h-adapted).

Layers: `L0` Raw OHLCV (O H L C V) · `L1` atomic transforms (point-wise) · `L2` rolling/temporal
(lags, rolling windows of length `n`) · `L3` MTF/regime (resample 1h→1d, recompute L1/L2, context
aggregates).

### A.2 Pipeline B L4 — classical indicators (reference design — certified)

Textbook definitions with zero-denominator guards (ε = 1e-9):

- `RSI_n` (Wilder smoothing).
- `MACD(12, 26, 9)`.
- canonical **`l4_atr = mean_n(TR)`** (matches viz/glossary). ADX (below) may use an internal Wilder-smoothed TR for ±DI — that internal series is **not** the canonical `l4_atr`.
- `OBV`, `ADL`, `Stoch_n`.
- `ADX`: `DX = 100 · |+DI − −DI| / max(ε, +DI + −DI)`; `ADX = Wilder_smooth(DX, n)`.
- `MFI_n`.
- `VWAP = Σ(TP·V) / max(ε, ΣV)`.

### A.3 Pipeline B L5 — research representations (reference design — certified)

All L5: **fit scope = Train only** (no leakage); transform API = `transform(X) -> features`.

- **PCA** — sklearn, `n_components = 8`, fit Train-only on standardized `X_raw`, persist
  `components_` / `mean_` / `explained_variance_` via joblib, transform = project.
- **DWT** — pywt `wavedec`, wavelet `db4`, level 3, rolling window `W = 64`, causal, output =
  per-level energy.
- **Autoencoder** — MLP, encoder dims `[64, 32, 8]`, ReLU, MSE, Adam, 50 epochs, fit Train-only,
  persist torch `state_dict`, transform = encoder.
- **Sequence** — LSTM hidden = 32, 1 layer, input window = 24 bars of `X_raw`, output = last hidden
  `h_t ∈ R^32`, persist `state_dict`.

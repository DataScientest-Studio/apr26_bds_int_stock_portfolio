# Detector algorithm — reference implementation (Pipeline A · L6)

> **Status: "reference design (one valid realization)".** The build contract (`build_contract_eng.md` §Detector output)
> defines only the **output contract** of the trend-line setup detector and explicitly defers the
> *geometric algorithm* to sub-task **F2** (ROADMAP). This document specifies **one concrete, causal
> algorithm** that satisfies that contract end-to-end. Every parameter taken from the contract
> (`MIN_TOUCHES=2`, `H=24`, `W_ATR=14`, `ATR_VARIANT=wilder`, `PRICE_VIEW=raw_usd_view`, `EPS=1e-9`)
> is canonical; every parameter introduced here only to make the algorithm runnable
> (`k=3`, `TOUCH_TOL=0.25`, `COOLDOWN=H`, the fit/window choices) is labelled **"reference design
> (one valid realization)"** and is the kind of value F2 may replace without breaking the §3 contract.

This is **Pipeline A** (the S&P 500 strategy, layers **L1–L10**); the detector is **L6**. It must not be
conflated with **Pipeline B** (OHLCV → L5 feature DAG, layers **L0–L5**), which is a separate scheme.

**Notation (from the glossary).** `t` = candle index (integer position after ascending sort by time, on
one continuous series per asset). `t0` = `entry_candle`. `sign = direction ∈ {+1, −1}`. For candle `t`:
`c = close[t]`, `o = open[t]`, `h = high[t]`, `l = low[t]`, `v = volume[t]`. All line functions,
`H`, purge and cooldown operate on the **index**, not on the timestamp. The detector reads the
`VIEW ohlcv_1h` (USD) materialized to `parquet/<TICKER>/ohlcv.parquet` (L4), restricted to the **Train**
window from L5 (warm-up rolls in the windows; OOS is frozen).

---

## 0. Causality contract (the overriding rule)

For any candle `t`, the detector uses **only candles `≤ t0`** when it fits lines, validates touches and
locates the break. There is **zero look-ahead** (glossary "Causality / zero look-ahead"). Concretely:

- A pivot at index `i` is **confirmed at candle `i+3`** (strength `k=3`), so a pivot is only usable from
  `i+3` onward — never the instant it forms.
- `L_trend`, `L_opp` are least-squares fits over swing indices **all `≤ t0`** (build_contract_eng.md §Detector output invariant 4).
- `ATR(t)` is Wilder, window `W_ATR=14`, computed on candles **ending at `t` inclusive**
  (glossary L6; build_contract_eng.md §Features (decision v1.2) note — the break candle is deliberately included in the normalizer).

The only forward-looking object in the whole pipeline is the **label window** `[t0, t0+H]`, which belongs
to L7 (triple barrier), **not** to the detector.

---

## 1. Fixed reference values

All values below are mirrored in `config/params.json` (`detector` block, plus top-level `TOUCH_TOL`) — the single configuration site.

| Symbol | Value | Units | Source |
|---|---|---|---|
| `k` (pivot strength) | `3` | candles each side | reference design (one valid realization) |
| `MIN_TOUCHES` | `2` | swing touches | contract (`config/params.json`, build_contract_eng.md §Parameters) |
| `TOUCH_TOL` | `0.25` | × `ATR(t)` | reference design (one valid realization); name reserved by build_contract_eng.md §Detector output; value set here and in `config/params.json` |
| `COOLDOWN` | `H = 24` | candles | reference design (one valid realization) |
| `H` | `24` | candles (horizon) | contract (build_contract_eng.md §Parameters) |
| `W_ATR` | `14` | candles | contract (build_contract_eng.md §Parameters) |
| `ATR_VARIANT` | `wilder` | — | contract (build_contract_eng.md §Parameters) |
| `LOOKBACK` (fit window) | `120` | candles | reference design (one valid realization) |
| `EPS` (ε) | `1e-9` | — | contract (build_contract_eng.md §Parameters) |

**Touch test (the load-bearing definition).** A swing point at index `s` with price `p_s`
(`p_s = high[s]` for a resistance line, `p_s = low[s]` for a support line) **touches** a candidate line
`L(·)` iff:

```
| p_s − L(s) | ≤ TOUCH_TOL · ATR(s)          # TOUCH_TOL = 0.25
```

Dedup rule (build_contract_eng.md §Detector output): **one swing-touch counts once**, not every adjacent candle that happens to lie
within tolerance.

---

## 2. Wilder ATR(t), guarded (the only ATR in L6)

True range and the Wilder recursion, causal, window `W_ATR=14`:

```
TR[t] = max( h − l ,  | h − close[t−1] | ,  | l − close[t−1] | )   # t≥1; TR[0] = h[0] − l[0]
ATR[W_ATR-1] = mean( TR[0 .. W_ATR-1] )                            # seed = simple mean of first 14 TR
ATR[t]       = ( ATR[t−1] · (W_ATR − 1) + TR[t] ) / W_ATR          # Wilder smoothing, t ≥ W_ATR
```

`ATR(t)` appears in L6 **only** inside `TOUCH_TOL·ATR(s)` (the touch test) and in the DET-09 guard
`ATR(t0) > 0`. It is **not** part of any barrier (barriers are geometric; build_contract_eng.md §Detector output / §Label — "no ATR↔label
coupling"). During warm-up `ATR(t)` is `NULL`/undefined for `t < W_ATR-1`; such candles can be pivots
but **cannot be `t0`** (the DET-09 guard `ATR(t0) ≤ 0` rejects them, see §8).

---

## 3. Step 1 — causal pivot / swing detection (strength `k=3`)

A **swing high** at index `i` (`3 ≤ i ≤ N−4`) iff `high[i]` is a strict local maximum over the window
`[i−3, i+3]`:

```
isSwingHigh(i) = ( high[i] >= high[j]  for all j in [i−3, i+3], j != i )
                 AND ( high[i] >  high[j]  for at least one j on each side )   # strictness, avoids flat plateaus
```

A **swing low** at index `i` is the mirror over `low[i]` (strict local minimum over `[i−3, i+3]`).

**Confirmation latency.** A swing at `i` requires candles up to `i+3` to be confirmed, so it becomes
visible to the detector only at candle `i+3`. When scanning for an entry at `t0`, only swings with
`i+3 ≤ t0` (equivalently `i ≤ t0−3`) are eligible — this is what enforces causality at the swing level.
Ties (equal highs on both sides) are resolved by the strictness clause: a flat plateau yields **no** pivot,
preventing duplicate swings at the same level.

The output is two index lists per asset: `SH = [swing-high indices]`, `SL = [swing-low indices]`,
each sorted ascending.

---

## 4. Step 2 — candidate line fit (least-squares through ≥ `MIN_TOUCHES` swings)

A line is `L(t) = a·t + b`. Given a set of swing indices `S = {s_1, …, s_m}` (with prices `p_{s}` =
highs for resistance, lows for support), the **guarded** ordinary-least-squares fit is:

```
n     = |S|                                  # require n >= MIN_TOUCHES = 2
Sx    = Σ s
Sy    = Σ p_s
Sxx   = Σ s·s
Sxy   = Σ s·p_s
den   = n·Sxx − Sx·Sx                          # = n · Σ(s − s̄)²  ≥ 0
if den <= EPS:  a = 0;  b = Sy / max(EPS, n)   # GUARD: collinear-in-t / single distinct index → flat line at mean price
else:           a = (n·Sxy − Sx·Sy) / den
                b = (Sy − a·Sx) / n            # n ≥ 2 here, no zero-division
```

The guard `den ≤ EPS` (ε = 1e-9) catches the degenerate case where every swing shares (numerically) the
same index — impossible for distinct confirmed swings, but defended anyway.

**Which swings define `L_trend` (per build_contract_eng.md §Detector output: "fit through the touchpoints").**

- **Long (`direction = +1`)**: `L_trend` is a **resistance** line. Take the swing highs `SH` inside the
  causal window `[t0 − LOOKBACK, t0−3]`, fit a line through the **`MIN_TOUCHES` most-recent qualifying
  swing highs**, then *grow* the touch set: every swing high in the window that passes the touch test
  (§1) against this line is appended to `topo_candles`, and the line is **re-fit** through the full
  touch set (a single re-fit pass). The line is **validated** iff `|topo_candles| ≥ MIN_TOUCHES` with all
  touches **strictly before `t0`**.
- **Short (`direction = −1`)**: mirror — `L_trend` is a **support** line through swing lows `SL`.

If fewer than `MIN_TOUCHES` qualifying swings exist in the window, **no candidate line** is emitted for
this `(direction, t0)` — the scan moves on (this is *not* a DET-09 rejection; there simply is no setup).

---

## 5. Step 3 — `L_opp` construction (opposing line)

The stop loss lives on `L_opp` (glossary L6). It is the **opposite-side** least-squares line over the
**same causal window** `[t0 − LOOKBACK, t0−3]`:

- **Long**: `L_opp` = least-squares **support** line through the swing **lows** `SL` in the window;
  validated by the same touch test (§1) requiring **`≥ 2`** opposite-side touches.
- **Short**: `L_opp` = least-squares **resistance** line through the swing **highs** `SH` in the window,
  `≥ 2` touches.

If fewer than 2 opposite-side swings exist in the window (or none pass the touch test), `L_opp` is
**missing** → the setup is **rejected and counted** as DET-09 `missing_L_opp` (§8). build_contract_eng.md §Detector output invariant 3
("`L_opp` exists before `t0`") and invariant 4 ("fits use only candles ≤ `t0`") are thereby satisfied.

---

## 6. Step 4 — direction & entry candle `t0`

The detector evaluates **both** directions independently and symmetrically (§9):

- `direction = +1` (long): break **upward through resistance** `L_trend`.
- `direction = −1` (short): break **downward through support** `L_trend`.

For a validated `L_trend` (built from data `≤ t0−3`), the **entry candle** is the **first** close that
breaks the line in the trade direction (build_contract_eng.md §Detector output invariant 2, close-based):

```
entry_candle t0 = first t (t > last_touch_index) such that  sign · ( close[t] − L_trend(t) ) > 0
```

The strict inequality `> 0` (not `≥`) means a close *exactly on* the line is **not** a break. Because
`closed_through_line = 1 ⇔ sign·(c − L_trend) > 0`, the entry definition guarantees
`closed_through_line(t0) = 1` definitionally — the L7 audit invariant (`test_entry_break_invariant`).

**Practical scan.** The detector advances `t` forward through the Train window. At each candidate `t`
treated as a prospective `t0`, it (a) builds `L_trend`/`L_opp` from swings `≤ t−3`, (b) checks validation
(`|topo_candles| ≥ 2`), (c) tests the break condition above at `t`. The first `t` satisfying all three is
emitted as a setup's `t0`.

---

## 7. Step 5 — dedup / cooldown = `H`, and long/short symmetry

**Dedup / cooldown (reference design).** After a setup fires on a given `L_trend` at `t0`, the detector
**suppresses new entries on the same line** for `COOLDOWN = H = 24` bars: any break of the *same*
validated line at `t ∈ (t0, t0 + COOLDOWN]` is ignored. "Same line" = the line carried the same touch set
(or a superset that still passes the touch test against the recorded `(a, b)` within `TOUCH_TOL·ATR`).
This prevents one trend line from emitting a burst of near-identical setups and aligns the suppression
horizon with the label horizon `H` so overlapping labels stay rare (L7 `label_uniqueness_weight` still
handles residual overlap). A line that is *re-fit* with a genuinely new swing after the cooldown is a new
line and may fire again.

**Long/short symmetry.** The long and short detectors are exact mirrors: swap (highs ↔ lows),
(resistance ↔ support), and `sign` flips from `+1` to `−1` in the break test and in `take_profit_level`.
The two directions are independent partitions downstream (`{asset_id} × {direction}`, glossary L7), so a
long and a short setup may legitimately coexist at overlapping indices.

---

## 8. DET-09 — rejection + audit (build_contract_eng.md §Detector output invariant 5)

A setup that has located a `t0` is **rejected and counted** (never silently dropped) iff **any** of:

```
R0 ≤ 0           # R0 = abs(close[t0] − L_opp(t0)); zero/negative geometric risk
ATR(t0) ≤ 0      # normalizer undefined / non-positive (e.g. t0 still in warm-up, or flat 14-bar TR)
L_opp missing    # no validated opposing line in the causal window (§5)
```

Each rejection increments a typed counter; the detector emits an audit record
`{asset_id, direction, t0, reason ∈ {R0_nonpos, ATR_nonpos, missing_L_opp}}`. These feed
`summary.json.counters.det09_rejected` (§11). The DET-09 **rejection rate** is a **WARN-only diagnostic**
at `>20%` and **never FAILs** the L8 dashboard (a high reject rate signals a noisy asset, not a broken
pipeline). Note the ordering guard: `R0` is only computed after `L_opp` is confirmed present, so the
`missing_L_opp` branch is checked **before** the `R0 ≤ 0` branch (no division/abs on a missing line).

---

## 9. Pseudocode (causal, both directions)

```text
INPUT  : ohlcv[0..N-1] for one asset (Train window), params
OUTPUT : list of setup objects + DET-09 audit counters

precompute ATR[0..N-1]          # Wilder, W_ATR=14, causal (see §2); NULL for t < W_ATR-1
SH = swing_high_indices(ohlcv, k=3)   # confirmed at i+3 (§3)
SL = swing_low_indices (ohlcv, k=3)

setups = []
audit  = { R0_nonpos:0, ATR_nonpos:0, missing_L_opp:0 }
cooldown_until = { }            # keyed by (direction, line_id) -> bar index

for direction in (+1, -1):
    sign = direction
    for t0 in range(W_ATR, N):                     # t0 candidate = prospective entry candle
        win_lo = max(0, t0 - LOOKBACK)
        swings_trend = (SH if sign==+1 else SL) filtered to [win_lo, t0-3]   # causal: i <= t0-3
        if len(swings_trend) < MIN_TOUCHES:  continue                         # no line -> no setup

        # ---- Step 2: fit L_trend through 2 most-recent qualifying swings, then grow + re-fit ----
        seed   = last MIN_TOUCHES indices of swings_trend
        Ltrend = lsq_fit_guarded(seed)                                        # §4 (den<=EPS guard)
        topo   = [ s for s in swings_trend if touch(s, Ltrend) ]              # §1 touch test, dedup
        if len(topo) < MIN_TOUCHES:  continue
        Ltrend = lsq_fit_guarded(topo)                                        # single re-fit pass
        last_touch = max(topo)
        if last_touch >= t0:  continue                                        # touches strictly before t0

        # ---- Step 4: break test (close-based, strict) ----
        if not ( sign * (close[t0] - Ltrend(t0)) > 0 ):  continue             # not the entry candle
        # first-break: ensure no earlier t in (last_touch, t0) already broke
        if any( sign*(close[t]-Ltrend(t)) > 0  for t in (last_touch, t0) ):  continue

        # ---- cooldown / dedup (§7) ----
        line_id = round_line(Ltrend)
        if t0 <= cooldown_until.get((direction,line_id), -1):  continue

        # ---- Step 3: L_opp (opposite side) ----
        swings_opp = (SL if sign==+1 else SH) filtered to [win_lo, t0-3]
        Lopp = lsq_fit_guarded(swings_opp) if count_touches(swings_opp) >= 2 else MISSING

        # ---- DET-09 (§8): order matters — missing first ----
        if Lopp is MISSING:
            audit.missing_L_opp += 1;  continue
        R0 = abs(close[t0] - Lopp(t0))
        if ATR[t0] is NULL or ATR[t0] <= 0:
            audit.ATR_nonpos += 1;     continue
        if R0 <= 0:
            audit.R0_nonpos += 1;      continue

        # ---- emit setup (§3 output contract) ----
        setups.append({
            direction          : sign,
            L_trend            : Ltrend,                       # callable a_t*t + b_t
            L_opp              : Lopp,                          # callable a_o*t + b_o
            topo_candles       : topo,                          # touches strictly < t0
            entry_candle       : t0,
            R0                 : R0,
            take_profit_level  : close[t0] + sign * R0,
            time_barrier_candle: t0 + H,                        # H = 24
        })
        cooldown_until[(direction,line_id)] = t0 + COOLDOWN     # = t0 + H
```

`lsq_fit_guarded`, `touch`, the Wilder `ATR` and the swing detectors are exactly §2–§5 above; every
division they contain is guarded (`den ≤ EPS → flat line`, `mean = Sy / max(EPS, n)`, `ATR / W_ATR` with
`W_ATR = 14`).

---

## 10. Worked examples

Synthetic indices and USD prices (from `VIEW ohlcv_1h`); `ATR(t0)` values are illustrative and positive.
These are **reference design (one valid realization)** numerical walk-throughs, not data from the source.

### 10.1 Long (break up through resistance)

Swing highs near a descending/flat resistance, swing lows below as the opposing support.

| index `i` | role | `high[i]` | `low[i]` |
|---|---|---|---|
| 40 | swing high (touch 1) | 101.00 | — |
| 58 | swing high (touch 2) | 100.96 | — |
| 76 | swing high (touch 3) | 101.02 | — |
| 47 | swing low (opp touch 1) | — | 96.10 |
| 69 | swing low (opp touch 2) | — | 96.55 |

- **`L_trend`** (resistance, LSQ through 40/58/76): ≈ flat at `L_trend(t) ≈ 100.99`. With
  `ATR(76)=0.30`, `TOUCH_TOL·ATR = 0.25·0.30 = 0.075`; all three highs lie within `±0.075` → `topo_candles
  = {40, 58, 76}`, `|topo| = 3 ≥ MIN_TOUCHES`. Valid.
- **Break / `t0`**: at `t0 = 80`, `close[80] = 101.40`. `sign·(c − L_trend) = +1·(101.40 − 100.99) =
  +0.41 > 0` → first break → `entry_candle = 80`, `closed_through_line(80) = 1`.
- **`L_opp`** (support, LSQ through 47/69): rising line; `L_opp(80) ≈ 96.92` (`a_o ≈ 0.0205`,
  `b_o ≈ 95.28`). Present (2 touches) → no `missing_L_opp`.
- **`R0`** `= |close[80] − L_opp(80)| = |101.40 − 96.92| = 4.48`. `R0 > 0` ✓; `ATR(80) = 0.31 > 0` ✓ →
  **not** rejected by DET-09.
- **`take_profit_level`** `= close[80] + (+1)·4.48 = 105.88`.
- **`time_barrier_candle`** `= 80 + 24 = 104`.
- **Cooldown**: any further up-break of this same resistance at `t ∈ (80, 104]` is suppressed.

### 10.2 Short (break down through support)

Mirror image: swing lows near a flat support, swing highs above as the opposing resistance.

| index `i` | role | `high[i]` | `low[i]` |
|---|---|---|---|
| 35 | swing low (touch 1) | — | 50.02 |
| 53 | swing low (touch 2) | — | 49.98 |
| 71 | swing low (touch 3) | — | 50.00 |
| 44 | swing high (opp touch 1) | 53.40 | — |
| 66 | swing high (opp touch 2) | 53.05 | — |

- **`L_trend`** (support, LSQ through 35/53/71): ≈ flat at `L_trend(t) ≈ 50.00`. `ATR(71)=0.12`,
  `TOUCH_TOL·ATR = 0.03`; all three lows within `±0.03` → `topo_candles = {35, 53, 71}`, valid.
- **Break / `t0`**: at `t0 = 75`, `close[75] = 49.70`. `sign·(c − L_trend) = −1·(49.70 − 50.00) =
  −1·(−0.30) = +0.30 > 0` → first down-break → `entry_candle = 75`, `closed_through_line(75) = 1`.
- **`L_opp`** (resistance, LSQ through 44/66): falling line; `L_opp(75) ≈ 52.81`. Present (2 touches).
- **`R0`** `= |49.70 − 52.81| = 3.11 > 0` ✓; `ATR(75) = 0.13 > 0` ✓ → not rejected.
- **`take_profit_level`** `= close[75] + (−1)·3.11 = 46.59`.
- **`time_barrier_candle`** `= 75 + 24 = 99`.

### 10.3 DET-09 rejection (missing `L_opp`)

Same long structure as 10.1, but the asset has had **only one** swing low (`{47}`) in the causal window
`[t0−120, t0−3]` (a strong trend with no intermediate pullback). The opposing-support fit needs `≥ 2`
touches → `L_opp` is **MISSING**. The setup is **rejected**, `audit.missing_L_opp += 1`, and no `R0` is
computed (ordering guard, §8). If instead `L_opp` existed but coincided with the entry close so that
`R0 = |close[t0] − L_opp(t0)| = 0`, the `R0_nonpos` counter would increment. Either way the candidate is
counted in `summary.json.counters.det09_rejected`, never silently dropped.

---

## 11. Contract conformance — mapping to build_contract_eng.md §Detector output

| §3 output object | Definition (§3) | Produced by (this doc) | Guard |
|---|---|---|---|
| `direction` (±1) | +1 long / −1 short | §6, both-direction scan; symmetry §7 | — |
| `L_trend(t) = a_t·t + b_t` | LSQ through touchpoints (resistance long / support short) | §4 `lsq_fit_guarded(topo)` | `den ≤ EPS → flat line at mean` |
| `L_opp(t) = a_o·t + b_o` | opposing line carrying the stop | §5 `lsq_fit_guarded(swings_opp)` | missing → DET-09; `den ≤ EPS → flat` |
| `topo_candles` | touchpoint indices on `L_trend`, **strictly before `t0`** | §4 grow+re-fit; `last_touch < t0` assert | dedup = one swing-touch |
| `entry_candle` `t0` | first close with `sign·(c − L_trend) > 0` after validation | §6 break test (strict `>`) | first-break check over `(last_touch, t0)` |
| `R0` | `abs(close[t0] − L_opp(t0))` | §8, after `L_opp` confirmed | `R0 ≤ 0 → DET-09 R0_nonpos` |
| `take_profit_level` | `close[t0] + direction · R0` | §9 emit | derived from guarded `R0` |
| `time_barrier_candle` | `t0 + H` (`H=24`) | §9 emit | integer index arithmetic |

**Invariants (§3) satisfied:** (1) line validated by `≥ MIN_TOUCHES=2` touches before `t0` — §4;
(2) `entry_candle` = first close breaking `L_trend` (close-based) — §6; (3) `L_opp` exists before `t0` —
§5; (4) all fits use only candles `≤ t0` — §0/§3/§5; (5) DET-09 rejects+counts `R0 ≤ 0`, `ATR(t0) ≤ 0`,
missing `L_opp` — §8.

**Downstream (L7) handshake.** The emitted objects are exactly what the transformer needs at `t0`:
`L_trend(t0)`/`L_opp(t0)` feed `distance_to_trend_line`, `distance_to_opposing_line`,
`risk_if_entered_pct`; `R0`/`take_profit_level`/`L_opp(t)`-moving feed the triple-barrier label;
`time_barrier_candle = t0+H` is the time barrier; `closed_through_line(t0) = 1` by construction (audit
invariant). ATR enters L6 only as the touch-tolerance scale and the DET-09 guard — **never** a barrier
(no ATR↔label coupling).

---

## 12. L8 thresholds & summary.json (where DET-09 lands)

The detector contributes the `setups_total` and `det09_rejected` counters to the L8 dashboard. For
completeness, the L8 aggregation that consumes them (these are L8 thresholds, reproduced here so the
detector's audit output is interpretable):

- **FAIL `>0`** (any one → dashboard FAIL → **L9 blocked**): in-session gaps; filled gaps; duplicate
  `(symbol, ts)`; prices `≤ 0`; NaN/Inf in Output B (undocumented); **parity mismatch on any of**
  `zip→DuckDB→parquet→Output B`.
- **WARN `>0.5%` / FAIL `>2%`**: `volume = 0` bars; zero-range `high == low` bars.
- **WARN `>20%`, never FAIL (diagnostic)**: **DET-09 rejection rate** = `det09_rejected /
  max(1, setups_total + det09_rejected)` (guarded denominator, ε-equivalent integer guard).
- **Aggregation**: any FAIL → dashboard FAIL → L9 blocked; WARN with no FAIL → proceed.

The detector contributes to the canonical `reports/quality/summary.json` (full schema in `quality_gate_spec_eng.md`): it populates the counters `setups_total` and `det09_rejected`, the `parities.parquet_outputB` flag, and the `DET-09` check (rejection rate vs `det09_rejected_warn_fraction`).

---

## 13. What is canonical vs. reference design (one valid realization)

- **Canonical (contract, do not change in F2):** the §3 output objects and their definitions;
  `MIN_TOUCHES=2`; `H=24`; `W_ATR=14`; `ATR_VARIANT=wilder`; `PRICE_VIEW=raw_usd_view`; `EPS=1e-9`;
  the five §3 invariants and DET-09; close-based, strict-`>` break; touches strictly before `t0`.
- **Reference design (one valid realization — F2 may replace):** `k=3` pivots with `i+3` confirmation;
  `TOUCH_TOL=0.25×ATR`; `LOOKBACK=120`; the "2 most-recent swings → grow → single re-fit" fitting
  policy; `COOLDOWN=H=24`; the `line_id` rounding used for dedup; the worked numeric examples.

Any F2 algorithm that emits the §3 objects, honors the five invariants, stays causal (candles `≤ t0`),
and feeds DET-09 the three rejection reasons is a conforming detector — the model only sees the L7 feature
rows it produces, so the geometry is swappable behind the output contract.

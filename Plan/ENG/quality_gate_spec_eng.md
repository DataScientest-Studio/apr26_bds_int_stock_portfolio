# quality_gate_spec_eng.md — L8 Quality Gate (concrete spec)

> **Scope.** This document specifies the **L8 quality gate** of **Pipeline A** (the S&P 500 strategy, layers L1–L10). L8 sits *between* L7 (Features X + label Y → Output B) and L9 (Optuna → XGBoost). It **measures and reports; it fixes nothing** — fixes belong to the source layers (L2–L7). Its single contract with L9 is binary: a **FAIL** anywhere closes the gate and **training (L9) does not start**.
>
> **Threshold provenance.** The master contract (`docs/SPEC.md`, v1.2) defers the *numeric thresholds* of L8 to roadmap item **F4b**. Every threshold and every invented structural choice in this document is therefore labelled **reference design (one valid realization)**. The *set* of counters/parities, the FAIL-on-any-mismatch parity rule, and the gate aggregation rule are **not** invented — they come from the glossary (L8) and the build contract (`build_contract_eng.md` §Outputs). Canonical terms (DuckDB, VIEW `ohlcv_1h`, QC-01…QC-11, PF · Sharpe · MDD · TIM · WR, ATR = Wilder, warm-up, triple barrier, `raw_usd_view`) are used verbatim per `ENG/glossary_eng.md`.
>
> **Two pipelines, never conflated.** **Pipeline A** = the L1–L10 strategy pipeline this gate guards. **Pipeline B** = the OHLCV → L5 feature DAG (its own layer scheme L0–L5). L8 is a Pipeline A artifact. Pipeline B appears here only as an **optional upstream-parity add-on** (§7) to the core Pipeline-A gate.
>
> **Certified scope.** The package certifies Pipeline A end-to-end (the detector is a *reference implementation* of the §3 output contract) + Pipeline B **L0–L5**. **L8 is Pipeline A's gate**; the Pipeline-B upstream-parity checks (§7) are an **optional add-on**, not required for the core Pipeline-A gate (this is a gate-scope boundary, not a certification boundary).

---

## 1. What L8 measures — counters and parities

L8 reads the *whole* upstream flow once, in one pass, and emits a fixed set of **counters** (single integers) and **parities** (paired counts that must match). The validation surface ties directly to the **QC-01…QC-11** load gates of L3 and to the **parity chain** `zip → DuckDB → parquet → Output B`.

### 1.1 The parity chain (zip → DuckDB → parquet → Output B)

Each hop is a store boundary; L8 re-counts both sides and asserts equality. **A parity is a pair of integers; the check passes iff the two integers are exactly equal.** No tolerance.

| Hop | Left store | Right store | What is compared | v1 reference target |
|---|---|---|---|---|
| **P1** `zip → DuckDB` | L2 LEAN ZIP store (510 zip = 503 universe + non-constituents) | L3 `raw_ohlcv_1h` table loaded into DuckDB | total row count **and** symbol count after the per-symbol upsert (DELETE-then-INSERT) | 8 841 820 rows · 503 symbols |
| **P2** `DuckDB → parquet` | L3 DuckDB (via `VIEW ohlcv_1h`, USD) | L4 `parquet/<TICKER>/ohlcv.parquet` (atomic snapshot materialization) | number of parquet files **and** per-ticker row count (parity per ticker) | 503 files; per-ticker row equality |
| **P3** `parquet → Output B` | L4 parquet OHLCV per ticker | L7 Output B (training matrix, one row per setup) | for each `{asset_id} × {direction}` partition: the number of setups emitted vs. the number of detector entries surviving DET-09 (audit R4) | per-partition setup-count equality |

> P1/P2 numbers (8 841 820 / 503 / 503 files) are **source facts** from `ENG/glossary_eng.md` (L3, L4), **not** reference design. P3 has no fixed numeric target — it is a structural equality (counts derived at build time), so its target is "exact match per partition", not a literal.

### 1.2 The QC-01…QC-11 tie-in

L3 already enforces QC-01…QC-11 on **every load** (a load that fails QC is not published). L8 **re-derives** the QC-relevant population counts from the published parquet/Output B so the dashboard restates them as gate items rather than trusting the upstream load alone (defense in depth). The mapping:

| QC gate | Statement (verbatim from glossary L3) | L8 counter / parity it feeds |
|---|---|---|
| QC-01 | `high ≥ low` | implied by `zero_range_bars` (high==low) + an internal `high<low` assertion (must be 0) |
| QC-02 | `high ≥ max(o,c) · low ≤ min(o,c)` | internal assertion (must be 0 violations) |
| QC-03 | no duplicate `(symbol, ts)` | `duplicates` counter |
| QC-04 | zero NULL in o/h/l/c/v | folded into `nan_inf_outputB` discipline + a raw-null assertion (must be 0) |
| QC-05 | prices > 0 | `prices_nonpos` counter |
| QC-06 | volume ≥ 0 | `volume_zero_bars` counter (volume==0 is the boundary; negative volume = hard internal assert 0) |
| QC-07 | universe 503/503 | `symbols` counter + parity **P1** symbol side |
| QC-08 | candles/day ∈ [5,9] | feeds the in-session gap logic (`gaps_in_session`) |
| QC-09 | ts within session 09:00–16:00 ET | feeds `gaps_in_session` (out-of-session ts ⇒ session-boundary violation) |
| QC-10 | ts strictly increasing per symbol | feeds `gaps_in_session` / `duplicates` (non-increasing ts) |
| QC-11 | date range and counters match `_meta` | feeds `inputs_hash` + parity **P1** row side |

### 1.3 The counter catalogue (the populations L8 counts)

| Counter (matches `summary.json` key) | Definition | QC / source tie |
|---|---|---|
| `rows` | total OHLCV rows seen across the published parquet | P1, QC-11 |
| `symbols` | distinct `asset_id` present | P1, QC-07 |
| `parquet_files` | count of `parquet/<TICKER>/ohlcv.parquet` | P2, glossary L4 (503) |
| `setups_total` | total setups emitted into Output B across all `{asset × direction}` partitions | P3, L7 |
| `det09_rejected` | setups rejected by the DET-09 invariant (`R0 ≤ 0`, `ATR(t0) ≤ 0`, or missing `L_opp`) and counted in the detector audit | glossary L6 DET-09 |
| `gaps_in_session` | missing in-session 1h candles (gaps *inside* RTH 09:00–16:00 ET) | QC-08/09/10 |
| `gaps_filled` | candles that were synthetically filled (must be 0 — the pipeline fills nothing) | glossary L8 "filled gaps = 0" |
| `volume_zero_bars` | candles with `volume == 0` | QC-06 |
| `zero_range_bars` | candles with `high == low` (zero-range) | QC-01 |
| `prices_nonpos` | candles with any price `≤ 0` | QC-05 |
| `duplicates` | duplicate `(symbol, ts)` pairs | QC-03/10 |
| `nan_inf_outputB` | NaN/Inf values in Output B beyond the **documented** exceptions (`build_contract_eng.md` §Outputs) | `build_contract_eng.md` §Outputs, §Definition of Done |

> **Documented Output-B exceptions (do NOT count toward `nan_inf_outputB`).** Per the Output-B contract (`build_contract_eng.md` §Outputs) the only sanctioned non-finite is `volume_z_score = NaN` when an asset has no volume **and** carries the explicit volume-missing flag. For the S&P 500 universe, volume is *required* (missing volume is itself a hard QC fail upstream), so in v1 this exception is expected to be empty. Every other NaN/Inf is undocumented and counts.

> **Why `det09_rejected` is diagnostic, not a fail.** DET-09 rejections are the detector *working as designed* (it must reject and **count**, never silently drop). A high rate signals a weak setup population or a mis-tuned detector, so L8 surfaces it as a **WARN-only** diagnostic (§2) — it can never FAIL the gate.

---

## 2. Counter → WARN/FAIL threshold table (fixed values)

All thresholds below are **reference design (one valid realization)** — `docs/SPEC.md` defers the numbers to F4b. They are fixed here so the gate is buildable today; F4b may re-pin them in `config/params.json` (the only configuration site), but the *comparison operators and the structure are frozen*.

| # | `check.id` | Counter / parity | OK iff | WARN iff | FAIL iff | Severity ceiling |
|---|---|---|---|---|---|---|
| 1 | `gaps_in_session` | `gaps_in_session` | `== 0` | — | `> 0` | FAIL |
| 2 | `gaps_filled` | `gaps_filled` | `== 0` | — | `> 0` | FAIL |
| 3 | `duplicates` | `duplicates` | `== 0` | — | `> 0` | FAIL |
| 4 | `prices_nonpos` | `prices_nonpos` | `== 0` | — | `> 0` | FAIL |
| 5 | `nan_inf_outputB` | `nan_inf_outputB` (undocumented only) | `== 0` | — | `> 0` | FAIL |
| 6 | `parity_zip_duckdb` | parity **P1** (rows + symbols) | both sides equal | — | any mismatch | FAIL |
| 7 | `parity_duckdb_parquet` | parity **P2** (files + per-ticker rows) | all equal | — | any mismatch | FAIL |
| 8 | `parity_parquet_outputB` | parity **P3** (per-partition setup count) | all equal | — | any mismatch | FAIL |
| 9 | `volume_zero_bars` | `volume_zero_bars` as a fraction of `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL |
| 10 | `zero_range_bars` | `zero_range_bars` as a fraction of `rows` | `≤ 0.5%` | `> 0.5%` and `≤ 2%` | `> 2%` | FAIL |
| 11 | `det09_rejected` | `det09_rejected / max(1, setups_total + det09_rejected)` (rejection rate) | `≤ 20%` | `> 20%` | never | **WARN max** |

**Fixed numeric constants (reference design):**
- `gaps_in_session`, `gaps_filled`, `duplicates`, `prices_nonpos`, `nan_inf_outputB`: **FAIL > 0** (zero-tolerance).
- Parity P1/P2/P3: **FAIL on any mismatch** (this rule is from the contract, not reference design).
- `volume_zero_bars`: **WARN > 0.5%**, **FAIL > 2%**.
- `zero_range_bars`: **WARN > 0.5%**, **FAIL > 2%**.
- `det09_rejected` rate: **WARN > 20%**, **never FAIL** (diagnostic).

**Zero-denominator guards (mandatory, ε = 1e-9):**
- **Fraction checks (#9, #10):** `fraction = volume_zero_bars / max(1, rows)`. If `rows == 0` the denominator guard yields `0` (no division by zero) — and an empty store is independently caught by parity **P1** FAIL, so the gate still closes.
- **DET-09 rate (#11):** `rate = det09_rejected / max(1, setups_total + det09_rejected)`; `den = 0 → 0`. Using `max(1, …)` (not `max(ε, …)`) because the denominator is an integer count; the `1` floor is the integer analogue of the ε-guard and keeps the rate in `[0,1]`.
- **Any internal ratio that can hit a zero denominator uses `max(ε, …)` with ε = 1e-9** (same constant as `body_to_range_ratio` and VWAP/ADX guards elsewhere in the spec).

**Threshold comparison precision.** Fractions are compared as floating-point; the WARN/FAIL bands use strict `>` at the lower edge and `≤` at the OK edge, so the bands are disjoint and exhaustive over `[0,1]`.

---

## 3. `reports/quality/summary.json` — fixed field schema

`summary.json` is the **single source of truth** for the gate: counters + per-check statuses + the input hash. The dashboard (§5) is a pure render of this file. The schema is **frozen**; a schema change is a hard fail of the build (bump `schema_version`).

```jsonc
{
  "schema_version": "1.0",                 // string (semver of THIS schema; reference design)
  "built_at_utc": "2026-06-15T00:00:00Z",  // string, ISO-8601 UTC (RFC 3339, 'Z' suffix)
  "inputs_hash": "<hex>",                  // string, hex digest over the upstream artifact set
                                           //   (zip set + duckdb file + parquet tree + Output B);
                                           //   ties to QC-11 (_meta counters) — repeatable input identity
  "counters": {
    "rows":               8841820,         // int  (>= 0)  — total OHLCV rows (P1)
    "symbols":            503,             // int  (>= 0)  — distinct asset_id (P1, QC-07)
    "parquet_files":      503,             // int  (>= 0)  — parquet/<TICKER>/ohlcv.parquet count (P2)
    "setups_total":       0,               // int  (>= 0)  — setups emitted into Output B (P3)
    "det09_rejected":     0,               // int  (>= 0)  — DET-09 rejections (audit)
    "gaps_in_session":    0,               // int  (>= 0)  — in-session 1h gaps
    "gaps_filled":        0,               // int  (>= 0)  — synthetically filled candles (must be 0)
    "volume_zero_bars":   0,               // int  (>= 0)  — volume==0 bars
    "zero_range_bars":    0,               // int  (>= 0)  — high==low bars
    "prices_nonpos":      0,               // int  (>= 0)  — price<=0 bars
    "duplicates":         0,               // int  (>= 0)  — duplicate (symbol, ts) pairs
    "nan_inf_outputB":    0                // int  (>= 0)  — undocumented NaN/Inf in Output B
  },
  "parities": {
    "zip_duckdb_rows":    true,            // bool — P1 rows+symbols equal
    "duckdb_parquet_files": true,          // bool — P2 files+per-ticker rows equal
    "parquet_outputB":    true             // bool — P3 per-partition setup counts equal
  },
  "checks": [                              // array; ONE object per gate item (§2, ids 1..11)
    {
      "id":        "gaps_in_session",      // string — stable check id (matches §2 check.id)
      "level":     "OK",                   // string enum: "OK" | "WARN" | "FAIL"
      "value":     0,                      // number — the measured value (int counter or float fraction)
      "threshold": "FAIL>0",               // string — human-readable threshold expression (the §2 rule)
      "desc":      "In-session 1h gaps (QC-08/09/10); zero-tolerance."  // string
    }
    // ... one entry for every check id 1..11 ...
  ],
  "overall_status": "OK"                   // string enum: "OK" | "WARN" | "FAIL" (the aggregation, §4)
}
```

### 3.1 Field types (frozen)

| Field | Type | Constraint |
|---|---|---|
| `schema_version` | string | semver; current `"1.0"` (reference design) |
| `built_at_utc` | string | ISO-8601 / RFC 3339, UTC, `Z` suffix |
| `inputs_hash` | string | lowercase hex digest of the upstream artifact set |
| `counters.*` | int | each `≥ 0` |
| `parities.zip_duckdb_rows` | bool | `true` ⇔ P1 equal |
| `parities.duckdb_parquet_files` | bool | `true` ⇔ P2 equal |
| `parities.parquet_outputB` | bool | `true` ⇔ P3 equal |
| `checks[]` | array of objects | exactly one per check id 1..11 |
| `checks[].id` | string | one of the §2 `check.id` values |
| `checks[].level` | string enum | `"OK"` \| `"WARN"` \| `"FAIL"` |
| `checks[].value` | number | int counter or float fraction (fractions in `[0,1]`) |
| `checks[].threshold` | string | the §2 rule, verbatim (e.g. `"WARN>0.5%; FAIL>2%"`) |
| `checks[].desc` | string | one-line human description |
| `overall_status` | string enum | `"OK"` \| `"WARN"` \| `"FAIL"` |

> **`value` for parity checks.** A parity check's `value` is `0` when matched and `1` when any mismatch is found (the count of mismatched units); its `level` is `OK` (`value==0`) or `FAIL` (`value>0`). This keeps `value` a number for *every* check entry.

---

## 4. Gate aggregation rule

The gate reduces the eleven `checks[].level` values to one `overall_status`, then maps that to a go/no-go for L9.

**Aggregation (precedence FAIL > WARN > OK):**

```text
if any check.level == "FAIL":   overall_status = "FAIL"
elif any check.level == "WARN": overall_status = "WARN"
else:                           overall_status = "OK"
```

**Gate decision (the binding contract with L9):**

| `overall_status` | Dashboard | L9 (Optuna → XGBoost training) |
|---|---|---|
| `FAIL` | **FAIL** (red) | **BLOCKED** — training does not start |
| `WARN` | **WARN** (amber) | **PROCEED** — training starts; WARNs are surfaced but non-blocking |
| `OK` | **OK** (green) | **PROCEED** — training starts |

**Rules made explicit:**
- **any FAIL → dashboard FAIL → L9 blocked.** A single FAILing item closes the gate regardless of all other items.
- **WARN (no FAIL) → proceed.** WARNs (including a `volume_zero_bars`/`zero_range_bars` band hit, or a `det09_rejected` rate over 20%) do **not** block training; they are recorded for the analyst.
- **`det09_rejected` can never raise `overall_status` to FAIL** (its severity ceiling is WARN, §2 #11) — by construction it can only ever contribute a WARN.
- The decision is consumed by L9's start condition ("green/amber L8 dashboard before training"). L9 reads `overall_status` from `summary.json`, not the HTML.

---

## 5. `reports/quality/dashboard.html`

`dashboard.html` is generated **from `summary.json`** and is **fully self-contained**: zero external dependencies, no network fetch, no JS framework, all CSS inlined — it opens correctly from a file path with no server. It is a *render*, never a source of truth (regenerating it from the same `summary.json` is deterministic).

**Contents (reference design layout):**
- **Header banner** showing `overall_status` as a single large badge — green **OK**, amber **WARN**, or red **FAIL** — plus `built_at_utc` and a short `inputs_hash` prefix.
- **One row per check** (the 11 items of §2), each rendered with its own **OK / WARN / FAIL** chip, the `id`, the measured `value`, the `threshold` string, and the `desc`. Rows are ordered exactly as the §2 table (FAIL-tier counters first, parities, then the rate diagnostics).
- **Counters block** echoing every `counters.*` value (the populations behind the checks), and a **parities block** showing P1/P2/P3 as pass/mismatch.
- **Gate verdict line** restating the §4 mapping in plain English, e.g. *"FAIL → L9 training blocked"* or *"OK → L9 may start"*.

> The dashboard intentionally shows the **per-item** status (not just the aggregate) so an analyst sees *which* counter failed and by how much, without opening the JSON. The aggregate badge and the per-item chips are both derived from the same `checks[]` array, so they can never disagree.

---

## 6. Worked example of the OK path (reference values)

For the canonical S&P 500 build with a clean upstream:

- `counters`: `rows = 8 841 820`, `symbols = 503`, `parquet_files = 503`, `gaps_in_session = 0`, `gaps_filled = 0`, `duplicates = 0`, `prices_nonpos = 0`, `nan_inf_outputB = 0`.
- `parities`: P1 `true`, P2 `true`, P3 `true`.
- `volume_zero_bars` and `zero_range_bars` each `≤ 0.5%` of `rows` → both `OK`.
- `det09_rejected` rate `≤ 20%` → `OK` (or `WARN` if higher, never FAIL).
- Aggregation: no FAIL, no WARN → `overall_status = "OK"` → dashboard **OK** → **L9 proceeds**.

If, say, `gaps_in_session = 3`: check #1 `level = FAIL` → `overall_status = "FAIL"` → dashboard **FAIL** → **L9 blocked**, regardless of every other green item.

---

## 7. Optional add-on — upstream Pipeline B parity checks

**Optional add-on to the core Pipeline-A L8 gate.** The core L8 gate measures the Pipeline A chain (§1). When the strategy consumes engineered features from **Pipeline B** (the OHLCV → L5 feature DAG, `qc_raw_ohlcv_data_sp500_alpaca_transforms`), L8 can additionally run **upstream-parity** checks against the Pipeline B materialization. These add-on checks are optional and do not affect the core Pipeline-A gate result.

**Pipeline B grids (REAL, from the `qc-transforms` structure materialization):**
- 1h rolling windows `n ∈ {5, 10, 20, 50}`; 1d windows `{20, 200}`.
- lag `k = 1`; regime quantiles `[0.33, 0.66]`; volume-z thresholds `[−1.0, 1.0]`.
- native bar `1h`; the only resample is `1h → 1d` (5m/15m are finer than the native bar); session phases are 1h-adapted.

**Pipeline B L4 reference (textbook + guards):** `RSI_n` (Wilder), `MACD(12,26,9)`, canonical `l4_atr = mean_n(TR)` (ADX may use an internal Wilder-smoothed TR for ±DI — **not** the canonical `l4_atr`), `OBV`, `ADL`, `Stoch_n`, `ADX` with `DX = 100·|+DI − −DI| / max(ε, +DI + −DI)` and `ADX = Wilder_smooth(DX, n)`, `MFI_n`, `VWAP = Σ(TP·V) / max(ε, ΣV)` — **ε = 1e-9** on every denominator.

**Pipeline B L5 reference:** PCA (sklearn, `n_components=8`, fit Train-only on standardized `X_raw`, persist `components_`/`mean_`/`explained_variance_` via joblib, transform = project); DWT (pywt `wavedec`, wavelet `db4`, `level=3`, rolling window `W=64`, causal, output = per-level energy); Autoencoder (MLP, encoder dims `[64,32,8]`, ReLU, MSE, Adam, 50 epochs, fit Train-only, persist torch `state_dict`, transform = encoder); Sequence (LSTM `hidden=32`, 1 layer, input window = 24 bars of `X_raw`, output = last hidden `h_t ∈ R^32`, persist `state_dict`). **All L5: fit scope = Train only (no leakage); transform API = `transform(X) -> features`.**

**Optional upstream-parity checks (add-on to the core Pipeline-A L8 gate; enable for certified Pipeline-B outputs):**
- **PB-row parity:** Pipeline B feature-parquet row count per `{asset, native_bar}` equals the L4 Pipeline A parquet row count for the same ticker (one engineered row per native 1h candle).
- **PB-resample parity:** the count of `1d` rows equals the count of distinct session days derived from the `1h` series (no orphan resampled bars).
- **PB-fit-scope assertion (anti-leakage, FAIL-on-violation):** every L4 indicator and every L5 representation was fit on **Train only**; any artifact whose fit window overlaps OOS = FAIL. (This mirrors Pipeline A's OOS-guard discipline.)
- **PB-finite check:** no undocumented NaN/Inf in the engineered columns after the ε-guards above; the only sanctioned NaN is the volume-missing case, identical to §1.3.

These add-on checks would each get their own `checks[]` entry with the same `{id, level, value, threshold, desc}` shape and feed the same §4 aggregation; enable them once the Pipeline B materialization includes the layers being checked.

---

## 8. Build invariants (DoD restated for L8)

- L8 **never mutates** upstream stores; it only reads and writes `reports/quality/summary.json` + `reports/quality/dashboard.html`.
- `summary.json` is written **before** `dashboard.html`; the HTML is a deterministic render of the JSON (same JSON → same HTML).
- Every divisor in §2 uses an explicit guard (`max(1, …)` for integer counts, `max(ε, …)` with **ε = 1e-9** for floats; `den = 0 → 0`).
- The gate is **binary toward L9**: `overall_status` is the only field L9 reads to decide go/no-go.
- All thresholds live in `config/params.json` (the `l8` block — the single configuration site); the operators and schema in this document are frozen. The *numbers* are **reference design (one valid realization)** pending F4b.

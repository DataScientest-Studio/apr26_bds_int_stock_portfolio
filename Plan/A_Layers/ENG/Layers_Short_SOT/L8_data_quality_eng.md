# L8 · Data-quality gate (SOT)

A quality gate before training: one dashboard summarizes the quality of the whole flow (L2–L7). It
**measures and reports; it fixes nothing** (fixes belong to the source layers). Single contract with L9:
any **FAIL** closes the gate and **training (L9) does not start**. This file owns the counters, the parity
chain, the `summary.json` schema and the aggregation rule; the numeric WARN/FAIL bands are owned by
[00_parameters_eng.md](00_parameters_eng.md) (the `l8` block).

## Parity chain (zip → DuckDB → parquet → Output B)

Each hop is a store boundary; both sides are re-counted and asserted **exactly equal** (no tolerance).

| Hop | Compared | v1 reference target |
|---|---|---|
| **P1** `zip → DuckDB` | total row count **and** symbol count | 8 841 820 rows · 503 symbols |
| **P2** `DuckDB → parquet` | parquet file count **and** per-ticker row count | 503 files; per-ticker row equality |
| **P3** `parquet → Output B` | per `{asset_id}×{direction}`: setups emitted vs detector entries surviving DET-09 (audit R4) | per-partition setup-count equality |

## Counter catalogue (the populations L8 counts)

| Counter (`summary.json` key) | Definition | QC / source tie |
|---|---|---|
| `rows` | total OHLCV rows across the published parquet | P1, QC-11 |
| `symbols` | distinct `asset_id` present | P1, QC-07 |
| `parquet_files` | count of `parquet/<TICKER>/ohlcv.parquet` | P2 |
| `setups_total` | setups emitted into Output B across all partitions | P3 |
| `det09_rejected` | setups rejected by DET-09 (`R0 ≤ 0`, `ATR(t0) ≤ 0`, or missing `L_opp`) | [L6](L6_setup_detector_eng.md) DET-09 |
| `gaps_in_session` | missing in-session 1h candles (inside RTH 09:00–16:00 ET) | QC-08/09/10 |
| `gaps_filled` | synthetically filled candles (must be 0 — the pipeline fills nothing) | — |
| `volume_zero_bars` | candles with `volume == 0` | QC-06 |
| `zero_range_bars` | candles with `high == low` | QC-01 |
| `prices_nonpos` | candles with any price `≤ 0` | QC-05 |
| `duplicates` | duplicate `(symbol, ts)` pairs | QC-03/10 |
| `nan_inf_outputB` | NaN/Inf in Output B beyond the documented exceptions | [L7](L7_features_x_label_y_eng.md) |

**Documented Output-B exception (does NOT count):** `volume_z_score = NaN` when an asset has no volume **and**
carries the explicit volume-missing flag. For the S&P 500 universe volume is required, so in v1 this is
empty. Every other NaN/Inf counts.

## Checks (11 items) → thresholds

Each check has an `id`, a measured `value`, and an `OK/WARN/FAIL` level. The numeric bands and the
zero-denominator guards are owned by [00_parameters_eng.md](00_parameters_eng.md) (`l8` block). Summary of
severity ceilings:

- Zero-tolerance FAIL `> 0`: `gaps_in_session`, `gaps_filled`, `duplicates`, `prices_nonpos`, `nan_inf_outputB`.
- Parity P1 / P2 / P3: FAIL on any mismatch (this rule is from the contract, not reference design).
- Fraction-of-`rows` bands: `volume_zero_bars`, `zero_range_bars` (WARN/FAIL bands per 00_parameters).
- `det09_rejected` rate: **WARN-only diagnostic** (never FAIL).

## `reports/quality/summary.json` — frozen field schema

`summary.json` is the single source of truth for the gate (counters + per-check statuses + input hash); the
HTML dashboard is a pure render of it. Schema frozen; a change bumps `schema_version`.

```jsonc
{
  "schema_version": "1.0",                 // semver of THIS schema
  "built_at_utc": "<ISO-8601 UTC, 'Z'>",   // string
  "inputs_hash": "<lowercase hex>",        // digest over zip set + duckdb + parquet tree + Output B (ties QC-11)
  "counters": {                            // each int >= 0
    "rows": 8841820, "symbols": 503, "parquet_files": 503,
    "setups_total": 0, "det09_rejected": 0,
    "gaps_in_session": 0, "gaps_filled": 0,
    "volume_zero_bars": 0, "zero_range_bars": 0,
    "prices_nonpos": 0, "duplicates": 0, "nan_inf_outputB": 0
  },
  "parities": {                            // bool; true ⇔ equal
    "zip_duckdb_rows": true,
    "duckdb_parquet_files": true,
    "parquet_outputB": true
  },
  "checks": [                              // exactly one object per check id 1..11
    { "id": "gaps_in_session", "level": "OK", "value": 0,
      "threshold": "FAIL>0", "desc": "In-session 1h gaps (QC-08/09/10); zero-tolerance." }
    // ... ids 2..11 ...
  ],
  "overall_status": "OK"                   // "OK" | "WARN" | "FAIL"  (the aggregation below)
}
```

A parity check's `value` is `0` when matched, `1` when any mismatch (so `value` is a number for every check).

## Gate aggregation rule

```text
if any check.level == "FAIL":   overall_status = "FAIL"
elif any check.level == "WARN": overall_status = "WARN"
else:                           overall_status = "OK"
```

| `overall_status` | L9 (Optuna → XGBoost) |
|---|---|
| `FAIL` | **BLOCKED** — training does not start |
| `WARN` | **PROCEED** — WARNs surfaced but non-blocking |
| `OK` | **PROCEED** |

- Any FAIL → dashboard FAIL → L9 blocked, regardless of all other items.
- `det09_rejected` can never raise `overall_status` to FAIL (severity ceiling WARN).
- L9 reads `overall_status` from `summary.json`, not the HTML.
- `reports/quality/dashboard.html` is a self-contained (zero-dependency) deterministic render of `summary.json`.

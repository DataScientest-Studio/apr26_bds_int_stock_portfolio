# 00 · Input contract (SOT)

Canonical home for the OHLCV table contract the whole pipeline operates on. A single OHLCV table per
Asset, **sorted ascending by time**, with **no gaps inside a session**.

## Table schema (columns, types, invariants)

| Column | Type | Invariant / note |
|---|---|---|
| `timestamp` | datetime (UTC, tz-aware) | step = `TF`; UTC tz-aware — the naive-ET→UTC conversion is performed only by the F1 reader at the read boundary |
| `open` | float | — |
| `high` | float | high/low integrity enforced by QC-02 |
| `low` | float | high/low integrity enforced by QC-02 |
| `close` | float | — |
| `volume` | float, `≥ 0` | S&P 500 universe: **volume required; missing volume = hard fail QC**. Generic path for Assets without volume → `volume_z_score = NaN` with an explicit flag |

The cross-bar integrity invariants (QC-01, QC-02) and the full QC-01…QC-11 predicate set are owned by
[L3_duckdb_raw_view_qc_eng.md](L3_duckdb_raw_view_qc_eng.md).

## Input metadata (manifest — NOT table columns)

| Field | Type | Note |
|---|---|---|
| `price_view` | string | the named input price view. **v1 value = `raw_usd_view`** (the DuckDB `VIEW ohlcv_1h` in USD, prices = `raw/<!--na:price_scale-->10000<!--/na-->.0`). Required for repeatability. **One value per dataset** (snapshot manifest), never a per-row column |

The canonical source of the contract is `VIEW ohlcv_1h` (USD) materialized to one
`<TICKER>/<TICKER>_ohlcv_1h.parquet` per ticker (<!--na:universe_size-->503<!--/na--> files, `zstd`). The contract stays source-independent:
any table satisfying the schema above is a valid input. Corporate-actions policy is out of scope for v1
(open risk R1).

## Naive-ET → UTC-at-F1-reader rule

In the LEAN ZIP archive (L2), timestamps are stored as **naive ET** (`America/New_York`, no timezone). The
conversion **naive ET → UTC tz-aware is performed only by the F1 reader at the read boundary** — never in
the archive, never as a table edit. Because DST changes occur outside the RTH session (09:00–16:00 ET), the
conversion is unambiguous. Downstream layers see only UTC tz-aware `timestamp`.

# L3 · DuckDB + VIEW ohlcv_1h + QC-01…QC-11 (SOT)

The canonical analytical database: raw integers in the table, USD in the view, quality-gated on every load.

- From the zips we load a single DuckDB database (file `*.duckdb`).
- The database holds the table `raw_ohlcv_1h` (verbatim data).
  - key columns: `symbol VARCHAR`, `ts TIMESTAMP`
  - price columns: `open/high/low/close BIGINT ×10000`
  - volume column: `volume BIGINT`
  - row count: 8 841 820
  - symbol count: 503 (ticker list: file `config/universe.txt`)
- USD exists only in the `VIEW ohlcv_1h` (= prices `/10000.0`).
  - this view is `price_view = raw_usd_view` (the named input price view; see [00_input_contract_eng.md](00_input_contract_eng.md))
  - the view does not copy data (zero storage duplication)
- The `_meta` table holds: `schema_version`, source, `built_at`, row/symbol counters.
- Per-symbol upsert works as DELETE-then-INSERT (uniqueness of `(symbol, ts)` guaranteed by the process + QC).
- Key numbers: 8 841 820 rows · 503 symbols · database 166 MB · range 2016-01-04 → rolling.

## QC-01…QC-11 (load gate predicates)

Every load passes 11 quality predicates; a load that fails any QC is **not published**.

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

A fail of any gate = the load is not published. The L8 dashboard ([L8](L8_data_quality_eng.md)) re-derives
the QC-relevant population counts from the published parquet / Output B (defense in depth).

# L2 · LEAN ZIP store (SOT)

A durable, compact archival store in LEAN format — the source of truth for rebuilding the database.

- The raw store is <!--na:lean_zip_count-->510<!--/na--> ZIP files.
  - name convention: `<ticker>.zip` (e.g. `aapl.zip`)
  - <!--na:lean_zip_count-->510<!--/na--> = the full ZIP inventory; the universe (<!--na:universe_size-->503<!--/na-->) is its quality-filtered subset (see `config/data_state_numbers.json` → `_universe_derivation`)
  - total size: <!--na:lean_zip_size_mb-->139<!--/na--> MB
  - one zip = the entire history of one ticker
- Each zip holds one CSV file without a header.
  - CSV row: `YYYYMMDD HH:MM,open,high,low,close,volume`
  - prices: integers ×<!--na:price_scale-->10000<!--/na--> (deci-cents; e.g. `$185.12 → 1851200`); zero floating-point errors in the archive
  - volume: integer (shares)
  - timestamps: naive ET (`America/New_York`), without a timezone
- We edit the zips only in append / replace-whole-ticker mode (never a partial edit inside the CSV).
- The zips are the source of truth: the database from [L3](L3_duckdb_raw_view_qc_eng.md) can be rebuilt from them in full.
- Price conversion to USD happens only in the database view ([L3](L3_duckdb_raw_view_qc_eng.md) `VIEW ohlcv_1h`).
- Time conversion naive-ET → UTC tz-aware happens only in the F1 reader (see [00_input_contract_eng.md](00_input_contract_eng.md)); F1 = function `ohlcv(ticker) -> DataFrame`.

# L2 · LEAN ZIP store (summary)

- The raw store is 510 ZIP files.
  - name convention: `<ticker>.zip` (e.g. `aapl.zip`)
  - 510 = 503 universe tickers + a few non-constituents
  - total size: 139 MB
  - one zip = the entire history of one ticker
- Each zip holds one CSV file without a header.
  - CSV row: `YYYYMMDD HH:MM,open,high,low,close,volume`
  - prices: integers ×10 000 (deci-cents)
  - volume: integer (shares)
  - timestamps: naive ET (America/New_York)
- We edit the zips only in append/replace-whole-ticker mode.
- The zips are the source of truth: the database from [L3](L3_duckdb_raw_view_qc_eng.md) can be rebuilt from them in full.
- Price conversion to USD happens only in the database view ([L3](L3_duckdb_raw_view_qc_eng.md)).
- Time conversion to UTC happens only in the F1 reader (F1 = function ohlcv(ticker) -> DataFrame)

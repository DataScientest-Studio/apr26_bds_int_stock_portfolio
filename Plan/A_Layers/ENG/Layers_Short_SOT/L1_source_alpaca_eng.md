# L1 · Source: Alpaca (SOT)

- We download sp500 data from the Alpaca exchange.
  - source: Alpaca Market Data API; `feed = sip` (consolidated tape, one authoritative quote source)
  - tool: QuantConnect LEAN (downloader CLI)
  - authorization: Alpaca API key only (headless, no OAuth)
- Incremental top-ups: every hour at `:05`.
  - method: REST (cron)
  - top-up lookback: ~5 days (upsert overwrites the tail of the series)
  - idempotent: re-running with the same window gives the same state
  - session guard: outside ET market hours (Mon–Fri) the cron does nothing (no-op)
- Download scope: the S&P 500 constituent set → <!--na:lean_zip_count-->510<!--/na--> tickers (one ZIP each → [L2](L2_lean_zip_store_eng.md)).
  - the <!--na:universe_size-->503<!--/na--> ML universe (`config/universe_tickers.txt`) is the **quality-filtered subset** applied downstream at [L3](L3_duckdb_raw_view_qc_eng.md) — data-completeness criteria (≥ 2 y history + gap coverage; 7 excluded); precise rule in `config/data_state_numbers.json` → `_universe_derivation`
  - interval: 1h candles, RTH session 09:00–16:00 ET only (~<!--na:candles_per_day_typical-->7<!--/na--> candles/day)
- Download result: ZIP files in LEAN format, one file per ticker.
- Prices arrive raw, with no split/dividend adjustments (adjustment = a deliberate decision of later layers; open risk R1 — corporate actions).
- The `volume` column is required; its absence = hard fail QC.
- Next layer: the zips become the LEAN store ([L2](L2_lean_zip_store_eng.md)).

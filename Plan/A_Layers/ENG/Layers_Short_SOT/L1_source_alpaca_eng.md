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
- Download scope: 503 S&P 500 tickers.
  - ticker list: file `config/universe.txt`
  - interval: 1h candles, RTH session 09:00–16:00 ET only (~7 candles/day)
- Download result: ZIP files in LEAN format, one file per ticker.
- Prices arrive raw, with no split/dividend adjustments (adjustment = a deliberate decision of later layers; open risk R1 — corporate actions).
- The `volume` column is required; its absence = hard fail QC.
- Next layer: the zips become the LEAN store ([L2](L2_lean_zip_store_eng.md)).

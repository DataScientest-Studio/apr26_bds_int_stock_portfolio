# L1 · Source: Alpaca (summary)

- We download sp500 data from the Alpaca exchange.
  - tool: QuantConnect LEAN (downloader CLI)
  - authorization: Alpaca API key
- Incremental top-ups: every hour at `:05`.
  - method: REST (cron)
  - top-up lookback: ~5 days (upsert overwrites the tail of the series)
  - outside session hours the cron does nothing (guard)
- Download scope: 503 S&P 500 tickers.
  - ticker list: file `config/universe.txt`
  - interval: 1h candles, session 09:00–16:00 ET only (~7 candles/day)

- Download result: ZIP files in LEAN format, one file per ticker
- Prices in the files are raw, with no adjustments
- The `volume` column is required; its absence = hard fail QC.

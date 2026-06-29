-- Canonical DuckDB schema for the active run's single analytical database
-- (liora.duckdb). The OHLCV + tickers tables are the source of truth; every
-- engineered feature is derived from `ohlcv` in src/features.sql, and every
-- model/portfolio artifact table is materialised by ingest_to_duckdb.py /
-- train_xgb_optuna.py / build_portfolios.sql.
--
-- adj_close is REQUIRED (split/dividend-adjusted close): data_loader.daily_return
-- and the whole EDA + feature pipeline are computed on it, not raw close.

CREATE TABLE IF NOT EXISTS ohlcv (
    date      DATE     NOT NULL,
    ticker    VARCHAR  NOT NULL,
    open      DOUBLE,
    high      DOUBLE,
    low       DOUBLE,
    close     DOUBLE,
    adj_close DOUBLE,
    volume    BIGINT,
    PRIMARY KEY (ticker, date)
);

CREATE TABLE IF NOT EXISTS tickers (
    ticker   VARCHAR PRIMARY KEY,
    name     VARCHAR,
    sector   VARCHAR,
    industry VARCHAR,
    "index"  VARCHAR,
    country  VARCHAR
);

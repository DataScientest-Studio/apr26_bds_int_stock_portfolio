-- Feature engineering in pure SQL — the supervised matrix for the model.
--
-- Reproduces the legacy pandas add_features() EXACTLY (verified by
-- tests/parity_features against models/train_xgboost_no_history_model.py):
-- momentum, annualized mean return, annualized volatility, liquidity,
-- 1-year drawdown, and the forward 63-day target. Every reader (training,
-- walk-forward) selects from this one view instead of recomputing in pandas.
--
-- pandas .rolling(N) uses min_periods=N (NaN until N valid observations); we
-- match it with `CASE WHEN COUNT(col) OVER w < N THEN NULL`. Sample std
-- (pandas ddof=1) -> STDDEV_SAMP. pct_change(N) -> adj_close / LAG(.,N) - 1.

CREATE OR REPLACE VIEW features AS
WITH base AS (
    SELECT
        date, ticker, adj_close, volume,
        adj_close / LAG(adj_close) OVER w - 1 AS daily_return
    FROM ohlcv
    WINDOW w AS (PARTITION BY ticker ORDER BY date)
),
feat AS (
    SELECT
        date, ticker, adj_close, volume, daily_return,
        adj_close / LAG(adj_close, 5)  OVER w - 1 AS ret_5d,
        adj_close / LAG(adj_close, 20) OVER w - 1 AS ret_20d,
        adj_close / LAG(adj_close, 60) OVER w - 1 AS ret_60d,
        CASE WHEN count(daily_return) OVER w20 < 20 THEN NULL
             ELSE avg(daily_return) OVER w20 * 252 END             AS mean_return_20d,
        CASE WHEN count(daily_return) OVER w60 < 60 THEN NULL
             ELSE avg(daily_return) OVER w60 * 252 END             AS mean_return_60d,
        CASE WHEN count(daily_return) OVER w20 < 20 THEN NULL
             ELSE stddev_samp(daily_return) OVER w20 * sqrt(252) END AS volatility_20d,
        CASE WHEN count(daily_return) OVER w60 < 60 THEN NULL
             ELSE stddev_samp(daily_return) OVER w60 * sqrt(252) END AS volatility_60d,
        CASE WHEN count(volume) OVER w20 < 20 THEN NULL
             ELSE avg(volume) OVER w20 END                         AS avg_volume_20d,
        CASE WHEN count(adj_close) OVER w252 < 60 THEN NULL
             ELSE adj_close / max(adj_close) OVER w252 - 1 END     AS drawdown_252d,
        LEAD(adj_close, 63) OVER w / adj_close - 1                 AS target_63d_return
    FROM base
    WINDOW
        w    AS (PARTITION BY ticker ORDER BY date),
        w20  AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19  PRECEDING AND CURRENT ROW),
        w60  AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN 59  PRECEDING AND CURRENT ROW),
        w252 AS (PARTITION BY ticker ORDER BY date ROWS BETWEEN 251 PRECEDING AND CURRENT ROW)
)
SELECT
    f.date, f.ticker,
    f.ret_5d, f.ret_20d, f.ret_60d,
    f.mean_return_20d, f.mean_return_60d,
    f.volatility_20d, f.volatility_60d,
    f.avg_volume_20d,
    ln(1 + f.avg_volume_20d) AS log_avg_volume_20d,
    f.drawdown_252d,
    f.daily_return,
    f.target_63d_return,
    t.sector, t.industry
FROM feat f
LEFT JOIN tickers t USING (ticker);

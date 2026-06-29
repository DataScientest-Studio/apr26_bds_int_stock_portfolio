-- Data-quality audit over the active run's ohlcv table (make audit).
-- Same KPIs the Streamlit Data Audit page computes, expressed in SQL.
WITH per_ticker AS (
    SELECT ticker, count(*) AS n FROM ohlcv GROUP BY ticker
)
SELECT
    (SELECT count(*) FROM ohlcv)                                              AS rows,
    (SELECT count(DISTINCT ticker) FROM ohlcv)                               AS tickers,
    (SELECT count(DISTINCT date) FROM ohlcv)                                 AS trading_dates,
    (SELECT min(date) FROM ohlcv)                                            AS date_min,
    (SELECT max(date) FROM ohlcv)                                            AS date_max,
    (SELECT count(*) FROM ohlcv
        WHERE high < low OR open > high OR open < low
           OR close > high OR close < low)                                   AS ohlc_violations,
    (SELECT count(*) FROM ohlcv WHERE volume = 0)                            AS zero_volume_rows,
    (SELECT count(*) FROM (SELECT ticker, date FROM ohlcv
        GROUP BY ticker, date HAVING count(*) > 1))                          AS duplicate_keys,
    min(n)                                                                   AS hist_min_days,
    CAST(median(n) AS BIGINT)                                                AS hist_median_days,
    max(n)                                                                   AS hist_max_days
FROM per_ticker;

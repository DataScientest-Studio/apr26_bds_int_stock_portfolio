-- Portfolio construction in pure SQL from the production model's rankings.
--
-- Builds 3 equal-weight, 10-stock, sector-capped portfolios (conservative /
-- balanced / aggressive) from model_rankings WHERE model_key='xgboost_no_history'.
--
-- Reproduces build_portfolios.py's greedy selection: "scan predicted-return desc,
-- take a stock if its sector has < floor(10*0.30)=3 picks". That is provably
-- equivalent to "keep each sector's top-3 (sector_rank<=3), then take the global
-- top-10 by predicted return" — a 4th-in-sector stock is never reachable, and the
-- greedy fills sectors in predicted order. The volatility cap (0.35/0.50/0.80) is
-- relaxed exactly when fewer than 10 sector-eligible names clear it.

CREATE OR REPLACE TABLE portfolio_recommendations AS
WITH params(profile, cap) AS (
    VALUES ('conservative', 0.35), ('balanced', 0.50), ('aggressive', 0.80)
),
prod AS (
    SELECT date, ticker, sector, industry, predicted_63d_return, volatility_60d, ret_60d
    FROM model_rankings WHERE model_key = 'xgboost_no_history'
),
cand AS (  -- only a sector's top-3 are ever selectable by the greedy
    SELECT date, ticker, sector, industry, predicted_63d_return, volatility_60d, ret_60d
    FROM (
        SELECT *, row_number() OVER (PARTITION BY sector ORDER BY predicted_63d_return DESC) AS sector_rank
        FROM prod
    )
    WHERE sector_rank <= 3
),
relax AS (  -- relax the vol cap when <10 sector-eligible names clear it
    SELECT p.profile, p.cap,
           count(*) FILTER (WHERE c.volatility_60d <= p.cap) < 10 AS relaxed
    FROM params p CROSS JOIN cand c
    GROUP BY p.profile, p.cap
),
elig AS (
    SELECT r.profile, r.relaxed,
           c.date, c.ticker, c.sector, c.industry,
           c.predicted_63d_return, c.volatility_60d, c.ret_60d
    FROM relax r CROSS JOIN cand c
    WHERE r.relaxed OR c.volatility_60d <= r.cap
),
ranked AS (
    SELECT *, row_number() OVER (PARTITION BY profile ORDER BY predicted_63d_return DESC) AS rank
    FROM elig
),
sized AS (
    SELECT *, 1.0 / count(*) OVER (PARTITION BY profile) AS weight
    FROM ranked WHERE rank <= 10
),
sector_sums AS (  -- separate aggregation avoids a window-over-window (DuckDB binder bug)
    SELECT profile, sector, sum(weight) AS sector_weight_after_selection
    FROM sized GROUP BY profile, sector
)
SELECT
    s.profile, s.rank, s.date, s.ticker, s.sector, s.industry, s.weight,
    s.predicted_63d_return, s.volatility_60d, s.ret_60d,
    ss.sector_weight_after_selection,
    s.relaxed AS volatility_cap_relaxed
FROM sized s JOIN sector_sums ss USING (profile, sector)
ORDER BY s.profile, s.rank;

CREATE OR REPLACE TABLE portfolio_summary AS
WITH descr(profile, description, ord) AS (
    VALUES
      ('conservative', 'Lower-volatility picks first; accepts lower expected return for a smoother ride.', 1),
      ('balanced',     'Middle risk profile; allows more volatile stocks but still filters extreme names.', 2),
      ('aggressive',   'Higher risk profile; allows high-volatility stocks if the model score is strong.', 3)
)
SELECT
    a.profile, d.description,
    a.date, a.stocks, a.equal_weight,
    a.expected_63d_return_weighted, a.avg_volatility_60d_weighted, a.avg_ret_60d_weighted,
    a.max_sector_weight, a.sectors, a.volatility_cap_relaxed
FROM (
    SELECT
        profile,
        max(date) AS date,
        count(*) AS stocks,
        min(weight) AS equal_weight,
        sum(predicted_63d_return * weight) AS expected_63d_return_weighted,
        sum(volatility_60d * weight) AS avg_volatility_60d_weighted,
        sum(ret_60d * weight) AS avg_ret_60d_weighted,
        max(sector_weight_after_selection) AS max_sector_weight,
        count(DISTINCT sector) AS sectors,
        bool_or(volatility_cap_relaxed) AS volatility_cap_relaxed
    FROM portfolio_recommendations GROUP BY profile
) a
JOIN descr d USING (profile)
ORDER BY d.ord;

CREATE OR REPLACE TABLE portfolio_sector_weights AS
SELECT profile, sector, sum(weight) AS weight
FROM portfolio_recommendations
GROUP BY profile, sector
ORDER BY profile, weight DESC;

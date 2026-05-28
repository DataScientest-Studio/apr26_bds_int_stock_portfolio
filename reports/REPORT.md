---
title: "Stock Portfolio Recommender"
subtitle: "Data Exploration, Pre-processing, Modeling & Defense"
author:
  - Gabriel Marchesan Almeida
  - Paweł Flak
  - Marcus Schürstedt
date: "\\today"
keywords: [machine learning, finance, portfolio, S&P 500, Alpaca, clustering, recommender]
subject: "Liora APR26 BDS INT — Data Scientist Capstone Project"
description: "End-to-end report covering data acquisition, exploration, pre-processing, modeling and conclusions for a beginner-friendly stock portfolio recommender."
lang: en

# --- Eisvogel template variables -------------------------------------------
titlepage: true
titlepage-color: "0B3D91"
titlepage-text-color: "FFFFFF"
titlepage-rule-color: "FFFFFF"
titlepage-rule-height: 2
logo-width: 100mm

toc: true
toc-own-page: true
toc-depth: 3

# Page layout
papersize: a4
geometry:
  - top=25mm
  - bottom=25mm
  - left=25mm
  - right=25mm
fontsize: 11pt
mainfont: "Arial"              # macOS-native, visually near-identical to Helvetica, full Unicode coverage (arrows, etc.)
monofont: "Menlo"
# Link colors: must be xcolor-named colors (not raw hex).
# NavyBlue is a built-in dvipsname that visually matches the titlepage hex.
linkcolor: "NavyBlue"
urlcolor: "NavyBlue"
toccolor: "NavyBlue"

# Code blocks
listings: true
listings-no-page-break: true
code-block-font-size: \footnotesize

# Header / footer
header-left: "Stock Portfolio Recommender"
header-right: "Liora APR26 BDS INT"
footer-left: "Marchesan · Flak · Schürstedt"
footer-right: "\\thepage"

# References / citations (uncomment when bibliography.bib lands)
# bibliography: bibliography.bib
# csl: ieee.csl
# link-citations: true
---

\newpage

# Executive Summary

> *Placeholder — to be finalised together with Section 11 (Conclusion).*

The **Stock Portfolio Recommender** is a beginner-friendly tool that turns a short
questionnaire about an investor (experience, time horizon, loss tolerance, monthly
budget, sector preferences) into a small, diversified portfolio of 5–10 stocks
picked from the S&P 500, accompanied by the risk metrics that justify each pick.

This document is the **single growing report** for the project. It is updated at
each Liora milestone:

| Milestone     | Deadline      | Sections covered             | Status        |
| ------------- | ------------- | ---------------------------- | ------------- |
| Rendering 1   | 2026-06-03    | §2 – §7                      | In progress   |
| Rendering 2   | 2026-07-01    | §8 – §9                      | Not started   |
| Final report  | 2026-07-08    | §1, §10 + revisions of all   | Not started   |

> **Disclaimer:** This project is decision support for a beginner investor, **not**
> financial advice.

\newpage

# 1. Introduction

## 1.1 Context and motivation

> *Placeholder — write 1–2 paragraphs explaining the gap in the retail-investor
> tooling market: existing screeners either lump users into "aggressive / moderate /
> conservative" buckets, or assume the user already speaks the language of finance.*

## 1.2 Problem statement

Retail investors who want to pick individual stocks usually have to choose between
paying for a broker's recommendation or scrolling through hundreds of tickers in an
online screener with no idea where to begin. We frame the recommendation problem in
three stages:

1. **Clustering** — group the stock universe by historical risk/return profile.
2. **Return ranking** — train a regression model to rank stocks *within* each cluster.
3. **Recommendation** — map the user's questionnaire to a target risk profile, pick the
   relevant clusters, and return top-*N* stocks per cluster, with a sector-concentration cap.

## 1.3 Scope and assumptions

- **Universe:** S&P 500 only (≈ 503 tickers). DAX 40 deferred to a stretch goal.
- **Granularity:** daily OHLCV bars; ≈ 5–6 years of history (Alpaca free IEX feed).
- **Currency:** USD only.
- **Horizon:** the recommender targets a 12-month-ahead expected return.
- **Out of scope:** intraday trading, options, fundamentals (P/E, EPS, dividend yield,
  any company financial statements), live execution, tax considerations.

## 1.4 Stakeholders and team

- **Team:** Gabriel Marchesan Almeida, Paweł Flak, Marcus Schürstedt.
- **Mentor:** Paul Grolier (Liora).
- **Audience for this report:** Liora jury (technical review, oral defense).

\newpage

# 2. Data Sources and Acquisition

## 2.1 Universe selection

> *Placeholder — explain the choice of S&P 500 as the initial universe, including the
> trade-off against the DAX 40. Single-currency, single-timezone, homogeneous accounting
> standards make for a cleaner first iteration.*

The S&P 500 constituent list is scraped from the Wikipedia page of S&P 500 companies.
We acknowledge the **survivorship bias** introduced by using today's index members
rather than a historical-constituent panel; mitigation strategies are discussed in
§6.1.

## 2.2 Data providers evaluated

| Provider | Role  | Status                                    |
| -------- | ----- | ----------------------------------------- |
| yfinance | OHLCV | **Rejected** (see §2.3)                   |
| Alpaca   | OHLCV | **Selected** (mentor-approved 2026-05-22) |

The project is intentionally **price-only** — no fundamentals, no risk-free rate, no offline
backup feed. Every feature engineered downstream (returns, volatility, beta, drawdown,
momentum, Sharpe with `rf = 0`) is derived from Alpaca OHLCV.

## 2.3 Why we abandoned yfinance (documented failed approach)

> *Placeholder — narrate the migration from yfinance to Alpaca that took place
> 2026-05-21 → 2026-05-24. Cover:*
>
> - *yfinance is an open-source scraper of an unofficial Yahoo endpoint, fragile to
>   rate limits / IP bans / silent breakage.*
> - *Paweł's side-by-side audit (`data provider choose.html`) — ~99.5 % similarity on
>   overlapping (ticker, date) pairs, with the worst tail attributable to split or
>   listing differences rather than data corruption.*
> - *Why Alpaca won: officially supported REST API, validated fields, batched bar
>   endpoint (200 symbols / req, 200 req / min), first-party SDK `alpaca-py`.*
> - *Trade-off: Alpaca does not cover DAX 40 on the free tier → reason for the
>   universe reduction.*

This is one of the **failed approaches** Paul explicitly asked us to document in the
final report.

## 2.4 Alpaca free IEX feed — capabilities and limits

- **Feed:** IEX (≈ 2–3 % of US volume); acceptable for **daily** aggregates.
- **History depth:** Alpaca returns data back to ≈ 2018-11-01 in our tests; SIP would
  give longer history but is paid.
- **Per-symbol caveat:** start dates are **not uniform**. New entrants (e.g. SNDK)
  have < 2 years of history. See §4.2 for the per-ticker availability map.
- **Adjustments:** we request `adjustment='all'` so splits and dividends are folded
  into the close price used for returns.

## 2.5 Acquisition pipeline (`fetch_data.py`)

> *Placeholder — describe the `fetch_data.py` CLI, configurable flags (`--years`,
> `--limit`, `--batch-size`), the output files in `data/`, and the verified run
> (2026-05-24: 503 tickers, 726 018 rows, 0 failures).*

\newpage

# 3. Data Audit

## 3.1 Datasets and schemas

| File                              | Rows    | Columns                          | Notes                         |
| --------------------------------- | ------- | -------------------------------- | ----------------------------- |
| `tickers.csv`                     | ≈&nbsp;503     | ticker, name, sector, industry,… | Wikipedia → enriched          |
| `prices_long.csv`                 | ≈&nbsp;726&nbsp;k | ticker, date, open, high, low, close, adj\_close, volume | Long format for feature eng. |
| `prices_close_wide.csv`           | ≈&nbsp;5&nbsp;k | date × ticker (adj\_close)       | Wide format for correlations |
| `failed_tickers.csv`              | 0       | ticker, reason                   | Empty after the last run     |

## 3.2 Data dictionary

> *Placeholder — provide a one-row-per-column dictionary: column name, dtype, unit,
> range, source, notes. Include the engineered columns from §7 once they exist.*

## 3.3 Completeness and missingness

> *Placeholder — produce a per-column missing-value count and a per-ticker
> first/last-trading-day table. Highlight the new entrants (SNDK, … ) with < 2 years
> of history.*

## 3.4 Statistical summary

> *Placeholder — table of `describe()` style stats for daily returns, log-returns,
> volume, and the engineered risk metrics; one short paragraph per column.*

\newpage

# 4. Exploratory Data Analysis

This section satisfies the Liora **Step 1** requirement: *"at least 5 relevant
visualizations, each with a precise commentary providing a business opinion and
validated by data manipulation or a statistical test."* We deliver **six**.

For each plot we provide:

- **What the plot shows** (one line).
- **Business commentary** (what the investor / model should take away).
- **Statistical validation** (a test or quantitative cross-check).

## 4.1 Number of stocks per sector

> *Placeholder — bar plot. Business commentary: which sectors dominate the S&P 500
> headcount; risk that the sector-concentration cap of 30 % becomes binding for
> tech-heavy profiles. Validation: χ² goodness-of-fit against a uniform-sector
> distribution.*

## 4.2 Mean daily volume per stock

> *Placeholder — histogram or sorted bar plot of mean daily volume. Business
> commentary: liquidity tiers — recommender should down-weight illiquid names.
> Validation: log-volume normality test (Shapiro / Jarque-Bera).*

## 4.3 Distribution of daily returns

> *Placeholder — histogram + KDE. Already-observed pattern: concentration around
> 0 % with small deviation. Business commentary: justifies the cluster + ranking
> approach (we are picking from a heavy-tailed-but-zero-centered population).
> Validation: Jarque-Bera vs. Normal; report skew, kurtosis.*

## 4.4 Price line plot (anchor tickers)

> *Placeholder — line plot of adj-close for a small anchor set (e.g. SPY, AAPL, MSFT,
> JPM, XOM, SNDK). Business commentary: visualises survivorship-bias proxy (SNDK has
> < 2 years of bars). Validation: report first/last available date per ticker.*

## 4.5 Correlation heatmap (sectors / top tickers)

> *Placeholder — Pearson correlation heatmap of daily log-returns. Business
> commentary: diversification logic — the recommender should pick across clusters
> with low cross-correlation. Validation: confirm with Spearman heatmap as a
> non-linear sanity check; report the off-diagonal mean.*

## 4.6 Risk vs. Return scatter

> *Placeholder — annualised return on the y-axis, annualised volatility on the
> x-axis, one dot per ticker, coloured by sector. **SNDK appears as an extreme
> outlier (≈ 342 % return, ≈ 98 % risk)** — discussed in §6.2. Business commentary:
> visual basis for the risk-tolerance mapping of the recommender. Validation:
> Pearson correlation between annualised vol and annualised return; bootstrap the
> mean Sharpe per sector.*

\newpage

# 5. Identified Issues and Biases

## 5.1 Survivorship bias

> *Placeholder — explain that today's S&P 500 ≠ historical S&P 500; the universe is
> biased toward winners. Mitigation roadmap: pull historical constituent lists from
> Wikipedia revisions if time permits (mentor 2026-05-22).*

## 5.2 Outliers — the SNDK case (documented failed-pure-drop)

> *Placeholder — narrate the discovery on the risk/return scatter: SNDK has
> 342 % return and 98 % risk, but only 1.2 years of history. Per the mentor
> (2026-05-28), we do **not** drop blindly. Instead, in §7 we plan the
> **with-vs.-without-outlier** modeling comparison and report the impact.*

## 5.3 Ragged histories (new S&P 500 entrants)

> *Placeholder — quantify the issue: count of tickers with < 2 y, < 5 y, ≥ 5 y of
> history. Decide a minimum-history rule for the clustering universe (e.g. ≥ 3 y),
> and explain why it is a defensible cutoff.*

## 5.4 Single-market / single-currency scope

> *Placeholder — acknowledge that dropping DAX 40 narrows the conclusions to USD
> equities. The methodology generalises but the back-tested numbers do not.*

## 5.5 Look-ahead leakage

> *Placeholder — explain the discipline used to prevent leakage: features at time t
> use only data available at t; cross-validation is `TimeSeriesSplit`, never k-fold
> (more in §7.6 and §8).*

\newpage

# 6. Data Manipulation Performed during EDA

> *Placeholder — short narrative of the data manipulations done **during** the
> exploration phase (vs. those done during pre-processing in §7). Examples:*
>
> - *Adjusted-close pivot (`pivot_table(index='date', columns='ticker', values='adj_close')`).*
> - *Daily log-returns: `np.log(adj_close / adj_close.shift(1))`.*
> - *Rolling annualised volatility (252-day window).*
> - *Sector and industry joins from `tickers.csv`.*
>
> *Include the exact code snippets that produced each plot in §4 so that the report
> remains reproducible from the raw CSVs.*

\newpage

# 7. Pre-processing and Feature Engineering

This section satisfies the Liora **Step 2** requirement.

## 7.1 End-state definition

The dataset emerging from this section must be **ML-ready**:

- Fully numerical (no string columns).
- No NaNs (or NaNs deliberately preserved with a documented downstream handler).
- One row per (ticker, date) for time-series modelling, plus a wide per-ticker
  feature matrix for clustering.
- Split-ready: indices that the modelling code can pass directly to
  `TimeSeriesSplit`.

## 7.2 Cleaning rules

> *Placeholder. Cover:*
>
> - *Drop trading-halt or zero-volume bars.*
> - *Handle ticker renames / mergers (track a `ticker_id` separate from `ticker`).*
> - *De-duplicate (ticker, date) rows from the raw pulls.*

## 7.3 Missing-value strategy (per column)

| Column                  | Missingness pattern | Strategy                                                         |
| ----------------------- | ------------------- | ---------------------------------------------------------------- |
| `open` / `high` / `low` / `close` | Trading halts | Forward-fill within ticker, max 3 days; else drop                |
| `volume`                | Holiday bars        | `0` + indicator column                                           |
| `adj_close`             | Pre-listing bars    | Left blank; ticker dropped if first-listing < min-history cutoff |
| `sector` / `industry`   | Unmapped tickers    | Manual fix via override CSV                                      |

> *Placeholder — refine table once we measure actual NA rates in §3.3.*

## 7.4 Categorical encoding

> *Placeholder. Decision matrix:*
>
> | Variable          | Cardinality | Encoding for tree-based models | Encoding for linear models |
> | ----------------- | ----------- | ------------------------------ | -------------------------- |
> | `sector` (11)     | low         | label encoding                 | one-hot                    |
> | `industry` (~120) | high        | target encoding (with CV)      | hashing trick              |
> | `index` (1)       | trivial     | drop                           | drop                       |

## 7.5 Derived features

> *Placeholder — define each feature with formula, window, and rationale. Suggested
> minimum set:*
>
> - *`ret_1d`, `ret_5d`, `ret_21d`, `ret_252d` — log-returns.*
> - *`vol_21d`, `vol_252d` — rolling annualised volatility.*
> - *`sharpe_252d` — computed with `rf = 0` (no external risk-free feed in scope).*
> - *`beta_252d` vs. SPY.*
> - *`max_drawdown_252d`.*
> - *`momentum_12_1` — 12-month return excluding the most recent month.*
> - *`amihud_illiq` — illiquidity proxy.*

## 7.6 Outlier policy (with-vs.-without comparison)

Per the mentor (2026-05-28), we **do not drop outliers blindly**. Instead, we will:

1. Define an outlier flag (e.g. `|z-score| > 4` on annualised return).
2. Train all downstream models **twice** — once with the flagged rows, once without.
3. Report Δ-metric (R², RMSE, ranking-IC) in §9 and let the data decide.

This is the standing protocol for the **SNDK-class** tickers introduced in §5.2.

## 7.7 Train / validation / test split

> *Placeholder — define the time-based split: train ≤ 2024-06, val 2024-07 → 2025-06,
> test 2025-07 → today. Justify why `TimeSeriesSplit` (5 folds) is used inside the
> training period and never random k-fold.*

\newpage

# 8. Modeling [PLACEHOLDER — Rendering 2, due 2026-07-01]

> *This section will be filled in for the Rendering 2 submission.*

<!--
  Internal outline (NOT rendered to PDF — drives Sprint 2 work):

  8.1 Baseline models
    - Clustering baseline: K-Means on (vol, return, beta, max-DD, sector-OHE).
    - Ranking baseline: linear regression of 12-month forward return on the §7
      feature set.
    - Recommendation baseline: equal-weight top-N within each cluster.

  8.2 Optimisation and hyperparameter search
    - Search strategy (grid / random / Bayesian).
    - Search budget.
    - Time-aware CV with TimeSeriesSplit.

  8.3 Advanced models — bagging, boosting, Deep Learning
    - Random Forest (bagging) — per the mentor (2026-05-28).
    - XGBoost (boosting) — per the mentor (2026-05-28).
    - Neural network baseline (Keras MLP) — to be introduced after Paul's
      masterclass on 2026-06-11.

  8.4 Interpretability
    - Feature importance (XGBoost gain, permutation importance).
    - SHAP values on a held-out fold.
    - Cluster persona descriptions (sector profile, mean Sharpe).

  8.5 Hierarchical clustering comparison
    - Linkage choice (ward, average, complete).
    - Cophenetic correlation vs. K-Means inertia.
-->

\newpage

# 9. Results and Discussion [PLACEHOLDER — Rendering 2]

> *Numbers will be filled during Sprint 2.*

<!--
  Internal outline (NOT rendered to PDF):

  9.1 Clustering quality
    - Silhouette score, Davies–Bouldin, Calinski–Harabasz.
    - Cluster persona summaries.

  9.2 Ranking model performance
    - R², RMSE, ranking IC (information coefficient) on out-of-time test.
    - Comparison: linear baseline · Random Forest · XGBoost.
    - With-vs.-without outliers comparison table (per §7.6).

  9.3 Recommendation evaluation
    - Backtest Sharpe of the top-N portfolio vs. equal-weight S&P 500.
    - Sector-cap binding frequency.
    - Sensitivity to the user-questionnaire mapping.

  9.4 Threats to validity
    - Survivorship bias (§5.1) — quantify residual effect.
    - Out-of-time degradation.
    - Free-tier feed coverage gaps.
-->

\newpage

# 10. Conclusion and Opening [PLACEHOLDER — Final Report]

> *This section will be added in the final report (2026-07-08).*

<!--
  Internal outline (NOT rendered to PDF):

  - What we built, in two paragraphs.
  - What worked, what didn't, what we'd do differently.
  - Three concrete extensions:
      (a) DAX 40 via a second provider,
      (b) historical-constituent panel to remove survivorship bias,
      (c) paper-trading loop via Alpaca.
-->

\newpage

# Appendices

## A. Reproducibility

> *Placeholder — exact `git clone`, `python -m venv`, `pip install -r requirements.txt`,
> `.env.local` setup, and the canonical command to regenerate every figure in §4.*

## B. Computing environment

> *Placeholder — Python version, OS, key library versions (pinned in
> `requirements.txt`).*

## C. Streamlit application

> *Placeholder — pages, navigation, how the recommender is served. Screenshots
> inline.*

## D. Glossary

> *Placeholder — Sharpe, beta, max drawdown, log-return, IEX feed, SIP feed,
> survivorship bias, look-ahead leakage, …*

## E. Bibliography

- Aroussi, R. — *[yfinance documentation](https://ranaroussi.github.io/yfinance/)*.
- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley.
- *(Add references progressively. Switch to a `.bib` file + CSL when count > 10.)*

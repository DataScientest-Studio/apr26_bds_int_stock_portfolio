# Stage 7 Report: Portfolio Construction Layer

## Why We Added Portfolio Construction

Until now, the project produced model rankings.

A ranking answers:

> Which stocks does the model score highest?

But a portfolio recommender needs to answer a more practical question:

> Which stocks should be selected together for a user?

The highest-ranked stocks can be too concentrated in one sector or too risky for
some users. So we added a portfolio construction layer on top of the current
best model.

## Model Used

The portfolio layer uses:

```text
Random Forest without history_days
```

This is the current main model because:

- it performed well on the five-year dataset
- removing `history_days` improved results
- walk-forward testing showed top-5 picks beat the universe in 7 of 9 folds
- it is easier to explain than the neural network

Input file:

```text
models/random_forest_no_history_latest_rankings.csv
```

The latest recommendation date is:

```text
2026-06-05
```

## Portfolio Rules

Each portfolio uses the same basic construction rules:

| Rule | Value |
|---|---:|
| Number of stocks | 10 |
| Weighting method | Equal weight |
| Weight per stock | 10% |
| Maximum single-stock weight | 20% |
| Maximum sector weight | 30% |
| Maximum stocks per sector | 3 |

Equal weighting keeps the first version simple and beginner-friendly.

The sector constraint prevents the model from putting almost everything into
one sector, especially Information Technology.

## Risk Profiles

Three user profiles were created.

| Profile | 60-Day Volatility Cap | Meaning |
|---|---:|---|
| Conservative | 0.35 | Lower-volatility stocks first |
| Balanced | 0.50 | Medium risk |
| Aggressive | 0.80 | Allows higher-volatility stocks |

The portfolios did not need to relax these volatility caps.

## Portfolio Summary

| Profile | Expected 63-Day Return | Avg 60-Day Volatility | Sectors | Max Sector Weight |
|---|---:|---:|---:|---:|
| Conservative | 0.0614 | 0.2971 | 6 | 30% |
| Balanced | 0.0841 | 0.3730 | 5 | 30% |
| Aggressive | 0.1291 | 0.5039 | 5 | 30% |

Interpretation:

- Conservative has the lowest expected return and lowest volatility.
- Balanced sits in the middle.
- Aggressive has the highest expected return and highest volatility.

This is exactly what we want from a simple risk-profile system.

## Conservative Portfolio

| Rank | Ticker | Sector | Weight | Predicted 63-Day Return | Volatility |
|---:|---|---|---:|---:|---:|
| 1 | CMG | Consumer Discretionary | 10% | 0.0916 | 0.3462 |
| 2 | PYPL | Financials | 10% | 0.0675 | 0.3299 |
| 3 | CPRT | Industrials | 10% | 0.0666 | 0.2424 |
| 4 | ICE | Financials | 10% | 0.0630 | 0.2224 |
| 5 | LDOS | Industrials | 10% | 0.0608 | 0.2785 |
| 6 | ROP | Information Technology | 10% | 0.0574 | 0.2609 |
| 7 | UHS | Health Care | 10% | 0.0551 | 0.3226 |
| 8 | TRMB | Information Technology | 10% | 0.0515 | 0.3338 |
| 9 | PTC | Information Technology | 10% | 0.0506 | 0.3180 |
| 10 | NFLX | Communication Services | 10% | 0.0503 | 0.3166 |

Sector weights:

| Sector | Weight |
|---|---:|
| Information Technology | 30% |
| Financials | 20% |
| Industrials | 20% |
| Communication Services | 10% |
| Consumer Discretionary | 10% |
| Health Care | 10% |

## Balanced Portfolio

| Rank | Ticker | Sector | Weight | Predicted 63-Day Return | Volatility |
|---:|---|---|---:|---:|---:|
| 1 | TSCO | Consumer Discretionary | 10% | 0.1270 | 0.4221 |
| 2 | CMG | Consumer Discretionary | 10% | 0.0916 | 0.3462 |
| 3 | CSGP | Real Estate | 10% | 0.0899 | 0.3710 |
| 4 | LULU | Consumer Discretionary | 10% | 0.0898 | 0.4810 |
| 5 | FIS | Financials | 10% | 0.0826 | 0.3671 |
| 6 | TYL | Information Technology | 10% | 0.0793 | 0.3677 |
| 7 | GDDY | Information Technology | 10% | 0.0789 | 0.4215 |
| 8 | FISV | Financials | 10% | 0.0678 | 0.3811 |
| 9 | PYPL | Financials | 10% | 0.0675 | 0.3299 |
| 10 | CPRT | Industrials | 10% | 0.0666 | 0.2424 |

Sector weights:

| Sector | Weight |
|---|---:|
| Consumer Discretionary | 30% |
| Financials | 30% |
| Information Technology | 20% |
| Industrials | 10% |
| Real Estate | 10% |

## Aggressive Portfolio

| Rank | Ticker | Sector | Weight | Predicted 63-Day Return | Volatility |
|---:|---|---|---:|---:|---:|
| 1 | STX | Information Technology | 10% | 0.1860 | 0.6526 |
| 2 | NTAP | Information Technology | 10% | 0.1854 | 0.6101 |
| 3 | FTNT | Information Technology | 10% | 0.1741 | 0.5674 |
| 4 | CEG | Utilities | 10% | 0.1338 | 0.5302 |
| 5 | TPL | Energy | 10% | 0.1280 | 0.5474 |
| 6 | TSCO | Consumer Discretionary | 10% | 0.1270 | 0.4221 |
| 7 | CMG | Consumer Discretionary | 10% | 0.0916 | 0.3462 |
| 8 | CSGP | Real Estate | 10% | 0.0899 | 0.3710 |
| 9 | LULU | Consumer Discretionary | 10% | 0.0898 | 0.4810 |
| 10 | APA | Energy | 10% | 0.0859 | 0.5107 |

Sector weights:

| Sector | Weight |
|---|---:|
| Consumer Discretionary | 30% |
| Information Technology | 30% |
| Energy | 20% |
| Real Estate | 10% |
| Utilities | 10% |

## What We Learned

### 1. The Constraint Layer Changes The Result

The raw model ranking was dominated by Information Technology.

The portfolio layer forced diversification. No portfolio has more than 30% in
one sector.

This makes the recommendation more realistic.

### 2. Risk Profiles Behave As Expected

The average volatility increases from conservative to aggressive:

```text
Conservative: 0.2971
Balanced:     0.3730
Aggressive:   0.5039
```

The expected return also increases:

```text
Conservative: 0.0614
Balanced:     0.0841
Aggressive:   0.1291
```

This is a good sign. The profile system is doing what it is supposed to do.

### 3. Equal Weighting Is Simple But Not Final

Equal weighting is easy to explain:

```text
10 stocks x 10% each
```

But future versions could improve weighting by using:

- lower weight for high-volatility stocks
- higher weight for stronger scores
- maximum drawdown limits
- target risk contribution

For a beginner project, equal weighting is a good first version.

## Output Files

New files:

```text
models/build_portfolios.py
models/portfolio_recommendations.csv
models/portfolio_summary.csv
models/portfolio_sector_weights.csv
```

## Recommendation

The project now has a complete first recommender pipeline:

```text
download data
build features
train and compare models
validate with walk-forward testing
rank stocks with Random Forest no-history
construct constrained portfolios
```

The next best step is to integrate this into the Streamlit app:

```text
User selects risk profile
App displays the matching portfolio
App shows expected return, volatility, and sector weights
```


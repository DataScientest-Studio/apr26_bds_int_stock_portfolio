# Stage 4 Report: Random Forest Without `history_days`

## Why We Ran This Experiment

In the five-year Random Forest run, the most important feature was:

```text
history_days
```

That feature means:

> How many historical rows are available for a ticker at a given date?

It can be useful because newer stocks and older stocks may behave differently.
But it can also become a shortcut. Instead of learning price behavior, the model
might learn that "more history" or "less history" is associated with certain
stocks or market periods.

So we trained a second Random Forest model with the same data, same target, same
time split, and same settings, but removed `history_days` from the input
features.

## Dataset And Split

The experiment used the five-year S&P 500 dataset:

| Item | Value |
|---|---:|
| Date range | 2021-06-09 to 2026-06-05 |
| Tickers | 503 |
| Price rows | 622,465 |
| Trading dates | 1,254 |

Train/test split:

| Split | Date Range | Rows |
|---|---|---:|
| Train | 2021-09-02 to 2024-12-31 | 413,691 |
| Test | 2025-01-02 to 2026-03-06 | 147,023 |

## Results

| Metric | Random Forest With `history_days` | Random Forest Without `history_days` |
|---|---:|---:|
| MAE | 0.1349 | 0.1342 |
| RMSE | 0.2089 | 0.2047 |
| Spearman rank correlation | 0.0862 | 0.1039 |
| Top-5 average actual return | 0.1902 | 0.3553 |

Removing `history_days` improved every key metric.

The biggest improvement was in top-5 average actual return:

```text
With history_days:    0.1902
Without history_days: 0.3553
```

That is an important result because the recommender cares about the quality of
the highest-ranked stocks.

## New Feature Importance

After removing `history_days`, the top features became:

| Rank | Feature | Importance |
|---:|---|---:|
| 1 | `drawdown_252d` | 0.1786 |
| 2 | `volatility_60d` | 0.1676 |
| 3 | `log_avg_volume_20d` | 0.1548 |
| 4 | `volatility_20d` | 0.0920 |
| 5 | `mean_return_60d` | 0.0759 |
| 6 | `ret_60d` | 0.0731 |
| 7 | `mean_return_20d` | 0.0523 |
| 8 | `ret_20d` | 0.0480 |
| 9 | `ret_5d` | 0.0273 |
| 10 | `sector_Health Care` | 0.0253 |

This is healthier.

The model now focuses more on actual market behavior:

- drawdown
- volatility
- volume
- recent return
- sector

Those are easier to explain as financial signals than `history_days`.

## Beginner Interpretation

This experiment shows why feature testing matters.

A feature can look useful in a model, but still be a shortcut. If removing the
feature improves results, that tells us the model was probably using it in a way
that did not generalize well.

In this case, removing `history_days` made the Random Forest:

- slightly more accurate
- better at ranking
- much better in top-5 stock selection
- easier to explain

## Updated Model Choice

The best current practical model is now:

```text
Random Forest without history_days
```

Why:

- best Random Forest metrics
- better top-pick behavior
- feature importance is more financially meaningful
- still beginner-friendly and explainable

## Output Files

New files:

```text
models/random_forest_no_history_model.pkl
models/random_forest_no_history_metrics.csv
models/random_forest_no_history_predictions.csv
models/random_forest_no_history_latest_rankings.csv
models/random_forest_no_history_feature_importance.csv
models/train_random_forest_no_history_model.py
```

## Recommendation

Use the no-history Random Forest as the main model for the next recommender
prototype.

Keep the older Random Forest with `history_days` only as a comparison result.

Next best experiment:

```text
Add XGBoost using the no-history feature set.
```

XGBoost often performs very well on tabular data and may improve the ranking
quality further.


# Stage 6 Report: Walk-Forward Backtesting

## Why We Needed Walk-Forward Backtesting

So far, the models were evaluated with one train/test split.

That is useful, but it can be misleading. A model might look good because it
performed well during one specific market period.

Walk-forward backtesting is a better test for time-series data.

Instead of training once and testing once, we repeat the process:

```text
Train on older data -> test the next period
Expand training data -> test the next period
Expand again -> test again
```

This is closer to how a real recommender would work over time.

## Model Tested

The walk-forward test used the current best practical model:

```text
Random Forest without history_days
```

We used the no-history version because the previous experiment showed that
removing `history_days` improved model quality and avoided a shortcut feature.

## Dataset

The same five-year S&P 500 dataset was used:

| Item | Value |
|---|---:|
| Date range | 2021-06-09 to 2026-06-05 |
| Tickers | 503 |
| Price rows | 622,465 |
| Trading dates | 1,254 |

The target stayed the same:

```text
target_63d_return
```

That means the return over the next 63 trading days.

## Walk-Forward Design

The script used:

| Setting | Value |
|---|---:|
| Initial training window | 504 trading days |
| Test window | 63 trading days |
| Step size | 63 trading days |
| Number of folds | 9 |

504 trading days is roughly two years.

63 trading days is roughly three months.

Each fold trained on all available historical data up to that point and tested
on the next 63 trading days.

## Summary Results

| Metric | Walk-Forward Average |
|---|---:|
| Folds | 9 |
| Mean MAE | 0.1256 |
| Mean RMSE | 0.1826 |
| Mean Spearman rank correlation | 0.0601 |
| Mean universe average actual return | 0.0568 |
| Mean top-5 average actual return | 0.2049 |
| Mean top-10 average actual return | 0.1642 |
| Folds where top-5 beat universe | 7 of 9 |

The most important result:

```text
Top-5 picks beat the universe average in 7 out of 9 folds.
```

That is a useful sign. It means the model did not only work in one fixed test
period. It usually selected better-than-average stocks across multiple windows.

## Fold Results

| Fold | Test Period | Spearman | Universe Avg | Top-5 Avg |
|---:|---|---:|---:|---:|
| 1 | 2023-09-06 to 2023-12-04 | -0.0145 | 0.1254 | -0.0336 |
| 2 | 2023-12-05 to 2024-03-06 | 0.0969 | 0.0748 | 0.4224 |
| 3 | 2024-03-07 to 2024-06-05 | -0.0009 | 0.0328 | 0.0928 |
| 4 | 2024-06-06 to 2024-09-05 | 0.0662 | 0.0902 | 0.1286 |
| 5 | 2024-09-06 to 2024-12-04 | 0.0285 | 0.0163 | 0.1767 |
| 6 | 2024-12-05 to 2025-03-10 | 0.0235 | -0.0390 | -0.0526 |
| 7 | 2025-03-11 to 2025-06-09 | 0.2163 | 0.0994 | 0.3190 |
| 8 | 2025-06-10 to 2025-09-09 | 0.0799 | 0.0472 | 0.3416 |
| 9 | 2025-09-10 to 2025-12-08 | 0.0446 | 0.0642 | 0.4493 |

## Beginner Interpretation

The model was not perfect.

Fold 1 was bad: the top-5 picks lost money while the universe did well.

Fold 6 was also weak: both the universe and the top-5 picks were negative, and
the top-5 picks were slightly worse.

But in 7 of 9 folds, the model's top-5 picks beat the average stock in the test
universe.

This is exactly why walk-forward testing is useful:

> It shows both the good periods and the bad periods.

A single train/test split can hide that.

## Average Feature Importance

Across the folds, the most important features were:

| Rank | Feature | Importance |
|---:|---|---:|
| 1 | `volatility_60d` | 0.1767 |
| 2 | `drawdown_252d` | 0.1706 |
| 3 | `log_avg_volume_20d` | 0.1463 |
| 4 | `volatility_20d` | 0.1022 |
| 5 | `mean_return_60d` | 0.0702 |
| 6 | `ret_60d` | 0.0681 |
| 7 | `mean_return_20d` | 0.0539 |
| 8 | `ret_20d` | 0.0521 |
| 9 | `sector_Energy` | 0.0295 |
| 10 | `ret_5d` | 0.0290 |

This is a healthier feature pattern than the earlier model with `history_days`.

The model is mostly using:

- volatility
- drawdown
- volume
- recent return
- sector

Those are meaningful financial signals.

## What We Learned

### 1. Random Forest No-History Still Looks Useful

The model beat the universe average in most test windows.

That supports using it as the main recommender ranking model for now.

### 2. Ranking Is Noisy

The mean Spearman rank correlation was only:

```text
0.0601
```

That is positive, but small.

This means the model has some ranking signal, but it is not strong enough to
trust blindly.

### 3. Top Picks Matter More Than Full Ranking

The model does not rank every stock perfectly.

But the top-5 average return was much better than the universe average:

```text
Universe average: 0.0568
Top-5 average:    0.2049
```

For a recommender, this is important because we care most about the selected
portfolio, not every single stock's exact rank.

### 4. Risk Controls Are Still Needed

The model had weak periods.

A real app should not simply buy the top 5 predictions. It should add:

- max sector exposure
- max single-stock weight
- volatility limit
- user risk profile
- maybe stop extreme model scores

## Output Files

New files:

```text
models/walk_forward_random_forest_no_history.py
models/walk_forward_rf_no_history_summary.csv
models/walk_forward_rf_no_history_fold_metrics.csv
models/walk_forward_rf_no_history_predictions.csv
models/walk_forward_rf_no_history_feature_importance.csv
models/walk_forward_rf_no_history_last_model.pkl
```

## Recommendation

The walk-forward result supports the current model choice:

```text
Use Random Forest without history_days as the main ranking model.
```

But the next project step should not be another model immediately.

The next best step is:

```text
Build the portfolio construction layer.
```

That means turning model rankings into a diversified recommendation:

```text
5-10 stocks
max 30% per sector
max 20% per stock
exclude stocks above user risk limit
rank by Random Forest score
```

This will move the project from "model experiment" toward the actual portfolio
recommender product.


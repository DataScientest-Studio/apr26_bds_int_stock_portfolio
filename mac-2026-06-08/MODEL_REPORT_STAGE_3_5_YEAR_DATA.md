# Stage 3 Report: Five Years Of Data

## What Changed

The project was updated from a one-year dataset to a five-year dataset.

New dataset:

| Item | Value |
|---|---:|
| Stock universe | S&P 500 |
| Tickers | 503 |
| Date range | 2021-06-09 to 2026-06-05 |
| Trading dates | 1,254 |
| Price rows | 622,465 |
| Missing values in price columns | 0 |

This gives the models much more history than the previous one-year dataset.

## Why This Matters

One year of data can be dominated by one market trend. In the previous run,
recent technology momentum was very strong, and the models learned that pattern.

Five years gives the models more examples from different market conditions. This
usually makes evaluation more realistic, but it can also make the problem
harder because the market changes over time.

## Train/Test Split

The fixed split date became valid again because the dataset now starts in 2021.

| Split | Date Range | Rows |
|---|---|---:|
| Train | 2021-09-02 to 2024-12-31 | 413,691 |
| Test | 2025-01-02 to 2026-03-06 | 147,023 |

The models still predict:

```text
target_63d_return
```

This is the future return over roughly three trading months.

## Model Results

| Metric | Ridge | Random Forest | ROCm PyTorch |
|---|---:|---:|---:|
| MAE | 0.1449 | 0.1349 | 0.2284 |
| RMSE | 0.2109 | 0.2089 | 0.3106 |
| Spearman rank correlation | 0.1197 | 0.0862 | 0.0057 |
| Top-5 average actual return | 0.1052 | 0.1902 | 0.1432 |

## What We Learned

Random Forest is now the best practical model from this run.

It has:

- best MAE
- best RMSE
- best top-5 average actual return

Ridge has the best Spearman rank correlation, but only slightly. Random Forest
has the stronger overall business result because its top picks performed better.

The ROCm PyTorch model performed worse on this longer dataset. That does not
mean ROCm or neural networks are bad. It means this simple neural network setup
is not yet tuned well enough for the larger historical dataset.

## Feature Importance

Random Forest's most important features were:

| Rank | Feature | Importance |
|---:|---|---:|
| 1 | `history_days` | 0.4491 |
| 2 | `volatility_60d` | 0.0996 |
| 3 | `drawdown_252d` | 0.0815 |
| 4 | `log_avg_volume_20d` | 0.0588 |
| 5 | `volatility_20d` | 0.0562 |
| 6 | `ret_60d` | 0.0418 |
| 7 | `mean_return_60d` | 0.0417 |
| 8 | `sector_Energy` | 0.0358 |
| 9 | `mean_return_20d` | 0.0232 |
| 10 | `ret_20d` | 0.0220 |

The high importance of `history_days` is a warning. It means the model is using
how much data a ticker has as a major signal. This may partly separate newer
stocks from older stocks, but it might also be a shortcut rather than a true
financial signal.

Next, we should test Random Forest both with and without `history_days`.

## Beginner Interpretation

Adding more data made the evaluation more serious.

On the one-year dataset, the ROCm PyTorch model looked strongest for ranking.
On the five-year dataset, Random Forest became the strongest practical model.

This is a normal machine learning lesson:

> A model that wins on a small dataset may not win on a larger or more realistic
> dataset.

The longer dataset gives us more confidence in Random Forest as the next model
to use for the recommender prototype.

## Recommended Next Steps

1. Use Random Forest as the main model for now.
2. Rerun Random Forest without `history_days` and compare results.
3. Add XGBoost as the next model.
4. Add walk-forward backtesting instead of one fixed train/test split.
5. Add portfolio constraints so the model rankings become diversified
   recommendations.

## Current Recommendation

For the next app version:

```text
Use Random Forest predictions as the main stock ranking score.
Keep Ridge as the simple baseline.
Keep ROCm PyTorch as an experimental advanced model.
```


# Stage 5 Report: XGBoost No-History Model

## Why We Tried XGBoost

After Ridge, Random Forest, and the ROCm PyTorch model, the next natural model
to test is XGBoost.

XGBoost is popular for tabular machine learning problems. It often performs very
well when the data is stored in rows and columns, like this stock dataset.

The goal of this experiment was:

> Test whether XGBoost can beat the current best model, Random Forest without
> `history_days`.

We used the no-history feature set because the previous experiment showed that
removing `history_days` improved Random Forest.

## Dataset And Split

The experiment used the same five-year S&P 500 dataset:

| Item | Value |
|---|---:|
| Date range | 2021-06-09 to 2026-06-05 |
| Tickers | 503 |
| Price rows | 622,465 |
| Trading dates | 1,254 |

The same train/test split was used:

| Split | Date Range | Rows |
|---|---|---:|
| Train | 2021-09-02 to 2024-12-31 | 413,691 |
| Test | 2025-01-02 to 2026-03-06 | 147,023 |

This keeps the model comparison fair.

## What XGBoost Is

XGBoost is a boosted tree model.

Random Forest builds many trees independently and averages them.

XGBoost builds trees sequentially. Each new tree tries to fix the mistakes made
by the previous trees.

Beginner explanation:

```text
Random Forest = many independent opinions averaged together
XGBoost       = many small corrections added step by step
```

This often makes XGBoost powerful, but it also means it can overfit if the
settings are too aggressive.

## Model Settings

The model used:

```text
n_estimators = 700
max_depth = 4
learning_rate = 0.03
min_child_weight = 30
subsample = 0.85
colsample_bytree = 0.85
reg_lambda = 5.0
reg_alpha = 0.05
tree_method = hist
```

These are conservative settings. The goal was not to maximize leaderboard
performance immediately, but to get a reasonable first XGBoost benchmark.

This XGBoost run used CPU histogram trees. The installed XGBoost package is not
a ROCm GPU backend.

## Results

| Metric | Ridge | Random Forest No History | XGBoost No History | ROCm PyTorch |
|---|---:|---:|---:|---:|
| MAE | 0.1449 | 0.1342 | 0.1371 | 0.2284 |
| RMSE | 0.2109 | 0.2047 | 0.2106 | 0.3106 |
| Spearman rank correlation | 0.1197 | 0.1039 | 0.0528 | 0.0057 |
| Top-5 average actual return | 0.1052 | 0.3553 | 0.2255 | 0.1432 |

## What The Results Mean

XGBoost did not beat Random Forest in this first run.

Compared with Random Forest without `history_days`, XGBoost had:

- higher MAE
- higher RMSE
- lower Spearman rank correlation
- lower top-5 average actual return

The best current model is still:

```text
Random Forest without history_days
```

However, XGBoost still beat Ridge on top-5 average actual return:

```text
Ridge top-5:   0.1052
XGBoost top-5: 0.2255
```

So XGBoost is not useless. It is just not the best current model.

## Feature Importance

XGBoost's top features were:

| Rank | Feature | Importance |
|---:|---|---:|
| 1 | `sector_Consumer Discretionary` | 0.0941 |
| 2 | `sector_Health Care` | 0.0721 |
| 3 | `log_avg_volume_20d` | 0.0713 |
| 4 | `volatility_60d` | 0.0613 |
| 5 | `drawdown_252d` | 0.0591 |
| 6 | `sector_Information Technology` | 0.0561 |
| 7 | `sector_Real Estate` | 0.0513 |
| 8 | `sector_Energy` | 0.0506 |
| 9 | `sector_Consumer Staples` | 0.0502 |
| 10 | `sector_Utilities` | 0.0496 |

This is different from Random Forest.

Random Forest emphasized drawdown, volatility, volume, and recent returns.

XGBoost gave more weight to sector indicators. That means it learned more
sector-level behavior during this test period.

## Latest Top Predictions

For the latest available date, 2026-06-05, XGBoost ranked these names highest:

| Rank | Ticker | Sector | Predicted 63-Day Return |
|---:|---|---|---:|
| 1 | TTD | Communication Services | 0.3139 |
| 2 | CEG | Utilities | 0.3031 |
| 3 | STX | Information Technology | 0.2857 |
| 4 | TSCO | Consumer Discretionary | 0.2495 |
| 5 | INTC | Information Technology | 0.2347 |
| 6 | APP | Information Technology | 0.2271 |
| 7 | CMG | Consumer Discretionary | 0.2170 |
| 8 | NTAP | Information Technology | 0.2169 |
| 9 | TPL | Energy | 0.2093 |
| 10 | ORCL | Information Technology | 0.2019 |

These predictions are more conservative than the earlier one-year neural-network
predictions. That is generally good. Extremely large predicted returns often
mean a model is extrapolating too aggressively.

## Beginner Lessons

### Lesson 1: Famous Models Do Not Automatically Win

XGBoost is a strong and widely used model, but it did not win this experiment.

This is normal.

Machine learning is empirical. We test models on our actual data and compare
results.

### Lesson 2: Feature Set Matters

Using the no-history feature set was important because it had already improved
Random Forest.

A model is only as good as the information it receives.

### Lesson 3: Ranking Metrics Matter

For this recommender project, top-5 average actual return is very important.

XGBoost's top-5 result was better than Ridge but worse than Random Forest no
history.

That means XGBoost may be useful, but it is not the current main model.

### Lesson 4: More Tuning May Change The Result

This was a first XGBoost benchmark.

Different hyperparameters may improve it:

- fewer or more trees
- different tree depth
- smaller learning rate
- stronger regularization
- different target horizon
- walk-forward validation

But we should not over-tune on one test split.

## Output Files

New files:

```text
models/train_xgboost_no_history_model.py
models/xgboost_no_history_model.json
models/xgboost_no_history_model.pkl
models/xgboost_no_history_metrics.csv
models/xgboost_no_history_predictions.csv
models/xgboost_no_history_latest_rankings.csv
models/xgboost_no_history_feature_importance.csv
```

## Current Recommendation

Use this model order for the next app prototype:

| Role | Model |
|---|---|
| Main recommender ranking model | Random Forest without `history_days` |
| Simple baseline | Ridge |
| Extra comparison | XGBoost without `history_days` |
| Experimental advanced model | ROCm PyTorch |

The main model should remain:

```text
Random Forest without history_days
```

Next best improvement:

```text
Add walk-forward backtesting.
```

One fixed train/test split is useful, but not enough. Walk-forward backtesting
will show whether the Random Forest advantage is stable across multiple market
periods.


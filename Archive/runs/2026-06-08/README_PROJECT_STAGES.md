# Project Stage Guide: Stock Portfolio Recommender

This README is a beginner-friendly index for the full machine learning project.

It explains what was built, in which order, what each stage teaches, and which
files to open if you want the details.

## Project In One Sentence

This project builds a stock portfolio recommender that:

1. downloads S&P 500 price data,
2. creates machine learning features,
3. trains several prediction models,
4. validates the best model over time,
5. converts model rankings into diversified portfolios.

The final result is not just a model. It is a first complete recommendation
pipeline.

## Important Disclaimer

This project is for learning and decision support only.

It is not financial advice, not a trading system, and not a guarantee of future
returns.

## Current Best Model

The current best practical model is:

```text
Random Forest without history_days
```

Why:

- it performed well on five years of S&P 500 data,
- it improved after removing the shortcut-like `history_days` feature,
- it performed well in walk-forward testing,
- it is easier to explain than the neural network,
- it can provide feature importance.

## Current Final Output

The final output is a set of three constrained portfolios:

| Profile | Expected 63-Day Return | Avg 60-Day Volatility | Stocks | Max Sector Weight |
|---|---:|---:|---:|---:|
| Conservative | 0.0614 | 0.2971 | 10 | 30% |
| Balanced | 0.0841 | 0.3730 | 10 | 30% |
| Aggressive | 0.1291 | 0.5039 | 10 | 30% |

Main output files:

```text
models/portfolio_recommendations.csv
models/portfolio_summary.csv
models/portfolio_sector_weights.csv
```

## Recommended Reading Order

Read the reports in this order.

### Stage 1: First Machine Learning Pipeline

Read:

```text
MODEL_REPORT.md
```

What this stage explains:

- what data was used,
- why `adj_close` matters,
- how returns and volatility were created,
- what the prediction target means,
- why we split data by time,
- how Ridge and ROCm PyTorch models were trained.

Beginner lesson:

> A machine learning project is more than a model. Data preparation, target
> definition, and evaluation design are just as important.

### Stage 2: Random Forest

Read:

```text
MODEL_REPORT_STAGE_2_RANDOM_FOREST.md
```

What this stage adds:

- Random Forest as a stronger tabular model,
- feature importance,
- comparison against Ridge and ROCm PyTorch.

Beginner lesson:

> Random Forest is a strong and explainable next step after a simple linear
> model.

### Stage 3: Five Years Of Data

Read:

```text
MODEL_REPORT_STAGE_3_5_YEAR_DATA.md
```

What this stage adds:

- the dataset was expanded from one year to five years,
- all models were rerun,
- model performance changed with more history.

Beginner lesson:

> A model that looks good on a small dataset may not stay best when more
> realistic data is added.

### Stage 4: Removing `history_days`

Read:

```text
MODEL_REPORT_STAGE_4_NO_HISTORY_DAYS.md
```

What this stage adds:

- tests whether `history_days` was acting like a shortcut,
- trains Random Forest without that feature,
- compares old and new Random Forest results.

Key result:

| Metric | RF With `history_days` | RF Without `history_days` |
|---|---:|---:|
| MAE | 0.1349 | 0.1342 |
| RMSE | 0.2089 | 0.2047 |
| Spearman | 0.0862 | 0.1039 |
| Top-5 avg actual return | 0.1902 | 0.3553 |

Beginner lesson:

> A feature can look important but still hurt generalization. Testing feature
> removal is a real part of model development.

### Stage 5: XGBoost

Read:

```text
MODEL_REPORT_STAGE_5_XGBOOST.md
```

What this stage adds:

- XGBoost benchmark,
- comparison with Random Forest no-history,
- XGBoost feature importance.

Key result:

| Model | MAE | RMSE | Spearman | Top-5 Avg Actual Return |
|---|---:|---:|---:|---:|
| Random Forest no-history | 0.1342 | 0.2047 | 0.1039 | 0.3553 |
| XGBoost no-history | 0.1371 | 0.2106 | 0.0528 | 0.2255 |

Beginner lesson:

> Famous models do not automatically win. You must test them on your actual
> data and business metric.

### Stage 6: Walk-Forward Backtesting

Read:

```text
MODEL_REPORT_STAGE_6_WALK_FORWARD.md
```

What this stage adds:

- more realistic time-based evaluation,
- nine expanding-window train/test folds,
- stability check across different market periods.

Key result:

```text
Top-5 picks beat the universe average in 7 of 9 folds.
```

Summary:

| Metric | Walk-Forward Average |
|---|---:|
| Mean MAE | 0.1256 |
| Mean RMSE | 0.1826 |
| Mean Spearman | 0.0601 |
| Mean universe return | 0.0568 |
| Mean top-5 return | 0.2049 |

Beginner lesson:

> One train/test split is not enough for time-series data. Walk-forward testing
> shows whether the model works repeatedly over time.

### Stage 7: Portfolio Construction

Read:

```text
MODEL_REPORT_STAGE_7_PORTFOLIO_CONSTRUCTION.md
```

What this stage adds:

- converts rankings into actual portfolios,
- creates conservative, balanced, and aggressive profiles,
- applies sector and volatility constraints.

Portfolio rules:

```text
10 stocks
10% equal weight per stock
max 30% per sector
risk profile based on 60-day volatility
```

Beginner lesson:

> A model score is not yet a portfolio. A recommender needs constraints,
> diversification, and user-risk logic.

## Main Data Files

```text
data/tickers.csv
data/prices_long.csv
data/prices_close_wide.csv
data/by_ticker/SP500/
```

Current dataset:

| Item | Value |
|---|---:|
| Universe | S&P 500 |
| Tickers | 503 |
| Date range | 2021-06-09 to 2026-06-05 |
| Price rows | 622,465 |
| Trading dates | 1,254 |

## Main Model Scripts

```text
models/train_first_model.py
models/train_random_forest_model.py
models/train_random_forest_no_history_model.py
models/train_xgboost_no_history_model.py
models/train_rocm_model.py
models/walk_forward_random_forest_no_history.py
models/build_portfolios.py
```

## Main Model Outputs

### Ridge Baseline

```text
models/first_model.pkl
models/model_metrics.csv
models/predictions.csv
models/latest_rankings.csv
```

### Random Forest No-History

```text
models/random_forest_no_history_model.pkl
models/random_forest_no_history_metrics.csv
models/random_forest_no_history_predictions.csv
models/random_forest_no_history_latest_rankings.csv
models/random_forest_no_history_feature_importance.csv
```

### XGBoost No-History

```text
models/xgboost_no_history_model.json
models/xgboost_no_history_metrics.csv
models/xgboost_no_history_predictions.csv
models/xgboost_no_history_latest_rankings.csv
models/xgboost_no_history_feature_importance.csv
```

### ROCm PyTorch

```text
models/rocm_model.pt
models/rocm_model_metrics.csv
models/rocm_predictions.csv
models/rocm_latest_rankings.csv
models/rocm_training_history.json
```

### Walk-Forward Backtest

```text
models/walk_forward_rf_no_history_summary.csv
models/walk_forward_rf_no_history_fold_metrics.csv
models/walk_forward_rf_no_history_predictions.csv
models/walk_forward_rf_no_history_feature_importance.csv
```

### Final Portfolio Outputs

```text
models/portfolio_recommendations.csv
models/portfolio_summary.csv
models/portfolio_sector_weights.csv
```

## How To Reproduce The Current Pipeline

From this folder:

```bash
cd mac-2026-06-08
source .venv/bin/activate
```

Download five years of data:

```bash
python fetch_data.py --years 5 --batch-size 10
```

Train the main model:

```bash
python models/train_random_forest_no_history_model.py
```

Run walk-forward backtesting:

```bash
python models/walk_forward_random_forest_no_history.py
```

Build final portfolios:

```bash
python models/build_portfolios.py
```

Optional comparison models:

```bash
python models/train_first_model.py
python models/train_xgboost_no_history_model.py
HSA_ENABLE_DXG_DETECTION=1 python models/train_rocm_model.py
```

## What A Beginner Should Understand By The End

After reading the reports, you should understand:

- what stock price data looks like,
- why adjusted close is used,
- how returns and volatility are created,
- what a prediction target is,
- why time-based splitting matters,
- why model comparison matters,
- why feature testing matters,
- why walk-forward backtesting is stronger than one split,
- why portfolio constraints are necessary,
- how model rankings become diversified recommendations.

## Current Recommendation For The App

The next implementation step is to connect the final portfolio outputs to the
Streamlit app:

```text
User chooses risk profile
App loads portfolio_recommendations.csv
App displays selected stocks, sector weights, expected return, and volatility
```

This would turn the project from a modeling pipeline into a usable demo.


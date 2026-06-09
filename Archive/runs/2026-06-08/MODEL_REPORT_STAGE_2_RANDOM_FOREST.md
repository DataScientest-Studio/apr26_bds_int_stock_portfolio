# Stage 2 Machine Learning Report: Random Forest Model

## 1. Why Add Random Forest?

The first modeling stage compared two models:

- a simple CPU Ridge regression model
- a ROCm/PyTorch neural network trained on the AMD GPU

The next logical beginner-friendly model is Random Forest.

Random Forest is useful because it sits between those two models:

| Model | Complexity | Beginner Interpretation |
|---|---|---|
| Ridge Regression | Low | Simple straight-line relationships |
| Random Forest | Medium | Many decision trees voting together |
| Neural Network | Higher | Flexible non-linear pattern learning |

Random Forest is especially popular for tabular data, which means data stored in
rows and columns. Our stock dataset is tabular.

The main question for this stage is:

> Does Random Forest improve our stock return ranking compared with Ridge and
> the ROCm neural network?

## 2. Reminder: What We Are Predicting

The target remains:

```text
target_63d_return
```

This means the stock's return over the next 63 trading days, roughly three
months.

The model receives only information that would have been known at the prediction
date:

- recent returns
- recent volatility
- recent volume
- drawdown
- sector
- history length

Then it tries to predict the future 63-day return.

## 3. Dataset Used

The same one-year S&P 500 dataset was used for all three models.

| Item | Value |
|---|---:|
| Stock universe | S&P 500 |
| Number of tickers | 503 |
| Date range | 2025-06-09 to 2026-06-05 |
| Price rows | 125,362 |
| Trading dates | 250 |
| Missing values in price columns | 0 |

The same time split was used:

| Split | Date Range | Rows |
|---|---|---:|
| Train | 2025-09-04 to 2026-01-20 | 47,554 |
| Test | 2026-01-21 to 2026-03-06 | 16,057 |

Using the same split is important. If each model used a different test period,
the comparison would not be fair.

## 4. How Random Forest Works

A Random Forest is made of many decision trees.

A decision tree asks a sequence of yes/no questions.

Example:

```text
Is ret_60d greater than 20%?
Is volatility_60d greater than 50%?
Is the stock in Information Technology?
Is drawdown_252d less than -10%?
```

Each tree makes its own prediction. The Random Forest averages the predictions
from many trees.

This helps because one tree can overfit easily. A forest of many trees is
usually more stable.

Beginner analogy:

> A single tree is one opinion. A Random Forest is a panel of many opinions.

## 5. Random Forest Settings

The model was trained with:

```text
n_estimators = 400
max_depth = 10
min_samples_leaf = 20
max_features = sqrt
```

What these mean:

| Setting | Meaning |
|---|---|
| `n_estimators=400` | Build 400 trees |
| `max_depth=10` | Do not let trees grow too deep |
| `min_samples_leaf=20` | Each final leaf must contain at least 20 examples |
| `max_features="sqrt"` | Each split only sees a random subset of features |

These settings are intentionally conservative. They reduce overfitting and make
the model more stable.

## 6. Output Files

The Random Forest training script created:

```text
models/random_forest_model.pkl
models/random_forest_metrics.csv
models/random_forest_predictions.csv
models/random_forest_latest_rankings.csv
models/random_forest_feature_importance.csv
```

The most important new file is:

```text
models/random_forest_feature_importance.csv
```

This tells us which features the model used most.

## 7. Model Comparison

### Metrics

| Metric | Ridge | Random Forest | ROCm PyTorch |
|---|---:|---:|---:|
| MAE | 0.1593 | 0.1421 | 0.1579 |
| RMSE | 0.2266 | 0.2129 | 0.2215 |
| Spearman rank correlation | 0.1386 | 0.2303 | 0.3404 |
| Top-5 average actual return | 0.5552 | 0.7099 | 0.8575 |

### What The Metrics Say

Random Forest had the best error metrics:

```text
Best MAE:  Random Forest
Best RMSE: Random Forest
```

That means Random Forest made the smallest average prediction errors.

The ROCm PyTorch model had the best ranking metrics:

```text
Best Spearman rank correlation: ROCm PyTorch
Best Top-5 average return:      ROCm PyTorch
```

That means the neural network did a better job ordering stocks from stronger to
weaker during the test period.

This is an important machine learning lesson:

> The model with the best prediction error is not always the model with the best
> recommendation ranking.

For a stock recommender, ranking quality may matter more than exact predicted
return.

## 8. Random Forest Feature Importance

Random Forest can tell us which features were most useful.

Top feature importances:

| Rank | Feature | Importance |
|---:|---|---:|
| 1 | `mean_return_60d` | 0.2223 |
| 2 | `ret_60d` | 0.1628 |
| 3 | `volatility_60d` | 0.1119 |
| 4 | `volatility_20d` | 0.1083 |
| 5 | `history_days` | 0.0637 |
| 6 | `sector_Energy` | 0.0476 |
| 7 | `log_avg_volume_20d` | 0.0438 |
| 8 | `mean_return_20d` | 0.0437 |
| 9 | `drawdown_252d` | 0.0385 |
| 10 | `ret_20d` | 0.0323 |

## 9. What Feature Importance Means

Feature importance answers:

> Which input columns helped the Random Forest make its decisions?

The most important features were 60-day return and 60-day average return. This
means the Random Forest relied heavily on medium-term momentum.

In plain English:

> Stocks that had already been moving strongly over the last few months were
> important for predicting the next few months.

Volatility was also important. The model did not only care about return. It also
used risk.

This matches the business goal of the project:

> A portfolio recommender should consider both return and risk.

## 10. What The Latest Random Forest Rankings Show

For the latest available date, 2026-06-05, the Random Forest model's top names
were:

| Rank | Ticker | Sector | Predicted 63-Day Return |
|---:|---|---|---:|
| 1 | DELL | Information Technology | 1.3434 |
| 2 | SNDK | Information Technology | 1.3017 |
| 3 | MU | Information Technology | 1.2015 |
| 4 | HPE | Information Technology | 1.1068 |
| 5 | INTC | Information Technology | 1.0513 |
| 6 | AMD | Information Technology | 0.9858 |
| 7 | STX | Information Technology | 0.8069 |
| 8 | ON | Information Technology | 0.7769 |
| 9 | DDOG | Information Technology | 0.7585 |
| 10 | QCOM | Information Technology | 0.6878 |

This is useful, but also risky.

Almost all top names are in Information Technology. The model is detecting a
strong pattern in that sector, but a real portfolio should not simply buy all
top-ranked names.

The recommender still needs sector limits.

## 11. What We Learned In Stage 2

### Lesson 1: Random Forest Is A Strong Tabular Baseline

Random Forest improved the prediction error compared with Ridge and the neural
network.

This shows why Random Forest is often a good second model after linear
regression.

### Lesson 2: Error And Ranking Are Different

Random Forest predicted returns more accurately on average.

The ROCm neural network ranked the best stocks better.

For this project, ranking is very important because the final product is a
recommender.

### Lesson 3: Momentum Is Dominating

The top features show that 60-day return and 60-day average return are driving a
lot of the Random Forest's decisions.

That means the current models are heavily momentum-based.

This can work in some markets, but it can fail when momentum reverses.

### Lesson 4: Diversification Is Still Missing

All three models tend to rank many Information Technology stocks highly.

This is not automatically wrong, but it creates concentration risk.

The machine learning model should be only one part of the system. The portfolio
construction layer still needs rules.

## 12. Which Model Should We Use Now?

For the next recommender prototype:

| Use Case | Best Current Choice |
|---|---|
| Most explainable baseline | Ridge |
| Best average prediction error | Random Forest |
| Best ranking / top-pick behavior | ROCm PyTorch |
| Best beginner teaching model | Random Forest |

Recommended practical choice:

> Use Random Forest as the main explainable ML model, and keep ROCm PyTorch as
> the more advanced comparison model.

Why:

- Random Forest is easier to explain.
- It has feature importance.
- It performed strongly.
- It trains quickly.
- It is less mysterious than the neural network.

But for ranking, we should keep watching the ROCm model because its top-pick
performance was better in this test.

## 13. Recommended Next Steps

### 1. Add A Model Comparison Table In Streamlit

Show:

- Ridge metrics
- Random Forest metrics
- ROCm PyTorch metrics
- top 10 latest predictions from each model

This will make the project easier to present.

### 2. Add Portfolio Construction

Convert rankings into a portfolio:

```text
select top names
apply max 30% sector exposure
apply max 20% single-stock weight
apply user risk profile
return final 5-10 stocks
```

### 3. Add Sector-Constrained Top Picks

Instead of showing the raw top 10, create a constrained ranking.

Example:

```text
No more than 3 stocks from the same sector in a 10-stock recommendation.
```

### 4. Add Walk-Forward Backtesting

One train/test split is not enough.

Use multiple time windows to test whether the model is stable.

Example:

```text
Train on one period -> test next month
Move forward
Repeat several times
Average the results
```

### 5. Add XGBoost

The next model to test should be XGBoost.

XGBoost is often very strong on tabular data. It may combine the strengths of
Random Forest and the ROCm neural network:

- strong prediction accuracy
- good ranking
- feature importance
- non-linear behavior

## 14. Final Stage 2 Summary

Stage 2 added a Random Forest model and compared it fairly against Ridge and the
ROCm PyTorch model.

The result:

- Random Forest had the best MAE and RMSE.
- ROCm PyTorch had the best ranking and top-5 return.
- Ridge remains the simplest baseline.
- Momentum and volatility are the most important current signals.
- The portfolio layer still needs diversification rules.

The most important beginner takeaway:

> A machine learning project should compare several models, but the "best" model
> depends on the business goal. For this project, ranking and portfolio behavior
> matter more than raw prediction error alone.


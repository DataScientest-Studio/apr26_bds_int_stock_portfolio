# Beginner-Friendly Report: Full 6-Year Stock Model Experiment

Run date: 2026-06-09

Experiment folder:

```text
mac-2026-06-09-full-6y
```

This report explains the full six-year experiment in plain language. It covers
what data was used, what each model tried to learn, what the numbers mean, and
why each model performed better or worse than the others.

This is an educational machine learning report, not financial advice.

## 1. What We Were Trying To Predict

The goal was to predict:

```text
target_63d_return
```

That means:

> If we look at a stock today, what return might it have about 63 trading days
> later?

There are about 21 trading days in a month, so 63 trading days is roughly three
market months.

Example:

```text
If a stock is $100 today and it is $110 after 63 trading days:
target_63d_return = 110 / 100 - 1 = 0.10
```

So a target value of `0.10` means `+10%`.

The models do not predict tomorrow's exact price. They try to rank stocks by
their expected three-month forward return.

## 2. The Data

The data came from Alpaca's IEX stock data feed and covered the current S&P 500
universe.

| Item | Value |
|---|---:|
| Stock universe | S&P 500 |
| Number of tickers | 503 |
| Date range | 2020-07-27 to 2026-06-08 |
| Trading dates | 1,474 |
| Price rows | 729,313 |
| Missing price values | 0 |
| Failed ticker downloads | 0 |

The calendar span is about `5.864` years. It is not exactly `6.000` years
because weekends, market holidays, and the current trading calendar affect the
actual rows we can retrieve.

Some S&P 500 companies have shorter histories because they are newer listings,
newer spin-offs, or newer index constituents. That is normal. For example,
`FDXF`, `Q`, `PSKY`, `SNDK`, `GEV`, `SOLV`, `VLTO`, `KVUE`, `GEHC`, and `WBD`
had the shortest histories in this run.

## 3. What One Data Row Means

Each row is one stock on one trading date.

Example rows from the real dataset:

| Date | Ticker | Open | High | Low | Close | Adjusted Close | Volume |
|---|---|---:|---:|---:|---:|---:|---:|
| 2026-06-05 | AAPL | 312.770 | 315.140 | 307.160 | 307.590 | 307.590 | 2,188,603 |
| 2026-06-08 | AAPL | 308.615 | 317.380 | 301.180 | 301.570 | 301.570 | 2,762,619 |
| 2026-06-05 | MSFT | 428.005 | 429.385 | 414.460 | 416.635 | 416.635 | 860,710 |
| 2026-06-08 | MSFT | 414.200 | 416.890 | 408.600 | 411.760 | 411.760 | 771,640 |
| 2026-06-05 | TPL | 398.975 | 400.490 | 386.770 | 389.750 | 389.750 | 15,417 |
| 2026-06-08 | TPL | 396.910 | 404.710 | 396.910 | 396.990 | 396.990 | 10,954 |

Column meanings:

| Column | Meaning |
|---|---|
| `date` | Trading day |
| `ticker` | Stock symbol |
| `open` | First traded price of the day |
| `high` | Highest traded price of the day |
| `low` | Lowest traded price of the day |
| `close` | Last traded price of the day |
| `adj_close` | Close price adjusted for corporate actions such as splits and dividends |
| `volume` | Number of shares traded |

The models mostly learn from `adj_close` and `volume`, plus sector metadata.

## 4. Features Created From The Data

Raw daily prices are not enough by themselves, so the scripts create features.
A feature is an input column given to a model.

Important features:

| Feature | Simple Meaning |
|---|---|
| `ret_5d` | Stock return over the last 5 trading days |
| `ret_20d` | Stock return over the last 20 trading days |
| `ret_60d` | Stock return over the last 60 trading days |
| `mean_return_20d` | Average recent return, annualized from the last 20 days |
| `mean_return_60d` | Average recent return, annualized from the last 60 days |
| `volatility_20d` | How jumpy the stock was over the last 20 days |
| `volatility_60d` | How jumpy the stock was over the last 60 days |
| `log_avg_volume_20d` | Recent trading volume, compressed with a log transform |
| `drawdown_252d` | How far the stock is below its recent one-year high |
| `sector_*` | One-hot encoded sector labels, such as Energy or Technology |
| `history_days` | How many rows of history that ticker has in the dataset |

`history_days` is useful to test, but risky. It can become a shortcut. A model
may learn that newer or older listings behave differently instead of learning a
real price pattern. That is why we also trained versions without it.

## 5. Train/Test Split

The fixed-split models used old data for training and newer data for testing.

| Split | Date Range | Meaning |
|---|---|---|
| Train | 2020-10-20 to 2024-12-31 | The model learned from this period |
| Test | 2025-01-02 to 2026-03-09 | The model was evaluated on this later period |
| Split date | 2025-01-01 | Everything before this was training data |

This matters because stock prediction must respect time. We should not train on
future data and then pretend we predicted the past.

## 6. How To Read The Metrics

| Metric | Beginner Meaning | Better Direction |
|---|---|---|
| MAE | Average absolute prediction error | Lower is better |
| RMSE | Like MAE, but punishes large mistakes more | Lower is better |
| Spearman rank correlation | Whether the model ranks winners above losers | Higher is better |
| Test universe average actual return | Average return of all tested stocks | Baseline comparison |
| Top-5 average actual return | Actual return of the model's top 5 picks each date | Higher is better |

For this project, ranking quality matters a lot. The app is not just asking:

```text
What exact return will this stock have?
```

It is asking:

```text
Which stocks should be ranked near the top?
```

So `Spearman rank correlation` and `Top-5 average actual return` are especially
important.

## 7. Models Used

### Model 1: Ridge Regression Baseline

Ridge Regression is a simple linear model.

In beginner terms:

> Ridge learns a weighted formula. Each feature gets a weight. The model adds
> those weighted features together to estimate the future return.

Example idea:

```text
prediction =
  weight_1 * ret_60d
+ weight_2 * volatility_60d
+ weight_3 * drawdown_252d
+ sector weights
+ ...
```

Ridge is intentionally simple. It is useful as a baseline because if a more
advanced model cannot beat Ridge, the advanced model may not be worth using yet.

Result:

| Metric | Value |
|---|---:|
| MAE | 0.133983 |
| RMSE | 0.203068 |
| Spearman rank correlation | 0.163658 |
| Top-5 average actual return | 0.342729 |

Why it was good:

- It had the best rank correlation.
- It had the best fixed-split top-5 actual return.
- It is simple, stable, and less likely to overfit complex noise.

Why it is limited:

- It can only learn mostly straight-line relationships.
- It may miss interactions like "high momentum is good only in certain sectors"
  or "drawdown means different things when volatility is high."

### Model 2: Random Forest

Random Forest is a group of many decision trees.

In beginner terms:

> A decision tree asks a sequence of yes/no questions. A Random Forest builds
> many trees and averages their answers.

Example tree-style questions:

```text
Is volatility_60d above 0.50?
Is drawdown_252d below -0.20?
Is the stock in the Energy sector?
Was ret_60d positive?
```

Result:

| Metric | Value |
|---|---:|
| MAE | 0.134929 |
| RMSE | 0.207194 |
| Spearman rank correlation | 0.083394 |
| Top-5 average actual return | 0.216048 |

Why it was worse than Ridge:

- It had lower rank correlation.
- Its top-5 picks performed worse than Ridge's top-5 picks.
- Its most important feature was `history_days`, which is a warning sign.

The top feature importance was:

```text
history_days = 0.472489
```

That means the model leaned heavily on how much history a ticker had. This can
work in a backtest, but it may not be a reliable financial signal.

Why it was still useful:

- It can learn non-linear patterns.
- It is easy to explain compared with a neural network.
- It gave us a reason to test a cleaner version without `history_days`.

### Model 3: Random Forest Without `history_days`

This is the same Random Forest idea, but it removes the suspicious
`history_days` feature.

Result:

| Metric | Value |
|---|---:|
| MAE | 0.135090 |
| RMSE | 0.204795 |
| Spearman rank correlation | 0.110156 |
| Top-5 average actual return | 0.300670 |

Why it was better than the original Random Forest:

- Top-5 actual return improved from `0.216048` to `0.300670`.
- Spearman rank correlation improved from `0.083394` to `0.110156`.
- RMSE improved from `0.207194` to `0.204795`.
- The model no longer relied on the questionable `history_days` shortcut.

Why it was worse than Ridge:

- Ridge still had better rank correlation: `0.163658` vs `0.110156`.
- Ridge still had better top-5 actual return: `0.342729` vs `0.300670`.
- The no-history Random Forest had slightly worse MAE than Ridge.

Why it remains a strong practical model:

- It is more flexible than Ridge.
- It avoids the `history_days` issue.
- It performed well in the walk-forward backtest.
- Its logic is still explainable through feature importance.

Latest top-ranked examples from this model:

| Date | Ticker | Sector | Predicted 63-Day Return | Volatility 60D | Return 60D |
|---|---|---|---:|---:|---:|
| 2026-06-08 | TPL | Energy | 0.215887 | 0.548681 | -0.249433 |
| 2026-06-08 | COHR | Information Technology | 0.160523 | 0.860106 | 0.668784 |
| 2026-06-08 | NTAP | Information Technology | 0.153790 | 0.609585 | 0.765962 |
| 2026-06-08 | TER | Information Technology | 0.143627 | 0.832929 | 0.306997 |
| 2026-06-08 | CIEN | Information Technology | 0.142463 | 0.835516 | 0.382020 |

These are predictions, not guaranteed outcomes.

### Model 4: XGBoost Without `history_days`

XGBoost is also tree-based, but it builds trees in a sequence. Each new tree
tries to fix errors from the previous trees.

In beginner terms:

> Random Forest builds many trees independently. XGBoost builds trees like a
> correction chain, where each tree tries to improve the model.

Result:

| Metric | Value |
|---|---:|
| MAE | 0.137294 |
| RMSE | 0.209521 |
| Spearman rank correlation | 0.059633 |
| Top-5 average actual return | 0.179273 |

Why it was worse here:

- It had the worst MAE among the non-neural fixed-split models.
- It had the worst RMSE among the non-neural fixed-split models.
- Its rank correlation was lower than Ridge and both Random Forest versions.
- Its top-5 actual return was much lower than Ridge and no-history Random
  Forest.

Why that can happen:

- XGBoost is powerful, but powerful models can overfit noisy financial data.
- Stock returns are very noisy compared with many normal tabular problems.
- The current hyperparameters may not be tuned enough for this dataset.

This does not mean XGBoost is bad. It means this specific XGBoost setup did not
win on this experiment.

### Model 5: ROCm PyTorch Neural Network

The neural network was a small PyTorch MLP trained on an AMD ROCm GPU:

```text
AMD Radeon(TM) 8060S Graphics
```

In beginner terms:

> A neural network learns layers of mathematical transformations. It can model
> complex patterns, but it needs careful tuning and can perform badly if the
> signal is weak or noisy.

Result:

| Metric | Value |
|---|---:|
| MAE | 0.341667 |
| RMSE | 0.430318 |
| Spearman rank correlation | -0.020311 |
| Top-5 average actual return | 0.178616 |

Why it was worse:

- It had by far the largest prediction error.
- Its rank correlation was negative, meaning its ranking was slightly worse
  than random in this fixed test.
- Its top-5 return was close to XGBoost but far below Ridge and no-history
  Random Forest.

Why this happened:

- The neural network may need better tuning.
- It may need more careful feature scaling, architecture changes, or regularization.
- Financial returns are noisy, so a flexible model can learn noise instead of
  useful signal.
- A GPU makes training faster, but it does not automatically make the model
  better.

The main lesson:

> More advanced technology does not automatically mean better predictions.

## 8. Fixed-Split Model Comparison

| Model | MAE | RMSE | Spearman Rank Corr | Top-5 Avg Actual Return |
|---|---:|---:|---:|---:|
| Ridge baseline | 0.133983 | 0.203068 | 0.163658 | 0.342729 |
| Random Forest | 0.134929 | 0.207194 | 0.083394 | 0.216048 |
| Random Forest, no `history_days` | 0.135090 | 0.204795 | 0.110156 | 0.300670 |
| XGBoost, no `history_days` | 0.137294 | 0.209521 | 0.059633 | 0.179273 |
| ROCm PyTorch MLP | 0.341667 | 0.430318 | -0.020311 | 0.178616 |

Best by metric:

| Metric | Winner | Why |
|---|---|---|
| MAE | Ridge | Lowest average prediction error |
| RMSE | Ridge | Lowest large-error penalty |
| Spearman rank correlation | Ridge | Best ranking relationship |
| Top-5 average actual return | Ridge | Best fixed-split top-pick result |
| Best explainable tree model | Random Forest without `history_days` | Strong result without the shortcut feature |

## 9. Walk-Forward Backtest

The fixed split tests one large train period and one later test period. That is
useful, but it can be lucky or unlucky depending on the exact dates.

The walk-forward backtest is stricter:

1. Train on an early historical window.
2. Test on the next 63 trading days.
3. Move forward.
4. Train again with more history.
5. Repeat.

Walk-forward result for Random Forest without `history_days`:

| Metric | Value |
|---|---:|
| Folds | 13 |
| Mean MAE | 0.121582 |
| Mean RMSE | 0.179460 |
| Mean Spearman rank correlation | 0.061784 |
| Mean universe actual return | 0.047126 |
| Mean top-5 actual return | 0.181969 |
| Mean top-10 actual return | 0.146203 |
| Top-5 beat universe folds | 9 out of 13 |

Why this matters:

- The top-5 picks beat the universe average in most folds.
- The result is not based on only one train/test cut.
- This makes the no-history Random Forest more credible as a practical
  recommender model.

Why the walk-forward top-5 return is lower than the fixed-split top-5 return:

- Walk-forward tests many different market periods.
- Some periods are harder than others.
- It gives less room for one lucky period to dominate the conclusion.

So the fixed-split Ridge result is very strong, but the walk-forward Random
Forest result is a more realistic view of repeatability.

## 10. Portfolio Construction

A model ranking is not yet a portfolio.

If we simply picked the highest-ranked stocks, the result could be too
concentrated in one sector. The portfolio layer adds simple rules:

| Rule | Value |
|---|---:|
| Stocks per portfolio | 10 |
| Weighting | Equal weight |
| Weight per stock | 10% |
| Maximum sector weight | 30% |
| Risk profiles | Conservative, balanced, aggressive |

The portfolio layer used:

```text
Random Forest without history_days
```

Why this model was used for portfolios:

- It avoids the suspicious `history_days` feature.
- It performs strongly enough to be useful.
- It is explainable.
- It has a walk-forward result, not just one fixed-split result.

Portfolio summary:

| Profile | Expected 63-Day Return | Avg 60-Day Volatility | Sectors | Max Sector Weight |
|---|---:|---:|---:|---:|
| Conservative | 0.067699 | 0.284227 | 6 | 0.30 |
| Balanced | 0.083820 | 0.405860 | 5 | 0.30 |
| Aggressive | 0.126650 | 0.535236 | 5 | 0.30 |

This behaves as expected:

- Conservative has the lowest expected return and lowest volatility.
- Balanced sits in the middle.
- Aggressive has the highest expected return and highest volatility.

## 11. Final Beginner Takeaway

The most important lesson is:

> The best model is not always the most complex model.

In this experiment:

- Ridge was the best fixed-split model.
- Random Forest without `history_days` was the best practical tree model.
- XGBoost did not beat the simpler models.
- The ROCm neural network performed poorly despite using GPU training.
- Walk-forward testing made the no-history Random Forest look more reliable
  than a single fixed split alone would show.

Recommended interpretation:

| Use Case | Best Choice |
|---|---|
| Simple benchmark | Ridge |
| Main explainable recommender model | Random Forest without `history_days` |
| More realistic validation view | Walk-forward Random Forest without `history_days` |
| Experimental advanced model | ROCm PyTorch MLP |
| Needs more tuning before use | XGBoost and ROCm PyTorch MLP |

The current best practical app model is still:

```text
Random Forest without history_days
```

The reason is not that it won every metric. It did not. The reason is that it
balances performance, explainability, and cleaner feature design better than the
other production-candidate models.


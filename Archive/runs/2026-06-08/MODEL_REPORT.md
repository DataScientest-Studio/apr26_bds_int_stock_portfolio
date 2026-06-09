# Machine Learning Report: First Stock Return Models

## 1. Project Goal

The goal of this project is to build a beginner-friendly stock portfolio
recommender.

The recommender should eventually help a user choose a small portfolio of
stocks based on their risk profile. To get there, we first trained models that
try to answer a simpler machine learning question:

> Given what a stock has done recently, can we estimate its return over the next
> 63 trading days?

63 trading days is roughly three months of stock-market activity. This is the
target the models are trying to predict.

This is not financial advice and not a production trading system. It is a first
machine learning experiment that shows how to turn stock-market data into
features, train models, evaluate them, and learn from the results.

## 2. Data Used

The data was downloaded from Alpaca's IEX stock-market feed.

Current dataset:

| Item | Value |
|---|---:|
| Stock universe | S&P 500 |
| Number of tickers | 503 |
| Date range | 2025-06-09 to 2026-06-05 |
| Trading dates | 250 |
| Long price rows | 125,362 |
| Wide price table shape | 250 dates x 503 tickers |
| Missing values in price columns | 0 |

The main file is:

```text
data/prices_long.csv
```

Each row represents one stock on one trading day.

Example row meaning:

```text
date = trading day
ticker = stock symbol
open = first traded price of the day
high = highest traded price of the day
low = lowest traded price of the day
close = closing price
adj_close = adjusted closing price
volume = number of shares traded
```

The metadata file is:

```text
data/tickers.csv
```

This contains the company name, sector, industry, index, and country for each
ticker.

## 3. Sector Distribution

The stocks are not evenly distributed across sectors.

| Sector | Stocks |
|---|---:|
| Industrials | 80 |
| Financials | 76 |
| Information Technology | 72 |
| Health Care | 59 |
| Consumer Discretionary | 48 |
| Consumer Staples | 36 |
| Utilities | 31 |
| Real Estate | 31 |
| Materials | 26 |
| Communication Services | 23 |
| Energy | 21 |

This matters because a recommender that simply picks the highest-scoring stocks
could easily become concentrated in one sector. In the latest predictions, many
of the highest-ranked stocks are in Information Technology. That may look
attractive from a pure return perspective, but it creates concentration risk.

For a real recommender, we should add rules such as:

```text
No sector may be more than 30% of the portfolio.
```

## 4. Why `adj_close` Matters

The project uses `adj_close` to calculate returns.

This is important because raw closing prices can be distorted by stock splits,
dividends, and other corporate actions. Adjusted close is designed to make price
history more comparable over time.

For example, if a company does a stock split, the raw price may suddenly drop,
but that does not mean investors lost that amount of money. Adjusted close helps
avoid treating those mechanical changes as real losses.

For machine learning, cleaner input data usually leads to more meaningful
features.

## 5. Features Created For The Models

Raw prices are not directly enough for most machine learning models. We need to
convert prices into features.

A feature is an input column that helps the model make a prediction.

The model used these features:

| Feature | Beginner Explanation |
|---|---|
| `ret_5d` | Return over the last 5 trading days |
| `ret_20d` | Return over the last 20 trading days |
| `ret_60d` | Return over the last 60 trading days |
| `mean_return_20d` | Average recent daily return, annualized |
| `mean_return_60d` | Average medium-term daily return, annualized |
| `volatility_20d` | Recent risk level based on daily movement |
| `volatility_60d` | Medium-term risk level |
| `log_avg_volume_20d` | Recent trading volume, log-transformed |
| `drawdown_252d` | How far the stock is below its recent high |
| `history_days` | How many rows of history are available for that stock |
| sector columns | One-hot encoded sector information |

### Return Features

Return features answer:

> Has this stock been going up or down recently?

For example:

```text
ret_60d = current adjusted close / adjusted close 60 days ago - 1
```

If `ret_60d = 0.20`, the stock gained about 20% over the last 60 trading days.

### Volatility Features

Volatility is used as a risk measure.

High volatility means the stock moves up and down strongly. Low volatility means
the stock is more stable.

For a beginner investor, volatility is often easier to understand as:

> How wild is the ride?

### Volume Feature

Volume tells us how actively a stock is traded.

The model uses `log_avg_volume_20d` instead of raw volume because volume is very
skewed. Some stocks trade much more than others. A log transform compresses
large values so they do not dominate the model too much.

### Drawdown Feature

Drawdown measures how far a stock has fallen from a recent high.

Example:

```text
drawdown = -0.25
```

This means the stock is 25% below its recent high.

Drawdown can help the model recognize stocks that are recovering, crashing, or
still near their highs.

## 6. Target Variable

The target is what the model tries to predict.

In this project, the target is:

```text
target_63d_return
```

This means:

> The stock's return over the next 63 trading days.

Formula:

```text
target_63d_return =
    adjusted close 63 trading days in the future / current adjusted close - 1
```

Example:

```text
target_63d_return = 0.10
```

This means the stock went up 10% over the following 63 trading days.

The model does not see this future value during prediction. It only uses past
features and then learns from historical examples where the future is already
known.

## 7. Train/Test Split

The data was split by time, not randomly.

This is important for financial data.

A random split would mix past and future rows. That can make the model look
better than it really is because it may indirectly learn from future market
conditions.

The actual split used was:

| Split | Date Range | Rows |
|---|---|---:|
| Train | 2025-09-04 to 2026-01-20 | 47,554 |
| Test | 2026-01-21 to 2026-03-06 | 16,057 |

The training set is used to fit the model.

The test set is held back until evaluation. It simulates asking:

> If we trained on older data, how well would the model work on newer data?

Because the project currently uses a 63-day forward target, the latest dates
cannot be used for supervised evaluation. We do not yet know their 63-day future
return inside this dataset.

## 8. Models Trained

Two models were trained.

### Model 1: CPU Ridge Regression

The first model is a Ridge regression baseline.

Ridge regression is a linear model. It tries to fit a relationship like:

```text
predicted return =
    weight_1 * feature_1
  + weight_2 * feature_2
  + ...
  + intercept
```

It is a good first model because it is:

- simple
- fast
- stable
- easier to explain than a neural network

The Ridge model runs on CPU.

Output files:

```text
models/first_model.pkl
models/model_metrics.csv
models/predictions.csv
models/latest_rankings.csv
```

### Model 2: ROCm PyTorch Neural Network

The second model is a small neural network trained with PyTorch on the AMD GPU.

It uses the ROCm stack on:

```text
AMD Radeon(TM) 8060S Graphics
```

The network architecture is:

```text
input features
-> dense layer with 64 units
-> ReLU
-> dropout
-> dense layer with 32 units
-> ReLU
-> output predicted return
```

This model can learn non-linear relationships. That means it can learn patterns
that are more complex than a straight line.

Output files:

```text
models/rocm_model.pt
models/rocm_model_metrics.csv
models/rocm_predictions.csv
models/rocm_latest_rankings.csv
models/rocm_training_history.json
```

## 9. Evaluation Metrics

Several metrics were used.

### MAE

Mean Absolute Error.

This measures the average size of the prediction error.

Lower is better.

Example:

```text
MAE = 0.15
```

This means the model's prediction is off by about 15 percentage points on
average.

### RMSE

Root Mean Squared Error.

This also measures prediction error, but it punishes large mistakes more than
MAE does.

Lower is better.

### Spearman Rank Correlation

This measures whether the model ranks stocks in a useful order.

This matters because the recommender does not need a perfect prediction for
every stock. It mainly needs to rank better stocks above worse stocks.

Interpretation:

| Spearman Value | Meaning |
|---:|---|
| near 1 | model ranking is very good |
| near 0 | ranking is mostly random |
| below 0 | ranking is wrong on average |

### Top-5 Average Actual Return

For each test date, we selected the top 5 stocks according to the model's
predicted return. Then we looked at what those stocks actually returned.

This is closer to the business use case:

> If the recommender picked the top stocks, how did those picks perform?

## 10. Results

### Metric Comparison

| Metric | CPU Ridge | ROCm PyTorch |
|---|---:|---:|
| MAE | 0.1593 | 0.1579 |
| RMSE | 0.2266 | 0.2215 |
| Spearman rank correlation | 0.1386 | 0.3404 |
| Test universe average actual return | 0.0249 | 0.0249 |
| Top-5 average actual return | 0.5552 | 0.8575 |

The ROCm PyTorch model performed better on this run.

The most important improvement is the Spearman rank correlation:

```text
CPU Ridge:    0.1386
ROCm PyTorch: 0.3404
```

This suggests that the neural network was better at ranking stocks from better
to worse during the test period.

## 11. What The Latest Rankings Show

The models also produced predictions for the latest available date:

```text
2026-06-05
```

The CPU Ridge model's highest predicted names included:

| Rank | Ticker | Sector | Predicted 63-Day Return |
|---:|---|---|---:|
| 1 | DELL | Information Technology | 0.8604 |
| 2 | SNDK | Information Technology | 0.7224 |
| 3 | AMD | Information Technology | 0.6395 |
| 4 | MU | Information Technology | 0.5815 |
| 5 | INTC | Information Technology | 0.5802 |

The ROCm PyTorch model's highest predicted names included:

| Rank | Ticker | Sector | Predicted 63-Day Return |
|---:|---|---|---:|
| 1 | LITE | Information Technology | 2.5528 |
| 2 | SMCI | Information Technology | 2.1517 |
| 3 | GLW | Information Technology | 1.6217 |
| 4 | TER | Information Technology | 1.3917 |
| 5 | CIEN | Information Technology | 1.3687 |

These are very aggressive predictions. A beginner should not interpret them as
guaranteed future returns.

They are better understood as model scores:

> The model thinks these stocks have strong recent patterns compared with the
> rest of the universe.

The concentration in Information Technology is also a warning sign. The model is
finding momentum and volatility patterns, but a portfolio recommender still
needs diversification rules.

## 12. What We Can Learn

### Lesson 1: Data Preparation Is Most Of The Work

The model did not train directly on raw CSV files.

We first had to:

- download the data
- check missing values
- calculate returns
- create rolling features
- create the future target
- split data by time
- scale numeric features

This is normal in machine learning. The model is only one part of the pipeline.

### Lesson 2: Avoid Random Splits In Time-Series Problems

Stock data has a time order.

Training on future data and testing on past data would not make sense. The
model should learn from the past and be evaluated on the future.

This is why a time-based split was used.

### Lesson 3: Ranking Can Matter More Than Exact Prediction

For a recommender, the model does not need to predict every return exactly.

It needs to help answer:

> Which stocks look better than others?

That is why Spearman rank correlation and top-5 average return are important.

The ROCm PyTorch model only slightly improved MAE and RMSE, but it improved the
ranking metric much more.

### Lesson 4: A Good ML Score Is Not A Portfolio Yet

The latest rankings are heavily concentrated in Information Technology.

A real portfolio recommender needs extra rules:

- maximum sector exposure
- maximum single-stock weight
- minimum liquidity
- user risk profile
- volatility limits
- maybe exclusion of very short-history stocks

The ML model gives a score. The recommender must turn that score into a balanced
portfolio.

### Lesson 5: GPU Training Works, But It Is Not Automatically Better

The ROCm model uses the AMD GPU successfully.

However, GPU support by itself does not guarantee a better model. The model
still needs:

- enough data
- useful features
- good validation
- tuning
- regularization

In this run, the PyTorch GPU model outperformed the CPU Ridge baseline. But we
should still compare models carefully and avoid assuming the most complex model
is always best.

## 13. Main Risks And Limitations

### Short History Window

The dataset only covers one year.

That means the model mostly learns from one market regime. It may not understand
other environments, such as:

- market crashes
- high inflation periods
- low-rate bull markets
- recession periods
- sector rotations

A stronger model should train on more years of data if possible.

### IEX Feed Limitation

The data comes from Alpaca's IEX feed. This is useful for a course project, but
it is not the same as full consolidated market data.

Volume and price behavior may differ from full-market data.

### Survivorship Bias

The ticker list comes from the current S&P 500. This means the dataset may not
include companies that were removed from the index in the past.

This can make historical testing look better than reality.

### High Predictions Need Constraints

Some predicted returns are extremely high.

This does not mean the stocks will actually return that much. It means the model
is extrapolating from recent patterns.

In finance, extreme model outputs should usually be capped, calibrated, or
treated as ranking scores rather than literal forecasts.

### Test Period Is Still Small

The test set runs from 2026-01-21 to 2026-03-06.

That is a useful first test, but it is not enough to prove the model is robust.
We need more backtesting windows.

## 14. Recommended Next Steps

### 1. Add Portfolio Constraints

Turn model scores into a realistic portfolio:

```text
5 to 10 stocks
max 30% per sector
max 20% per single stock
exclude stocks above user risk limit
```

### 2. Add User Risk Profiles

Create risk profiles such as:

| Profile | Rule Example |
|---|---|
| Conservative | lower volatility, more defensive sectors |
| Balanced | medium volatility, sector-diversified |
| Aggressive | higher volatility allowed, stronger return focus |

### 3. Compare More Models

Recommended comparison:

- Ridge regression
- Random Forest
- XGBoost
- PyTorch neural network

All models should use the same train/test split so the comparison is fair.

### 4. Add Walk-Forward Backtesting

Instead of one train/test split, use multiple time windows.

Example:

```text
Train on months 1-6, test month 7
Train on months 2-7, test month 8
Train on months 3-8, test month 9
```

This gives a better view of model stability.

### 5. Improve Features

Possible new features:

- sector-relative momentum
- market-relative return
- beta vs. S&P 500 ETF
- maximum drawdown over 60 days
- volatility change
- moving-average crossover signals
- recent earnings or fundamental data if available

## 15. Final Summary

This project now has a working machine learning pipeline:

1. Download one year of S&P 500 stock data.
2. Build return, risk, volume, drawdown, and sector features.
3. Create a 63-trading-day future return target.
4. Split the data by time.
5. Train a simple CPU Ridge baseline.
6. Train a ROCm PyTorch model on the AMD Strix Halo GPU.
7. Compare the models with prediction and ranking metrics.

The latest result shows that the ROCm PyTorch model performed better than the
CPU Ridge baseline on the current one-year dataset, especially for ranking.

The most important beginner takeaway:

> Machine learning for investing is not just about predicting prices. It is
> about building a careful pipeline, avoiding time leakage, measuring ranking
> quality, and turning model scores into diversified decisions.


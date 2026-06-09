# Full 6-Year Experiment: All Models

Experiment folder:

```text
mac-2026-06-09-full-6y
```

Run date: 2026-06-09

## Dataset

The experiment fetched the full six-year Alpaca IEX window available at run time.

| Item | Value |
|---|---:|
| Universe | S&P 500 |
| Tickers | 503 |
| Date range | 2020-07-27 to 2026-06-08 |
| Calendar span | 5.864 years |
| Trading dates | 1,474 |
| Price rows | 729,313 |
| Missing OHLCV/adjusted-close values | 0 |
| Failed ticker download file | Not created |

Some newer constituents have shorter histories, which is expected. The shortest
histories in this run were `FDXF`, `Q`, `PSKY`, `SNDK`, `GEV`, `SOLV`, `VLTO`,
`KVUE`, `GEHC`, and `WBD`.

## Fixed-Split Model Results

All fixed-split models used:

```text
Train: 2020-10-20 to 2024-12-31
Test:  2025-01-02 to 2026-03-09
Split: 2025-01-01
Target: 63-trading-day forward return
```

| Model | MAE | RMSE | Spearman Rank Corr | Test Universe Avg Return | Top-5 Avg Actual Return |
|---|---:|---:|---:|---:|---:|
| Ridge baseline | 0.133983 | 0.203068 | 0.163658 | 0.042787 | 0.342729 |
| Random Forest | 0.134929 | 0.207194 | 0.083394 | 0.042787 | 0.216048 |
| Random Forest, no `history_days` | 0.135090 | 0.204795 | 0.110156 | 0.042787 | 0.300670 |
| XGBoost, no `history_days` | 0.137294 | 0.209521 | 0.059633 | 0.042787 | 0.179273 |
| ROCm PyTorch MLP | 0.341667 | 0.430318 | -0.020311 | 0.042787 | 0.178616 |

## Walk-Forward Backtest

The walk-forward Random Forest without `history_days` retrained on expanding
history and tested 63-trading-day windows.

| Metric | Value |
|---|---:|
| Folds | 13 |
| Mean MAE | 0.121582 |
| Mean RMSE | 0.179460 |
| Mean Spearman rank correlation | 0.061784 |
| Mean universe actual return | 0.047126 |
| Mean top-5 actual return | 0.181969 |
| Mean top-10 actual return | 0.146203 |
| Top-5 beat universe folds | 9 |

## Recommendation Portfolios

Portfolio construction used the Random Forest without `history_days` latest
rankings from 2026-06-08.

| Profile | Expected 63-Day Return | Avg 60-Day Volatility | Sectors | Max Sector Weight | Volatility Cap Relaxed |
|---|---:|---:|---:|---:|---|
| Conservative | 0.067699 | 0.284227 | 6 | 0.30 | False |
| Balanced | 0.083820 | 0.405860 | 5 | 0.30 | False |
| Aggressive | 0.126650 | 0.535236 | 5 | 0.30 | False |

## Output Files

Key generated outputs:

```text
data/prices_long.csv
data/prices_close_wide.csv
models/model_metrics.csv
models/random_forest_metrics.csv
models/random_forest_no_history_metrics.csv
models/xgboost_no_history_metrics.csv
models/rocm_model_metrics.csv
models/walk_forward_rf_no_history_summary.csv
models/portfolio_recommendations.csv
models/portfolio_summary.csv
```

## Takeaway

The fixed-split Ridge baseline had the best rank correlation and top-5 average
actual return on this six-year run. The Random Forest without `history_days`
remains the strongest practical tree model because it avoids the known
`history_days` shortcut and still delivers strong top-5 results. The
walk-forward test remains the more realistic validation view, where the
no-history Random Forest top-5 beat the universe in 9 of 13 folds.

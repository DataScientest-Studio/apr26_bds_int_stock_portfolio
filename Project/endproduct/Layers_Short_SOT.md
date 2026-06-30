# Layers Short SOT — Minimal Feature Namespace Pipeline

This is the source of truth for the implemented per-asset pipeline. The scope is
limited to `Plan/` and `Project/`.

## Layer Map

| Layer | Name | Contract |
|---|---|---|
| L1 | Alpaca OHLCV Download | Upstream provenance. Raw 1h OHLCV came from Alpaca Market Data API. |
| L2 | ZIP Archive / Seed Export | Upstream provenance. One archive per ticker was exported to `data/seed/<TICKER>_ohlcv_1h.parquet`. |
| L3 | DuckDB Build | `build_db.py` loads all seed parquets into `liora.duckdb`, table `bars_1h`. |
| L4 | Parquet 1h / 1d / 1w | The notebook reads DuckDB, writes clean 1h OHLCV, then deterministic 1d and 1w roll-ups. |
| L5 | Time Split | Warmup / Train / OOS split with purge and embargo. OOS stays unread until the verdict step. |
| L6 | Features + Triple Barrier Y | Candidate bars use 1h momentum for side, Features come from namespaces, Y is symmetric ATR Triple Barrier. |
| L7 | Optuna HPO + Kelly | Optuna tunes XGB on Train CV AUC-PR; Kelly is calibrated on Train out-of-fold log-growth. |
| L8 | XGB Strategy Artifact | XGB trains on full Train and is embedded as base64 in `strategy_<TICKER>.py`. |
| L9 | OOS Endproduct | OOS verdict, dashboard row, README, and final seven-file asset folder. |

## Feature Namespaces

The model input order is deterministic:

1. `01-99`: `features_1h`
2. `101-199`: `features_1d`
3. `201-299`: `features_1w`
4. `901-999`: `multi_tf`

Each registry uses a single `features` list with `id`, `name`, `implemented`,
`formula`, and `unit`. The active manifest is resolved from
`Project/Structure/config/feature_namespaces.json`.

The current feature families are returns, SMA/MA distances, volume z-score,
ATR percent, realized volatility, RSI, Bollinger Bands, MACD, and simple
multi-timeframe alignment/spread ratios. Daily and weekly features are computed
on completed roll-up bars and projected as-of to the 1h decision timestamp.
Multi-timeframe features are pure functions of already projected 1h/1d/1w
feature values.

## Candidate And Label Contract

Every eligible 1h bar can become a candidate. The candidate side is:

`direction = sign(log_return_5)`

`0`, missing, infinite, or insufficient-history values are skipped.

The label `Y_outcome` is `TripleBarrier.ATR.v1`:

- entry: `open[t0+1]`
- width: `ATR14[t0] * TB_ATR_MULTIPLIER`
- target: `entry + direction * width`
- stop: `entry - direction * width`
- horizon: `H=24`
- trigger clock: close-based
- condition fill: next open
- scheduled fill: close at the time barrier

## Operator Surface

```bash
cd Project/Structure
make build-db
make run-asset TICKER=AAPL
make loop "AAPL TSLA XOM"
make dashboard
make on
```

## Seven-File Asset Contract

Each `Assets/<TICKER>/` folder contains:

1. `<T>__L4_to_L9.ipynb`
2. `<T>_ohlcv_1h.parquet`
3. `<T>_ohlcv_1d.parquet`
4. `<T>_ohlcv_1w.parquet`
5. `OPTUNAs_XGB_HPOs_best_params.json`
6. `strategy_<T>.py`
7. `<T>_README.md`

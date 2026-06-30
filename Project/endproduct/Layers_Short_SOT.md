# Layers Short SOT — data acquisition (1.3–1.5) + 9 layers (1.6 → 4.2)

Source of truth for the implemented pipeline. The runner notebook (`notebook_template.ipynb`, executed
by `run_asset.py`) runs layers 1.6 → 4.2 in order for one ticker; the input step 1.5 (`build_db.py`)
builds the shared input once beforehand (`make build-db`). Layers **1.3–1.4 are data provenance
(upstream) — NOT this repo's code**: they show where the parquets in `data/seed/` came from. All the
math lives in `Project/Structure/pipeline.py`; the deliverable files are written by `asset_writers.py`
and the notebook.

Frozen knobs (`config/pipeline_parameters.json`): `H=24`, `PURGE_CANDLES=24`, `EMBARGO_BARS=35`,
`THRESHOLD_ENTRY=0.6`, `W_ATR=14`, `W_VOL=20`, `MIN_TOUCHES=2`, `N_TRIALS=200`, CV `k=4` purged
walk-forward, `RANDOM_SEED=42`, `XGBOOST_N_JOBS=1`, `INITIAL_CAPITAL_USD=1000`, `COMMISSION_BPS=1`,
`SLIPPAGE_BPS=2`. Splits: warmup `2016-01-04 → 2016-10-14`, train `2016-10-17 → 2023-12-29`,
OOS `2024-01-02 → 2026-05-29`.

## Data section

### 1.3 — Acquisition: Alpaca (provenance, upstream)
Raw 1h OHLCV was downloaded from the **Alpaca Market Data API** (`feed=sip`) **upstream / offline — not
through this repo**. This repo is self-contained: no live API call, no key, no fetch code — it ships the
ready parquets. Shown in the visualization as the data's origin.

### 1.4 — Archive: QuantConnect / LEAN → export to data/seed (provenance, upstream)
The raw OHLCV was held in **QuantConnect / LEAN** format (1 zip = 1 ticker) and **exported once** to
`data/seed/<TICKER>_ohlcv_1h.parquet` — exactly the files this repo ships. Also provenance (upstream),
not this repo's code.

### 1.5 — Data source in the repo (build_db.py)
`build_db.py` (operator step `make build-db`, **outside** `pipeline.py`) loads the raw 1h OHLCV from
`data/seed/*_ohlcv_1h.parquet` into `liora.duckdb` — one table `bars_1h(ticker, timestamp, open, high,
low, close, volume)`. This is the pipeline's shared input; it produces **no** deliverable files (the 7
files are produced by layers 1.6 → 4.2). Extend the universe by dropping another
`data/seed/<TICKER>_ohlcv_1h.parquet` and running `make build-db` (or let `make loop` auto-export a
missing ticker's seed from the SP500 source DuckDB).

## Pipeline section (1.6 → 4.2)

### 1.6 — Snapshot → clean OHLCV (+ 1d/1w roll-up)
`layer1_6_snapshot_to_parquet` reads `bars_1h` for the ticker from `liora.duckdb` and **fail-closed**
asserts the clean-OHLCV candle contract (no NaN/duplicate/non-monotonic timestamps; finite, positive
OHLC; `high≥low`, `high≥max(open,close)`, `low≤min(open,close)`; non-negative volume) → writes the clean
1h parquet (file #2). `layer1_6_materialize_timeframes` rolls 1h up to 1d (ET day) / 1w (ISO week)
deterministically → files #3/#4.

### 1.7 — Time split + purge + embargo
`layer1_7` splits the candle index into warmup / train / OOS by the configured dates and purges the
train tail so no training label window (length `H=24`) overlaps the OOS boundary, plus an
`EMBARGO_BARS=35` gap. The OOS window is never read until layer 4.1.

### 2.1 — Trend-line setup detector
`layer2_1_detect` fits the trend line `L_trend`, the opposing line `L_opp`, the touchpoints, `t0`,
`R0` and `direction` using **only candles ≤ t0** (zero look-ahead); pivots `pivot_k=3`, lookback 120,
`MIN_TOUCHES=2`, cooldown 24. The same detector also runs over completed 1d / 1w bars to produce coarse
context (2.3).

### 2.2 — Output B = features X + label Y
For each Train setup, `derive_output_b` assembles the model row X and the Triple-Barrier label
Y (`TB_v1.2`: signal close[t0], entry open[t0+1], TP/SL close[t] fill open[t+1], Time Barrier MOC at
`H=24`; SL = moving `L_opp(t)`, barriers from `R0`). **The standard trendline features are the core 5**
(always on when the timeframe is enabled): `distance_to_trend_line`, `risk_box_height_pct`,
`bar_return_pct`, `volume_z_score`, `direction` (reduced from 8 — `distance_to_opposing_line`,
`body_to_range_ratio`, `touch_count` are dropped from X and kept only as Output-B audit columns).

### 2.3 — Feature selection (per-asset manifest)
`resolve_feature_manifest` builds the per-asset effective manifest from the machine registries
(`Features/features_*`) + `config/per_asset_feature_selection.json`: the core 5 standard features +
the selected additional **F** features. The **default selection** is exactly
`[distance_to_trend_line, risk_box_height_pct, bar_return_pct, volume_z_score, direction,
log_return_5 (F9), close_z_score_20 (F11), dist_to_sma_20 (F19)]` — 8 X — where **F11 / F19 are the
mean / moving-average features** (`(close−SMA20)/std20` and `close/SMA20−1`, causal 20-bar). Optional
causal **1d / 1w** context (the core 5 suffixed + `log_return_5`, projected as-of, never look-ahead) and
the **2.3.4 between_timeframes cross-TF block** (6 standard alignment features FT900/902/903/905/907/908
+ F909/F910) add columns when enabled. The per-asset selection is chosen by a **Train-only feature
search** (purged walk-forward CV AUC-PR, `make feature-search` / part of `make loop`) — OOS is never read.

### 3.1 — Optuna HPO + Kelly calibration
`layer3_1_optuna` tunes the XGBoost hyperparameters (max_depth, eta, subsample, colsample_bytree,
min_child_weight, reg_lambda, n_estimators) with **Optuna TPE + MedianPruner over purged walk-forward
CV (k=4), maximizing AUC-PR on Train** (`N_TRIALS=200`) → best params (file #5). **3.1b** `calibrate_kelly`
then picks the fractional-Kelly multiplier **λ** with a dedicated 1-D Optuna study (GridSampler over
`[0.05, 1.0]`, 20 points) that maximizes **Train out-of-fold log-growth**; λ is stored as
`kelly_fraction` in best_params. Both steps are Train-only (OOS untouched); the XGBoost model is
unchanged by the Kelly step.

### 3.2 — Final model + strategy artifact
`layer3_2_train` trains XGBoost on the full Train set; Train acceptance runs the engine on the Train
window. `strategy_meta` + `asset_writers.write_strategy` emit `strategy_<T>.py` (file #6): the base64
model, the resolved FEATURE_MANIFEST, the `EXECUTION_CONTRACT` (fills/costs, `capital_mode`,
`kelly_cap`, `kelly_basis`), `best_params` (incl. `kelly_fraction`), and a selfcheck against golden
prediction vectors.

### 4.1 — OOS verdict (Risk-Box engine, Kelly sizing)
`run_engine` runs one sequential pass over the OOS window (the first OOS read) on the in-RAM booster.
Position sizing is **per-trade fractional Kelly**: `f = clip(kelly_fraction · (2p − 1), 0, KELLY_CAP)`,
`q = f · E / (entry_fill · (1+fee))` — the symmetric Risk-Box gives reward:risk `b=1`, so full per-trade
Kelly is `2p − 1` (p = the model's win probability). `CAPITAL_MODE=kelly_fractional_compounding` is the
default; `all_in_compounding_per_asset` is selectable. The verdict (end capital, PF, max drawdown, win
rate, trades, TIM) is written to `oos_metrics.db` and feeds the Dashboard.

### 4.2 — README + the 7-file deliverable
`write_readme` writes the OOS report (file #7): the capital path (with the calibrated λ), the feature
table, and the Risk-Box trade ledger. The notebook's final gate asserts the 7 expected files exist in
`Assets/<TICKER>/`.

## Operator surface (`Project/Structure/`)

```
make build-db                          data/seed/*.parquet → liora.duckdb
make run-asset TICKER=AAPL             run the notebook → Assets/AAPL/ (7 files)
make feature-search                    rank feature combos per ticker on Train CV AUC-PR (print-only)
make loop "AAPL TSLA XOM"              end-to-end per ticker: top Train features + Kelly + OOS + dashboard
make dashboard                         refresh the Dashboard feed (oos_metrics.db → Plan/data/dashboard.json)
make on / make off                     serve / stop the static visualization in the browser
```

Deterministic and reproducible (`RANDOM_SEED=42`, `XGBOOST_N_JOBS=1`, seeded Optuna) at the pinned
versions in `Project/Structure/requirements.txt`.

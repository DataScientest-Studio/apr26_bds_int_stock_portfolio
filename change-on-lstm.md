# change-on-lstm — work order: the 1000-LSTM-Liora sibling project

## 1. Goal

Build **1000-LSTM-Liora** — a standalone LSTM deep-learning analogue of this project:
the same per-asset research discipline (Triple-Barrier labels, purged walk-forward CV,
Kelly sizing, one-shot OOS, client basket demo), with an **LSTM sequence classifier
replacing XGBoost** and **all data acquisition detached** — the new project starts from
a bundled DuckDB of daily S&P 500 OHLCV and is fully usable straight from a `git clone`.

## 2. Relationship to this repo

Concept reuse, zero runtime coupling. The sibling ports the *mechanisms* (source-QC
predicates, split/purge/embargo, ATR Triple Barrier geometry, label-uniqueness weights,
purged walk-forward folds, tie-invariant AUC-PR, Kelly OOF calibration, the trade engine
with HODL fallback, the strategy-artifact pattern, the ML Basket Simulator app, the
`oos_metrics` schema) — but imports nothing from this repo at runtime and ships as a
separate, clean git repository presented on its own.

## 3. Old → new mapping

| Aspect | liora-project-ml-engineering (this repo) | 1000-LSTM-Liora |
|---|---|---|
| Model | XGBoost binary logistic (Optuna, 200 trials) | PyTorch **LSTM** (CPU-only), small seeded Optuna HPO (~10 trials: hidden / lr / dropout) |
| Model input | flat feature vector at t0 | **sequence window of 60 trading days** × daily features, z-scored with TRAIN-only stats |
| Timeframe | 1h bars (+1d/1w roll-ups) | **daily bars only** |
| Data plane | reads the external upstream 1h DuckDB store | acquisition **detached**: a daily roll-up of the whole S&P 500 is **bundled in the repo** (`data/sp500_1d.duckdb`, under GitHub's file-size limit) |
| Split dates | warmup 2016-01-04→2016-10-14 · train →2023-12-29 · OOS 2024-01-02→2026-05-29 | **calendar-round**: warmup 2016-01-01→2016-12-31 · train 2017-01-01→2023-12-31 · OOS 2024-01-01→2026-04-30 |
| Purge / embargo | H=24 bars purge, 35 bars embargo | H=10 trading days purge (=H), 10 bars embargo |
| Per-asset deliverable | seven files (notebook + parquets + params + strategy + README) | **three files** (`best_params.json`, `strategy_<T>.py` with base64 state_dict + selfcheck, `<T>_README.md`) + the `oos_metrics` row |
| Docs plane | Plan site (Procedure Lego + SOT + fail-closed gate + configurations + glossary + dashboard) | **single premium README** + one static dashboard page |
| Research plane | continuous S.1 feature-search loop | none (fixed feature set by design) |
| Client app | ML Basket Simulator (:8501) | same app, rebranded (:8502) |

## 4. Fixed decisions

1. **Data**: daily bars of the whole S&P 500 rolled up from the upstream 1h store and
   committed into the repo — a clone works immediately; the 1h source itself exceeds
   GitHub's per-file limit and stays out.
2. **Scope**: core pipeline + Basket app + premium README + minimal static dashboard.
   No Lego/SOT/gate plane, no notebook runner, no search loop.
3. **Dates**: the calendar-round split above; purge = H = 10 trading days, embargo = 10.
4. **Model**: 1-layer LSTM (hidden ∈ {16, 32, 64}, dropout, BCE-with-logits with
   pos_weight × label-uniqueness weights), seeded TPE + median pruner (~10 trials),
   early stopping on fold AUC-PR, deterministic CPU training (2 threads), final refit
   on full Train, Kelly λ from OOF log-growth.

## 5. New repo layout

```
1000-LSTM-Liora/
├── README.md              # presentation centerpiece: tiers, D1–D9 layer table, model card, quickstart
├── LICENSE                # MIT
├── Makefile               # deps / build-data / run-asset / loop / dashboard / app / serve / on / off / clean
├── requirements.txt       # pinned CPU-only deps (torch via the PyTorch CPU wheel index)
├── config.json            # single home of every parameter (splits, barriers, costs, HPO space, seed)
├── data/sp500_1d.duckdb   # committed daily store — the D1 input
├── pipeline.py            # D2–D6 + engine: QC, split/purge, features, Triple Barrier, sequences, run_engine, Kelly
├── model.py               # LSTMClassifier + seeded training + Optuna objective + determinism recipe
├── run_asset.py           # CLI: TICKER=X → HPO → refit → one-shot OOS → Assets/<T>/ + oos_metrics row
├── asset_writers.py       # strategy artifact (base64 state_dict + selfcheck), OOS README, sqlite UPSERT
├── app.py                 # ML Basket Simulator (Streamlit, read-only)
├── build_dashboard.py     # oos_metrics.db → dashboard/data/dashboard.json
├── dashboard/dashboard.html
├── tools/build_data.py    # one-time provenance: upstream 1h store → bars_1d (parity-checked, atomic)
└── Assets/                # per-asset outputs (gitignored)
```

## 6. Non-goals

No Procedure Lego / SOT / fail-closed docs gate. No feature-search plane. No notebook
runner. No data acquisition (no API calls, no 1h store dependency at runtime). No GPU.

## 7. Definition of done

- [ ] `data/sp500_1d.duckdb` built from the upstream store, row-for-row parity-checked
      against this repo's per-asset daily parquets, under GitHub's file-size limit.
- [ ] `run_asset.py TICKER=AAPL` end-to-end: HPO → Kelly → refit → one-shot OOS →
      3-file deliverable + `oos_metrics` row; a rerun reproduces identical numbers.
- [ ] `python3 Assets/AAPL/strategy_AAPL.py` selfcheck passes (golden vectors, MODEL_HASH).
- [ ] Basket app boots on :8502 and its basket math matches the DB; dashboard renders.
- [ ] Fresh-clone simulation green: `git clone … && make deps && make run-asset TICKER=…`.
- [ ] Private repo `flak92/1000-LSTM-Liora` pushed; project lives at
      `/opt/to_liora_school/1000-LSTM-Liora` next to this one.

## 8. Provenance note

The bundled daily store is a deterministic roll-up of the upstream Alpaca S&P 500 1h
DuckDB (`qc-raw-ohlcv-data-sp500-alpaca`): bars grouped by ET session day,
O=first / H=max / L=min / C=last / V=sum, exact-value parity asserted against this
repo's independently derived per-asset daily parquets. `tools/build_data.py` documents
the rule and stays in the repo as provenance; cloners never need to run it.

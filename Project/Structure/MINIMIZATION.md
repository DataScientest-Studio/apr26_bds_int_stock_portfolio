# Minimization — what changed and why

The project was reduced to the smallest stack that still meets the course and
defense requirements: **Bash (Makefile) + DuckDB/SQL + XGBoost/Optuna + Streamlit**.

## One sentence (defense)

> The project is a minimal **Bash + DuckDB + SQL + XGBoost/Optuna + Streamlit**
> pipeline: Alpaca S&P 500 data lands in one DuckDB database, features and
> portfolios are SQL, the model is tuned with Optuna, and results are shown in
> Streamlit — no scattering across hundreds of CSVs and no zoo of models.

## Production path (`Project/Structure/`)

| Stage | Implementation |
|------|----------------|
| Data store | one `liora.duckdb` per run (`schema.sql`: `ohlcv`, `tickers`) |
| Ingest | `make build-db` (`ingest_to_duckdb.py`) from the run's frozen CSVs; `fetch_data.py` writes DuckDB directly for new runs |
| Features | `src/features.sql` — DuckDB window functions (verified 1:1 vs the old pandas pipeline by `tests/parity_features.py`) |
| Model | `train_xgb_optuna.py` — XGBoost native API + Optuna; writes `xgb_model.json` + DuckDB tables |
| Walk-forward | `walk_forward.sh` — Bash loop over expanding folds, fixed best params |
| Portfolios | `build_portfolios.sql` — sector/volatility-capped selection in pure SQL |
| App | `app.py` — reads `liora.duckdb` read-only; no training at runtime |

Run it all: `make build-db && make pipeline && make app`.

## Decisions

- **One production model = XGBoost + Optuna** (`model_key = xgboost_no_history`).
  Ridge / Random Forest / RF-no-history / ROCm training code moved to
  `Archive/runs/2026-06-08/models/legacy_scripts/`. Their metrics stay as static
  rows in `model_metrics` so the 5-model **leaderboard** (the "we compared and
  chose" narrative) survives. The walk-forward backtest is strong
  (11/11 folds positive top-5, ~24% mean top-5 vs ~5% universe); on the single
  2025+ split XGBoost trails the frozen RF-no-history baseline, which the
  leaderboard documents honestly.
- **DuckDB built in place from the existing frozen CSVs** — identical dataset to
  the rendered PDF, no Alpaca re-fetch.
- **Dual visualization kept on purpose**: the 6 EDA plot types
  (countplot/boxplot/histogram/lineplot/heatmap/scatter, matplotlib/seaborn) are a
  course-rubric requirement and feed the PDF; model/portfolio charts stay in
  plotly. The app was *not* rewritten to native-only charts.
- **scikit-learn and the torch/ROCm stack are gone** — the model uses XGBoost's
  native `train`/`DMatrix` API, so `requirements.txt` is a single pruned file.

## Consistency note

Switching the production model to XGBoost diverges from the narrative in the
already-rendered `Formalities/Rendering1/` PDF (which names RF-no-history). That
frozen deliverable is left untouched; the difference is for `Rendering2` / an
addendum to reconcile.

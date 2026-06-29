# Stocks Recommender Based on User Profile

Beginner-friendly stock portfolio recommender — Liora *Data Scientist* capstone.
Turns an investor profile into a diversified 10-stock portfolio from the S&P 500.
**Decision support — not financial advice.**

## Repository layout (3 pillars)

- **`Formalities/`** — course deliverables and admin: `Timeline.md` (deadlines, steps,
  actions), `DATA_AUDIT.md`, `rocm.md`, `meeting_notes/`, `Rendering1/` (REPORT.md + PDF +
  `figures/`), `Rendering2/`.
- **`Project/`** — the working project:
  - `Structure/` — live, minimal code: `app.py`, `fetch_data.py`, `train_xgb_optuna.py`,
    `schema.sql` / `src/features.sql` / `audit.sql` / `build_portfolios.sql`, `walk_forward.sh`,
    `src/`, `reports/`, `Makefile`, `config/paths.yaml`.
  - `endproduct/` — symlinks to the active run's `data` (holds `liora.duckdb`) / `models`
    and the report `figures`.
  - `.venv/` — local environment (created by `make setup`).
- **`Archive/`** — frozen material: `runs/2026-06-08/` (the active Alpaca S&P 500 run, plus
  the CSV-era reference app and `models/legacy_scripts/` for the retired Ridge/RF/ROCm models)
  and `experiments/` (yfinance dataset, source-comparison dashboards, scraped lists).

## Minimal stack

Bash (Makefile) + **DuckDB/SQL** + **XGBoost/Optuna** + **Streamlit**. One analytical
database (`liora.duckdb`) per run, one production model, one `requirements.txt`. Feature
engineering and portfolio construction are SQL; the only Python "glue" is fetch, training,
and the app. See [`Project/Structure/MINIMIZATION.md`](Project/Structure/MINIMIZATION.md).

## Quickstart

```bash
cd Project/Structure
make setup        # create ../.venv and install requirements.txt
make build-db     # build liora.duckdb from the run's frozen CSVs
make pipeline     # train (XGBoost+Optuna) → walk-forward → portfolios
make app          # run the Streamlit defense demo
make help         # list all targets
```

The active data/model run is **`Archive/runs/2026-06-08`** (Alpaca S&P 500, 503 tickers),
wired in through `Project/Structure/config/paths.yaml` → `Project/endproduct/` symlinks.
Everything is read from `liora.duckdb`; no models are trained inside the app. Deadlines and
deliverables live in [`Formalities/Timeline.md`](Formalities/Timeline.md).

# Stocks Recommender Based on User Profile

Beginner-friendly stock portfolio recommender — Liora *Data Scientist* capstone.
Turns an investor profile into a diversified 10-stock portfolio from the S&P 500.
**Decision support — not financial advice.**

## Repository layout (3 pillars)

- **`Formalities/`** — course deliverables and admin: `Timeline.md` (deadlines, steps,
  actions), `DATA_AUDIT.md`, `rocm.md`, `meeting_notes/`, `Rendering1/` (REPORT.md + PDF +
  `figures/`), `Rendering2/`.
- **`Project/`** — the working project:
  - `Structure/` — live, minimal code: `app.py`, `fetch_data.py`, `src/`, `models/`,
    `reports/`, `Makefile`, `config/paths.yaml`.
  - `endproduct/` — symlinks to the active run's `data`/`models` and the report `figures`.
  - `.venv/` — local environment (created by `make setup`).
- **`Archive/`** — frozen material: `runs/2026-06-08/` (the active Alpaca S&P 500 model run)
  and `experiments/` (yfinance dataset, source-comparison dashboards, scraped lists).

## Quickstart

```bash
cd Project/Structure
make setup     # create ../.venv and install dependencies
make app       # run the Streamlit defense demo
make help      # list all targets
```

The active data/model run is **`Archive/runs/2026-06-08`** (Alpaca S&P 500, 503 tickers),
wired in through `Project/Structure/config/paths.yaml` → `Project/endproduct/` symlinks.
No models are trained inside the app. Deadlines and deliverables live in
[`Formalities/Timeline.md`](Formalities/Timeline.md).

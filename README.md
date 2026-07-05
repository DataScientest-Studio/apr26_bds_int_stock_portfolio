# liora-project-ml-engineering — per-asset XGBoost pipeline (S&P 500)

A self-contained, **presentation-ready** per-asset **XGBoost** trading study over S&P 500 bars,
with a client-facing **ML Basket Simulator** on top. Clone it and the app + dashboard render
immediately from the sealed results — nothing to train.

## Run it — two commands

```bash
make deps      # once: .venv + pinned requirements
make app       # the demo: Streamlit basket simulator on :8501, already showing the sealed results
```

Every other surface is read-only and instant:

| command | what it does |
|---|---|
| `make app` | ML Basket Simulator — pick tickers (each = $1000), see the basket over the OOS window (:8501) |
| `make on` | the **Plan** site (index, configurations, glossary, dashboard, Procedure-Lego) on :8000 (`make off` stops) |
| `make dashboard` | refresh the OOS feed → `plan/data/dashboard.json` |
| `make verify` | reproduce the demo tickers from the bundled mini-bars — matches the sealed rows |
| `make run-asset TICKER=AAPL` | re-run one asset's L1–L9 notebook → `Assets/AAPL/` (7 files) + a results row |

## What ships sealed (clone → show)

The results are committed, so a fresh clone shows the app + dashboard with zero training:

| path | what it is |
|---|---|
| `data/oos_metrics.db` | the one-shot OOS result row per asset (395) — read by the app & dashboard |
| `data/per_asset_feature_overrides.json` | the per-asset feature subset the search selected |
| `data/bars_demo.duckdb` | **mini bars** (15 recognizable tickers) so `make verify` reproduces on a clone |
| `plan/data/dashboard.json` | the prebuilt dashboard feed |

The **full** bars store (`data/liora.duckdb`, 160 MB, all 503 tickers) is **not** committed — it is
built from an external upstream S&P 500 store and exceeds GitHub's limit. So the app shows all 395
sealed results standalone; `make verify` reproduces the 15 demo tickers from the bundled mini-bars;
and the full universe needs the upstream store: `make build-db` (set `SP500_DUCKDB=...` to point at it).

## Repo layout

```
data/     sealed store — oos_metrics.db + per-asset selections + mini demo bars (+ full liora.duckdb, ignored)
src/      the ML engine — pipeline (L1–L9), run_asset (notebook runner), notebook_template.ipynb,
          build_db, build_dashboard, bars, asset_writers  +  config/ (JSON)  +  Features/ (registries)
app/      the Streamlit basket simulator (app.py)
plan/     the static presentation site (index / configurations / glossary / dashboard / procedure_lego)
docs/     Layers_Short_SOT.md — the Tier-3 replication blueprint
tools/    build_demo_bars.py (mini-bars builder) + verify_repro.py
```

## Research integrity — OOS is read once, never optimized

Every choice — the XGBoost hyper-parameters (Optuna), the per-asset feature subset, and the operating
point (entry threshold, Kelly fraction) — is made on the **Train** window alone, scored by purged
walk-forward cross-validation. The **OOS** window is read **exactly once per asset**, at the verdict
step, and reported as-is; it never feeds back into any decision. Optimizing against OOS would be
research nonsense (fitting the test set). The pipeline is deterministic (`seed_everything`,
`XGBOOST_N_JOBS=1`), so the same input reproduces the same OOS row — which is what `make verify` checks.

## Pipeline layers (L1 → L9)

| Layer | What it does |
|---|---|
| L1–L3 | Raw 1h OHLCV (Alpaca) → external upstream DuckDB → `data/liora.duckdb` (`bars_1h`), verbatim |
| L4 | Clean 1h OHLCV + deterministic 1d / 1w roll-ups (parquet) |
| L5 | Warmup / Train / OOS split with purge + embargo (OOS unread until the verdict) |
| L6 | Candidate side = `sign(log_return_5)`; 56 namespaced features; symmetric ATR Triple-Barrier label (H=24) |
| L7 | Optuna tunes XGBoost on Train CV AUC-PR; Kelly fraction on Train out-of-fold log-growth |
| L8 | XGBoost trains on full Train, embedded as base64 in `strategy_<TICKER>.py` |
| L9 | One-shot OOS verdict → results row, README, and the 7-file `Assets/<TICKER>/` folder |

Features are namespaced and concatenated in a deterministic order (`1h` 01–99, `1d` 101–199,
`1w` 201–299, `multi_tf` 901–999), resolved from `src/config/feature_namespaces.json`. Full contract:
`docs/Layers_Short_SOT.md`. Per-asset deliverable = 7 files (executed notebook, 1h/1d/1w parquet,
Optuna best-params, base64 strategy artifact + selfcheck, OOS README).

MIT-style coursework demo. `main` / `preparing_to_present` keep the full research apparatus (the
continuous feature-search loop, the build/check doc-gate); this `show_able` branch is the trimmed exhibit.

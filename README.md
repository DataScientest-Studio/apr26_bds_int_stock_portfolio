# liora-project-ml-engineering — minimal per-asset ML pipeline (S&P 500)

**Run & use (from the repo root or `Project/Structure`):**

```bash
make app         # Tier 1 client app (Streamlit) -> http://localhost:8501 : click tickers (each = $1000), Calculate basket
make on          # Tier 2+3 Plan site, background -> http://localhost:8000/index.html (refreshes the dashboard feed; make off stops)
make dashboard   # refresh the OOS table feed only (oos_metrics.db -> Plan/data/dashboard.json); open it via the Plan site -> Dashboard
```

A minimal, self-contained, reproducible ML trading pipeline with a client-facing
demo on top. For a chosen ticker it computes layers **L1 → L9** in one notebook and
leaves exactly **7 deliverable files** in `Assets/<TICKER>/`; the **ML Basket
Simulator** (Streamlit) lets a client replay a basket of those results over the
fixed OOS window. The ML runtime stays minimal (no SHA / lineage / heavy QC
scaffolding); the docs/viz plane is kept honest by one fail-closed gate
(`make check`): every data-state number has a single home and the visualization
derives from the SOT.

## Documentation tiers

Every document in this repo has exactly one of three roles:

| Tier | Role | Artifact | Audience | Entry point |
|---|---|---|---|---|
| 1 | Client app | ML Basket Simulator — `Project/Structure/app.py` | clients | `make app` → `http://localhost:8501` |
| 2 | Backend explanation | `Plan/` pages: `index`, `configurations`, `glossary`, `dashboard` | reviewers / operators | `make on` → `http://localhost:8000/index.html` |
| 3 | Replication blueprint | `Plan/procedure_lego.html` + the "Kontrakt replikacji" blocks & PL PROMPTS in `Project/endproduct/Layers_Short_SOT.md` | engineers rebuilding an analogous app | the Procedure Lego link on the index page |

Tier 3 is a data-processing blueprint (data science / data engineering / ML) —
replicating the modules, not the frontend.

## Pillars

- **`Plan/`** — **visualization** (Tier 2; `procedure_lego.html` is Tier 3): static pages
  (`index.html` → `procedure_lego.html`, `configurations.html`, `glossary.html`,
  `dashboard.html`). `procedure_lego.html` is the Procedure Lego canvas (L1–L9 + guards
  G.1–G.3, drag&drop, per-block replication prompts), generated from
  `procedure_lego.html.tmpl` by `make build` — edit the `.tmpl`, never the
  generated `.html`. It shows only what the code actually computes.
- **`Project/`** — the working project:
  - `Structure/` — the operational root: `app.py` (the Tier-1 client app),
    `pipeline.py` (layers L1–L9), `notebook_template.ipynb` (the per-asset runner),
    `build_db.py`, `run_asset.py`, `build_dashboard.py`, `asset_writers.py`,
    `reports/` (e.g. `compare_xgb_vs_rf.py`), `config/`, `Features/`, `data/seed/`,
    `Assets/` (empty at start), `Makefile`, `requirements.txt`.
  - `endproduct/` — the Tier-3 source-of-truth mirror (`Layers_Short_SOT.md`,
    `README.md`) plus a symlink to `Assets/`.

## Pipeline layers (L1 → L9)

| Layer | Name | What it does |
|---|---|---|
| L1 | Alpaca OHLCV download | Upstream provenance — raw 1h OHLCV came from the Alpaca Market Data API. |
| L2 | Seed export | Upstream provenance — one archive per ticker exported to `data/seed/<TICKER>_ohlcv_1h.parquet`. |
| L3 | DuckDB build | `build_db.py` loads the seed parquets into `liora.duckdb` (table `bars_1h`). |
| L4 | Parquet 1h / 1d / 1w | The notebook reads DuckDB, writes clean 1h OHLCV, then deterministic 1d and 1w roll-ups. |
| L5 | Time split | Warmup / Train / OOS split with purge and embargo; OOS stays unread until the verdict step. |
| L6 | Features + Triple-Barrier Y | Candidate side = `sign(log_return_5)`; <!--na:n_features_total-->56<!--/na--> namespaced features; label = symmetric ATR Triple Barrier (`H=24`). |
| L7 | Optuna HPO + Kelly | Optuna tunes XGBoost on Train CV AUC-PR; the Kelly fraction is calibrated on Train out-of-fold log-growth. |
| L8 | XGB strategy artifact | XGBoost trains on the full Train set and is embedded as base64 in `strategy_<TICKER>.py`. |
| L9 | OOS endproduct | OOS verdict, dashboard row, README, and the final seven-file asset folder. |

Features are namespaced and concatenated in a deterministic order: `1h` (01–99),
`1d` (101–199), `1w` (201–299), `multi_tf` (901–999). The active manifest is resolved from
`config/feature_namespaces.json`. Full contract: `Project/endproduct/Layers_Short_SOT.md`.

## 7 files per asset (`Project/Structure/Assets/<TICKER>/`)

1. `<TICKER>__L4_to_L9.ipynb` — the executed copy of the runner notebook
2. `<TICKER>_ohlcv_1h.parquet` — clean 1h OHLCV (L4)
3. `<TICKER>_ohlcv_1d.parquet` — materialized 1d
4. `<TICKER>_ohlcv_1w.parquet` — materialized 1w
5. `OPTUNAs_XGB_HPOs_best_params.json` — best hyper-parameters + Kelly fraction (L7)
6. `strategy_<TICKER>.py` — self-contained strategy artifact (base64 model + selfcheck)
7. `<TICKER>_README.md` — OOS summary + capital path + trade ledger

## Document cross-match & dependencies

```
config/*.json + Features/*/feature_registry.json + config/frozen_data_state_numbers.json
  │  make build (render) · make check (fail-closed audit)
  ├─> Plan/configurations.html            ({{...}} tokens — Tier 2)
  ├─> Plan/procedure_lego.html            ({{...}} tokens — Tier 3)
  └─> README.md + Project/endproduct/*.md (inline na:KEY marker regions)

Project/endproduct/Layers_Short_SOT.md — "Kontrakt replikacji" blocks (the Tier-3 source)
  └─ derive 1:1, gate-crossmatched ─> procedure_lego.html [J1] MODULES
                                      (rationale lives only in the [J1b] PL PROMPTS)

make run-asset / make loop
  ├─> Assets/<T>/ — the 7-file deliverable
  └─> oos_metrics.db ── make dashboard ──> Plan/data/dashboard.json ──> dashboard.html (Tier 2)
                    └── read-only ───────> app.py — ML Basket Simulator (Tier 1, make app)
```

Edit only the single homes — the config JSONs, the SOT, and the two `.tmpl`
templates — never a generated `.html`. On divergence the SOT wins. `make check`
fails closed on marker drift, stray data-state literals, and the lego↔SOT
crossmatch.

## Quickstart

```bash
cd Project/Structure
make deps                      # install requirements.txt into ../.venv
make build-db                  # data/seed/*.parquet -> liora.duckdb
make run-asset TICKER=AAPL     # run the notebook -> Assets/AAPL/ (7 files)
make on                        # static visualization (background): http://localhost:8000/index.html; make off stops
make app                       # ML Basket Simulator demo (Streamlit): http://localhost:8501
```

The demo can also be launched directly from the repo root with
`streamlit run Project/Structure/app.py` — pick tickers (each = a $1000 entry on the
first OOS day) and see the basket outcome at the end of the fixed OOS window, read
straight from `oos_metrics.db` (nothing is retrained at runtime).

Run a whole universe in one go, then refresh the dashboard feed:

```bash
make loop "AAPL TSLA XOM"      # ensure seeds -> build-db -> run each ticker -> dashboard
make dashboard                 # oos_metrics.db -> Plan/data/dashboard.json
make build                     # regenerate Plan/*.html from *.tmpl + Markdown markers
make check                     # fail-closed gate: drift / stray literals / lego<->SOT crossmatch
```

The continuous per-asset feature search (S.1) runs detached in tmux and keeps going
until you stop it — see the S.1 block in `Project/endproduct/Layers_Short_SOT.md`:

```bash
make search-on                 # launch the supervised search loop (top-20 by default)
make search-status             # per-ticker status / best CV / pending_better
make search-agent-on           # optional: Claude Sonnet steering via /loop
make search-apply TICKER=AAPL  # manual re-apply (a deliberate second OOS read)
make search-off                # graceful stop
```

The XGBoost-vs-RandomForest model comparison (boosting vs bagging) lives in
`reports/compare_xgb_vs_rf.py`. Run `make help` for the full operator surface.

You extend the universe by dropping another `data/seed/<TICKER>_ohlcv_1h.parquet` and
running `make build-db`. `Assets/` starts empty — you decide how many assets to create. The
pipeline is deterministic (`seed_everything`, `XGBOOST_N_JOBS=1`), so OOS results are
reproducible.

# liora-project-ml-engineering — minimal per-asset ML pipeline (S&P 500)

A minimal, self-contained, reproducible ML trading pipeline. For a chosen ticker it
computes layers **L1 → L9** in one notebook and leaves exactly **7 deliverable files** in
`Assets/<TICKER>/`. The ML runtime stays minimal (no SHA / lineage / heavy QC scaffolding);
the docs/viz plane is kept honest by one fail-closed gate (`make check`): every data-state
number has a single home and the visualization derives from the SOT.

## Pillars

- **`Plan/`** — **visualization**: static pages (`index.html` → `procedure_lego.html`,
  `configurations.html`, `glossary.html`, `dashboard.html`). `procedure_lego.html` is the
  Procedure Lego canvas (L1–L9 + guards G.1–G.3, drag&drop, per-block replication prompts),
  generated from `procedure_lego.html.tmpl` by `make build` — edit the `.tmpl`, never the
  generated `.html`. It shows only what the code actually computes.
- **`Project/`** — the working project:
  - `Structure/` — the operational root: `pipeline.py` (layers L1–L9),
    `notebook_template.ipynb` (the per-asset runner), `build_db.py`, `run_asset.py`,
    `build_dashboard.py`, `asset_writers.py`, `reports/` (e.g. `compare_xgb_vs_rf.py`),
    `config/`, `Features/`, `data/seed/`, `Assets/` (empty at start), `Makefile`,
    `requirements.txt`.
  - `endproduct/` — the source-of-truth mirror (`Layers_Short_SOT.md`, `README.md`) plus a
    symlink to `Assets/`.
- **`Archive/`** — frozen material: `old-capstone-2026-06-29/` (the previous DuckDB/Streamlit
  "Stocks Recommender" project) plus earlier `runs/` and `experiments/`.
- **`Formalities/`** — course deliverables: `Timeline.md`, `DATA_AUDIT.md`, and the renderings
  in `Rendering1/`. The Rendering-2 modeling write-up is `MODELING_REPORT_010726.md` at the
  repo root.

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

## Quickstart

```bash
cd Project/Structure
make deps                      # install requirements.txt into ../.venv
make build-db                  # data/seed/*.parquet -> liora.duckdb
make run-asset TICKER=AAPL     # run the notebook -> Assets/AAPL/ (7 files)
make serve                     # static visualization: http://localhost:8000/index.html
```

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

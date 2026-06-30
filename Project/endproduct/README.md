# endproduct — SOT + final deliverable

This folder is the **presentation and source of truth (SOT)** of the project: a concise,
layer-by-layer description of the implemented pipeline plus links to the real deliverables.
No PDF reports, no screenshots.

- [`Layers_Short_SOT.md`](Layers_Short_SOT.md) — the source of truth: data acquisition (1.3–1.5)
  + the 9 implemented layers (1.6 → 4.2), the feature set, Kelly position sizing, and the operator surface.
- `Assets/` — symlink to [`../Structure/Assets/`](../Structure/Assets) (each asset's deliverable, produced by `make run-asset` / `make loop`).
- `main_data_flow.html` — symlink to the visualization in [`Plan/`](../../Plan/main_data_flow.html).

## The 7-file contract (`Assets/<TICKER>/`)

| # | File | Layer | Content |
|---|------|-------|---------|
| 1 | `<T>__Layer1_6_to_Layer4_2.ipynb` | 4.2 | the executed copy of the runner notebook |
| 2 | `<T>_ohlcv_1h.parquet` | 1.6 | clean 1h OHLCV |
| 3 | `<T>_ohlcv_1d.parquet` | 1.6 | materialized 1d roll-up |
| 4 | `<T>_ohlcv_1w.parquet` | 1.6 | materialized 1w roll-up |
| 5 | `OPTUNAs_XGB_HPOs_best_params.json` | 3.1 | best hyperparameters + resolved feature manifest + calibrated `kelly_fraction` |
| 6 | `strategy_<T>.py` | 3.2 | standalone strategy artifact (base64 model + EXECUTION_CONTRACT + selfcheck) |
| 7 | `<T>_README.md` | 4.2 | OOS report: capital path + feature table + Risk-Box trade ledger |

## Data acquisition (provenance — **upstream, not this repo's code**)

The raw 1h OHLCV was downloaded from **Alpaca** (`feed=sip`, layer 1.3), held in **QuantConnect /
LEAN** zip format and exported once to `data/seed/*_ohlcv_1h.parquet` (layer 1.4). The repo's input
step (**1.5**): `build_db.py` loads those parquets into `liora.duckdb` (table `bars_1h`) — the shared
input; there is no live fetch. Layer 1.5 produces no deliverable files; the 7 files above are produced
by layers 1.6 → 4.2.

## Reproducibility

The result is deterministic (`RANDOM_SEED=42`, `XGBOOST_N_JOBS=1`, seeded Optuna samplers) and
reproducible at the pinned versions in [`../Structure/requirements.txt`](../Structure/requirements.txt).
Regenerate everything from the operator surface in `../Structure/`:

```
cd ../Structure
make build-db
make loop "AAPL AMZN GOOGL JNJ JPM META MSFT NVDA TSLA XOM"   # per-asset: top Train features + Kelly + OOS
make on                                                       # serve the static visualization + dashboard
```

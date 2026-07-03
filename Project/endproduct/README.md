# endproduct — SOT + final deliverable

This folder presents the implemented minimal per-asset ML pipeline and the
deliverable contract.

- [`Layers_Short_SOT.md`](Layers_Short_SOT.md) — the source of truth for L1-L9 + guards
  (per-module "Kontrakt replikacji" blocks; the Procedure Lego MODULES derive from them).
- `Assets/` — symlink to [`../Structure/Assets/`](../Structure/Assets), produced by `make run-asset` / `make loop`.
- `procedure_lego.html` — symlink to the Procedure Lego visualization in [`Plan/`](../../Plan/procedure_lego.html)
  (generated from `Plan/procedure_lego.html.tmpl` by `make build`; guarded by `make check`).

## The 7-File Contract (`Assets/<TICKER>/`)

| # | File | Layer | Content |
|---|------|-------|---------|
| 1 | `<T>__L4_to_L9.ipynb` | L9 | executed copy of the runner notebook |
| 2 | `<T>_ohlcv_1h.parquet` | L4 | clean 1h OHLCV |
| 3 | `<T>_ohlcv_1d.parquet` | L4 | materialized 1d roll-up |
| 4 | `<T>_ohlcv_1w.parquet` | L4 | materialized 1w roll-up |
| 5 | `OPTUNAs_XGB_HPOs_best_params.json` | L7 | best params, feature manifest, namespace metadata, CV diagnostics |
| 6 | `strategy_<T>.py` | L8 | standalone strategy artifact with base64 XGB model and selfcheck |
| 7 | `<T>_README.md` | L9 | OOS report, feature table, Triple Barrier trade ledger |

## Data Provenance

Raw 1h OHLCV was downloaded upstream from Alpaca, archived one ticker per ZIP,
and exported once to `Project/Structure/data/seed/*_ohlcv_1h.parquet`.
`build_db.py` loads those seed parquets into `liora.duckdb`. The repository does
not call the data API live.

## Reproducibility

```bash
cd ../Structure
make build-db
make loop "AAPL AMZN GOOGL JNJ JPM META MSFT NVDA TSLA XOM"
make on
```

The pipeline is deterministic for fixed input data, config, dependency versions,
`RANDOM_SEED=42`, and `XGBOOST_N_JOBS=1`.

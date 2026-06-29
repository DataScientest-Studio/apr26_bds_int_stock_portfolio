# L12 · Endproduct — per-asset deliverable folder (SOT)

The shipped end product: one self-contained **ticker folder** per asset (the asset's project folder, present from the start),
built up by the `<TICKER>__L4_to_L12.ipynb` runner from [L4](L4_snapshot_parquet_eng.md) through L12 and reported on by the
one-shot OOS run ([L11](L11_oos_test_eng.md), the external `l11_asset_metrics.sqlite` DB). `×<!--na:universe_size-->503<!--/na-->` folders — one per asset.

## Folder

```
<TICKER>/
├── <TICKER>__L4_to_L12.ipynb
├── <TICKER>_ohlcv_1h.parquet
├── OPTUNAs_XGB_HPOs_best_params.json
├── strategy_<TICKER>.py
└── <TICKER>_README.md
```

| File | Content | Origin |
|---|---|---|
| `<TICKER>__L4_to_L12.ipynb` | the per-asset **L4→L12 runner**: creates the parquet from the DuckDB snapshot, then drives the asset through to L12 — every artifact lands in this folder | present from the asset's start; runs [L4](L4_snapshot_parquet_eng.md)→L12 |
| `<TICKER>_ohlcv_1h.parquet` | clean 1h OHLCV (zero derived columns) — OHLCV lineage, **not** the X/y training matrix | created by the notebook from the [L4](L4_snapshot_parquet_eng.md) DuckDB snapshot; clean OHLCV, kept for data lineage / OOS replay |
| `OPTUNAs_XGB_HPOs_best_params.json` | best-trial XGB hyperparameters for this asset | [L9](L9_optuna_tuning_eng.md) Optuna HPO |
| `strategy_<TICKER>.py` | `MODEL_B64` + `FEATURE_MANIFEST` + `LABEL_CONTRACT` + `THRESHOLD_ENTRY` + `MODEL_HASH` + `TRAIN_WINDOW` + `selfcheck()` | [L10](L10_xgboost_strategy_eng.md) final XGB → base64 model (`MODEL_B64`) embedded in the `.py` |
| `<TICKER>_README.md` | human-readable per-asset report card: this asset's parameters (Optuna best params, `THRESHOLD_ENTRY`, `TRAIN_WINDOW`, `MODEL_HASH`, `FEATURE_MANIFEST`) + a **summary** of the OOS verdict (PF · MDD · TIM · WR) + data info (rows, date range) | assembled at packaging time from L4 data + L9 params + L10 strategy + the external [L11](L11_oos_test_eng.md) `l11_asset_metrics.sqlite` — a derived summary, **not** an authoritative store |

- **Self-containment:** `strategy_<TICKER>.py` imports standalone — the model lives in `MODEL_B64`, it does **not** read the parquet at import. The parquet is bundled alongside for reproducibility / audit / OOS replay, not consumed by the `.py`.
- **README is documentation-only:** `<TICKER>_README.md` is a generated human-readable index/report; nothing imports or executes it. It is regenerated from the artifacts and the external `l11_asset_metrics.sqlite`, so it never becomes a second source of truth.
- **One folder per asset:** `×<!--na:universe_size-->503<!--/na-->` independent folders; each can be debugged, disabled, swapped or deployed on its own (per-asset independence, [L10](L10_xgboost_strategy_eng.md)).
- **Order:** the folder is the deliverable assembled after L10; [L11](L11_oos_test_eng.md) runs once on the frozen `strategy_<TICKER>.py` and writes the verdict (PF · MDD · TIM · WR) to the external `l11_asset_metrics.sqlite`. The **authoritative** OOS results are **not** stored inside the folder — only a derived human-readable summary in `<TICKER>_README.md`; the external `l11_asset_metrics.sqlite` stays the single source of truth.
- **Fixed count / not a filter:** L12 packages **all `×<!--na:universe_size-->503<!--/na-->` frozen per-asset folders** (one per asset, *not* only OOS winners). The [L11](L11_oos_test_eng.md) OOS verdict — the external `l11_asset_metrics.sqlite` DB — does **not** change the content or `MODEL_HASH` of any `strategy_<TICKER>.py` — L12 is packaging, not selection.
- **One folder, one name:** the asset lives in a single `<TICKER>/` folder from the start; the parquet is `<TICKER>_ohlcv_1h.parquet` throughout (no separate working path, no repackaging) — the notebook writes it there directly from the DuckDB snapshot.

# L12 · Endproduct — per-asset deliverable folder (SOT)

The shipped end product: one self-contained folder per asset, assembled after [L10](L10_xgboost_strategy_eng.md)
and validated by the OOS run ([L11](L11_oos_test_eng.md)). `×<!--na:universe_size-->503<!--/na-->` folders — one per asset.

## Folder

```
<TICKER>/
├── <TICKER>_ohlcv_1h.parquet
├── OPTUNAs_XGB_HPOs_best_params.json
└── strategy_<TICKER>.py
```

| File | Content | Origin |
|---|---|---|
| `<TICKER>_ohlcv_1h.parquet` | clean 1h OHLCV (zero derived columns) | [L4](L4_snapshot_parquet_eng.md) snapshot (`parquet/<TICKER>/ohlcv.parquet`), packaged here under the per-asset name for data lineage / OOS replay |
| `OPTUNAs_XGB_HPOs_best_params.json` | best-trial XGB hyperparameters for this asset | [L9](L9_optuna_tuning_eng.md) Optuna HPO |
| `strategy_<TICKER>.py` | `MODEL_B64` + `FEATURE_MANIFEST` + `LABEL_CONTRACT` + `THRESHOLD_ENTRY` + `MODEL_HASH` + `TRAIN_WINDOW` + `selfcheck()` | [L10](L10_xgboost_strategy_eng.md) final XGB → b64 |

- **Self-containment:** `strategy_<TICKER>.py` imports standalone — the model lives in `MODEL_B64`, it does **not** read the parquet at import. The parquet is bundled alongside for reproducibility / audit / OOS replay, not consumed by the `.py`.
- **One folder per asset:** `×<!--na:universe_size-->503<!--/na-->` independent folders; each can be debugged, disabled, swapped or deployed on its own (per-asset independence, [L10](L10_xgboost_strategy_eng.md)).
- **Order:** the folder is the deliverable assembled after L10; [L11](L11_oos_test_eng.md) runs once on the frozen `strategy_<TICKER>.py` and reports the verdict (PF · MDD · TIM · WR) — OOS results are **not** stored inside the folder.
- **Naming note:** `<TICKER>_ohlcv_1h.parquet` is the L4 snapshot (`parquet/<TICKER>/ohlcv.parquet`) repackaged under the per-asset deliverable name; L4 keeps its own path convention unchanged.

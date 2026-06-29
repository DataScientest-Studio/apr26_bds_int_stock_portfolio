# L4 · Snapshot → parquet OHLCV (SOT)

Read isolation: an atomic database snapshot materialized as clean OHLCV per ticker (zero features).

- We make an atomic copy of the database (snapshot) at a single point in time.
  - if the source changes mid-copy, a retry follows (torn-read guard)
  - transformations read only the snapshot, never the live store
- Next to the copy a JSON manifest is produced.
  - manifest fields: `rows / symbols / ts_min / ts_max / price_view`
  - IN-07: `price_view = raw_usd_view` written into the manifest (input repeatability)
- From the snapshot, `COPY … TO parquet` writes a parquet per ticker.
  - path convention: `<TICKER>/<TICKER>_ohlcv_1h.parquet` (the asset's ticker folder)
  - file count: <!--na:universe_size-->503<!--/na-->
  - compression: zstd
- Columns in parquet: only `timestamp · open · high · low · close · volume`.
  - zero derived columns — features are computed only by the transformer ([L7](L7_features_x_label_y_eng.md))
- After every materialization we check row and symbol parity against the snapshot.
- One parquet file serves both training and the OOS test — it has no cuts and no features (a fixed design decision: one parquet serves Train and the OOS test).

- Each asset has **one ticker folder** `<TICKER>/` (its project folder) holding a per-asset **run notebook** `<TICKER>__L4_to_L12.ipynb`. The notebook is the **L4→L12 runner**: it **creates `<TICKER>_ohlcv_1h.parquet` from the DuckDB snapshot** here (L4), then drives the asset through to L12 — every artifact lands in this same folder:

```
<TICKER>/
├── <TICKER>__L4_to_L12.ipynb   (the runner)
└── <TICKER>_ohlcv_1h.parquet   (L4: clean OHLCV from the DuckDB snapshot)
```

- The notebook does **not** add columns to the parquet — each downstream layer's results are saved as separate artifacts / execution sections (the parquet contract — clean OHLCV, no features, no Y — stays intact).
- By [L12](L12_endproduct_eng.md) the folder holds **5 files** (the runner + parquet + Optuna params + strategy `.py` + README).

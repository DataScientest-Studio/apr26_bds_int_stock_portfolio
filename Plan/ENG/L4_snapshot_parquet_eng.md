# L4 · Snapshot → parquet OHLCV (summary)

- We make an atomic copy of the database (snapshot).
  - if the source changes mid-copy, a retry follows (guard against torn-read)
- Next to the copy a JSON manifest is produced.
  - manifest fields: `rows / symbols / ts_min / ts_max / price_view`
- From the snapshot, `COPY` writes a parquet per ticker.
  - path convention: `parquet/<TICKER>/ohlcv.parquet`
  - file count: 503
  - compression: zstd
- Columns in parquet: only `timestamp · open · high · low · close · volume`.
  - zero derived columns — features are computed only by the transformer ([L7](L7_features_x_label_y_eng.md))
- Transformations read only the snapshot, never the live store.
- After every materialization we check row and symbol parity against the snapshot.
- One parquet file serves both training and the OOS test — that is why it has no cuts and no features (register C-71).

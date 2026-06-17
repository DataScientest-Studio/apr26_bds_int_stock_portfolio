# L4 · Snapshot → Parquet OHLCV — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L4 · Snapshot → Parquet OHLCV

## Purpose (Cel)
Atomic read-isolated snapshot of DB materialized as clean per-ticker parquet (zero features); manifest with provenance; enables repeatable downstream transforms.

## Input / Output
**In**: Live DuckDB from L3 (snapshot at point-in-time).  
**Out**: 503 parquet files `parquet/<TICKER>/ohlcv.parquet` (zstd), manifest JSON (`rows/symbols/ts_min/ts_max/price_view`), IN-07 flag.

See: [L4_snapshot_parquet_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L4_snapshot_parquet_eng.md)

## Notebook / Artifact
- Path: `parquet/<TICKER>/ohlcv.parquet`
- Columns: `timestamp · open · high · low · close · volume` (USD)
- Manifest: written next to snapshot

## Tasks / Steps
1. Take atomic snapshot of DuckDB (retry on torn-read).
2. Write manifest JSON with counters + `price_view`.
3. `COPY … TO` parquet per ticker (zstd compression).
4. Verify 503 files created.
5. Guard: transforms read only snapshot, never live DB.

## QC Gates / DoD Items
- [ ] 503 parquet files, zstd compressed.
- [ ] Manifest contains IN-07 `price_view = raw_usd_view`.
- [ ] Column set exactly matches spec (no extra columns).
- [ ] Parity with L3 row count.
- [ ] Snapshot timestamp recorded.

## Dependencies
- Previous: L3 (DuckDB, canonical analytical DB)
- Next: L5 (Time split, temporal hygiene)
- Cross-cutting owners: `00_conventions_eng.md` (global naming and numbers)

## 3D Visualisation
- Cube: front = parquet file stack icon.
- Left: DB snapshot arrow.
- Right: 503 `ohlcv.parquet` meshes.
- Back: manifest JSON panel + "zstd".
- Attached: per-ticker folder tree.

---

**Footer**: Pin this card to 3D model layer L4 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L4_snapshot_parquet_eng.md` | Facts only from SOT.
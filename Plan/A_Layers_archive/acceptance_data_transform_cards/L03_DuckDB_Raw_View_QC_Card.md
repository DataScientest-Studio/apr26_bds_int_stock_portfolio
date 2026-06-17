# L3 · DuckDB + VIEW ohlcv_1h + QC-01…QC-11 — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L3 · DuckDB + VIEW ohlcv_1h + QC-01…QC-11

## Purpose (Cel)
Canonical analytical database: load zips into `raw_ohlcv_1h` (integers), expose `VIEW ohlcv_1h` (USD prices), run QC-01…QC-11 on every load; `_meta` for provenance.

## Input / Output
**In**: 510 ZIPs from L2.  
**Out**: `*.duckdb` (166 MB), table `raw_ohlcv_1h` (8 841 820 rows, 503 symbols), `VIEW ohlcv_1h` (price /10000), `_meta` table, QC gate results.

See: [`00_input_contract_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_input_contract_eng.md) · [L3_duckdb_raw_view_qc_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md)

## Notebook / Artifact
- DB file: `*.duckdb`
- View: `price_view = raw_usd_view`
- QC: 11 predicates (QC-01…QC-11) run on load

## Tasks / Steps
1. Load zips → `raw_ohlcv_1h` (DELETE+INSERT per symbol).
2. Create `VIEW ohlcv_1h` (USD conversion, zero data copy).
3. Populate `_meta` (schema_version, built_at, counters).
4. Execute QC-01…QC-11; fail on any violation.
5. Record row/symbol counts for parity (P1).

## QC Gates / DoD Items
- [ ] 8 841 820 rows, 503 symbols, 166 MB DB.
- [ ] `VIEW ohlcv_1h` exists and returns USD prices.
- [ ] All QC-01…QC-11 pass (no NaN/Inf except documented cases).
- [ ] `_meta` contains correct provenance.
- [ ] Uniqueness `(symbol, ts)` guaranteed.

## Dependencies
- Previous: L2 (ZIP store, durable source of truth)
- Next: L4 (Snapshot parquet, read-isolated copy)
- Cross-cutting owners: `00_conventions_eng.md`, `00_parameters_eng.md`, `00_definition_of_done_eng.md` (global rules, numbers, acceptance)

## 3D Visualisation
- Cylinder DB node or cube: front = DuckDB logo + "VIEW ohlcv_1h".
- Left: ZIP → load arrows.
- Right: USD price view + QC-01…QC-11 table on side wall.
- Back: "8 841 820 rows · 503 symbols · 166 MB" + green checkmarks.
- Attached: small QC predicate list plane.

---

**Footer**: Pin this card to 3D model layer L3 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md` | Facts only from SOT.
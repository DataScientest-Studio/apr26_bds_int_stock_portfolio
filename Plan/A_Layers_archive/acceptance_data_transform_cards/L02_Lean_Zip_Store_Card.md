# L2 · LEAN ZIP Store — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L2 · LEAN ZIP Store

## Purpose (Cel)
Provide durable, compact archival store (510 ZIPs, 139 MB) as the single source of truth for rebuilding the full database; CSV rows without header, prices ×10000, naive ET timestamps.

## Input / Output
**In**: ZIPs from L1 (or rebuild).  
**Out**: 510 `<ticker>.zip` files; each holds one headerless CSV (`YYYYMMDD HH:MM,open×10000,...`); total 8 841 820 rows across all.

See: [`00_input_contract_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_input_contract_eng.md) · [L2_lean_zip_store_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L2_lean_zip_store_eng.md)

## Notebook / Artifact
- Archive format: LEAN zip + CSV row layout
- Size reference: 139 MB total
- Related: only append/replace-whole-ticker edits allowed

## Tasks / Steps
1. Receive/validate 510 ZIPs from L1.
2. Enforce name convention `<ticker>.zip`.
3. Store prices as integers ×10000 (zero FP error).
4. Guard: never partial CSV edit inside a zip.
5. Document: zips are rebuild source for L3 DuckDB.

## QC Gates / DoD Items
- [ ] Exactly 510 ZIPs, 503 universe + extras.
- [ ] Every CSV row matches `YYYYMMDD HH:MM,open,high,low,close,volume` (integers ×10000).
- [ ] Volume column present and integer.
- [ ] No header row inside CSVs.
- [ ] Parity with L3 row/symbol counts (P1).

## Dependencies
- Previous: L1 (Source, raw download)
- Next: L3 (DuckDB + QC, first analytical store)
- Cross-cutting owners: `00_conventions_eng.md`, `00_parameters_eng.md` (global rules and numbers)

## 3D Visualisation
- Cube: front = ZIP archive stack icon.
- Left: L1 arrow + "510 ZIPs".
- Right: CSV rows graphic (×10000 prices).
- Back: "139 MB · 8 841 820 rows" panel.
- Attached: folder meshes floating around node.

---

**Footer**: Pin this card to 3D model layer L2 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L2_lean_zip_store_eng.md` | Facts only from SOT.
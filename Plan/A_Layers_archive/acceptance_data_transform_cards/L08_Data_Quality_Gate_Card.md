# L8 · Data Quality Gate — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L8 · Data Quality Gate

## Purpose (Cel)
Single quality dashboard before training: count parities P1/P2/P3, aggregate L2–L7 stats into `summary.json`; any FAIL blocks L9; measures only (no fixes).

## Input / Output
**In**: Output B from L7 + prior stores.  
**Out**: `summary.json` (counters, parities, WARN/FAIL status), L8 dashboard; gate decision (PASS/FAIL).

See: [L8_data_quality_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L8_data_quality_eng.md) · [`00_parameters_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_parameters_eng.md) (l8 thresholds)

## Notebook / Artifact
- Parity chain: P1 (zip↔DuckDB), P2 (DuckDB↔parquet), P3 (parquet↔Output B)
- `summary.json` schema owned here
- Thresholds in params.json `l8` block

## Tasks / Steps
1. Re-count rows/symbols at each store boundary.
2. Assert P1/P2/P3 exact equality (no tolerance).
3. Aggregate counters, compute WARN/FAIL bands.
4. Write `summary.json`.
5. Gate: FAIL → stop before L9.

## QC Gates / DoD Items
- [ ] P1/P2/P3 all PASS (exact row/symbol match).
- [ ] `summary.json` schema correct.
- [ ] L8 dashboard shows per-layer health.
- [ ] Any FAIL blocks training.
- [ ] Reference targets from v1 (8 841 820 rows, 503 symbols).

## Dependencies
- Previous: L7 (Features, Output B)
- Next: L9 (Optuna/XGB) — only if PASS (gate blocks training)
- Cross-cutting owners: `00_parameters_eng.md`, `00_definition_of_done_eng.md` (L8 thresholds and DoD)

## 3D Visualisation
- Shield/gate cube: front = L8 dashboard icon.
- Left: P1/P2/P3 parity arrows.
- Right: summary.json + counters.
- Back: green PASS / red FAIL wall.
- Attached: 503×metrics preview or parity table.

---

**Footer**: Pin this card to 3D model layer L8 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L8_data_quality_eng.md` | Facts only from SOT.
# L5 · Time Split — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L5 · Time Split

## Purpose (Cel)
Enforce strict temporal hygiene: three disjoint windows (Warm-up / Train / OOS) per asset with purge (H=24) + embargo (5 sess) buffers; dates from `params.json` only.

## Input / Output
**In**: Parquet from L4 (Train window for detector).  
**Out**: Windowed series with hard boundaries; purged setup indices; CV scheme (purged walk-forward k=4).

See: [L5_time_split_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L5_time_split_eng.md) · [`00_parameters_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_parameters_eng.md)

## Notebook / Artifact
- Splits: `config/params.json` → `splits` block
- Warm-up: 2016-01-04 → 2016-10-14 (W=20)
- Train: 2016-10-17 → 2023-12-29
- OOS: 2024-01-02 → 2026-05-29 (frozen)

## Tasks / Steps
1. Load per-ticker parquet.
2. Slice into Warm-up / Train / OOS per `params.json`.
3. Apply PURGE_CANDLES=24 and EMBARGO=5 sessions at boundaries.
4. Verify no label window crosses split (assertion).
5. Emit purged indices for CV.

## QC Gates / DoD Items
- [ ] Splits match params.json exactly (no hardcode).
- [ ] Purge/embargo prevent leakage across boundaries.
- [ ] Warm-up rows with NULL features dropped.
- [ ] OOS untouched until L10 one-shot.
- [ ] CV scheme = purged walk-forward (k=4).

## Dependencies
- Previous: L4 (Snapshot, atomic read isolation)
- Next: L6 (Detector, setup extraction)
- Cross-cutting owners: `00_parameters_eng.md`, `00_definition_of_done_eng.md` (split dates and acceptance checklist)

## 3D Visualisation
- Timeline slab or cube: front = calendar/split icon.
- Left: Warm-up/Train/OOS colored segments.
- Right: purge (H=24) + embargo (5) buffer zones graphic.
- Back: dates from params.json.
- Attached: three window planes with row counts.

---

**Footer**: Pin this card to 3D model layer L5 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L5_time_split_eng.md` | Facts only from SOT.
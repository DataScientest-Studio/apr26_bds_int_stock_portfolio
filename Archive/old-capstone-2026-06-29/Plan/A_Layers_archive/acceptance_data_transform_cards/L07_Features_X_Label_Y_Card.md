# L7 · Features X + Label Y — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L7 · Features X + Label Y

## Purpose (Cel)
Transform setups into training matrix: compute 8 causal features at t0, triple-barrier label Y, `label_uniqueness_weight`; produce Output A/B with exact schema.

## Input / Output
**In**: Setup objects from L6 (Train).  
**Out**: Output A (setups + X + Y), Output B (FEATURE_MANIFEST 7-X + closed_through_line + label); 8 feature formulas, sample weights.

See: [L7_features_x_label_y_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md) · [`00_definition_of_done_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_definition_of_done_eng.md)

## Notebook / Artifact
- 8 features (7 X + `closed_through_line` audit) at t0 (distance_to_trend_line … body_to_range_ratio)
- Label Y: first-touch triple-barrier outcome (TP/SL/time, BARRIER_MODE)
- `FEATURE_MANIFEST`: exactly the 7 X columns + closed_through_line audit flag (Output B)

## Tasks / Steps
1. For each setup compute 8 features at t0 (ATR, volume z-score, etc.).
2. Apply triple-barrier labeling (R0 from opposing line).
3. Compute `label_uniqueness_weight` for overlapping windows.
4. Emit Output A/B with exact column names/types.
5. Guard: `closed_through_line = 1` from entry onward.

## QC Gates / DoD Items
- [ ] Output B schema matches L7 spec exactly.
- [ ] No NaN/Inf beyond documented (volume_z_score=0 when std=0).
- [ ] `label_uniqueness_weight` computed correctly.
- [ ] `Y_outcome` matches first-touch rule.
- [ ] Partitioning per `{asset_id} × {direction}`.

## Dependencies
- Previous: L6 (Detector, setup objects)
- Next: L8 (Data Quality Gate, parity & summary)
- Cross-cutting owners: `00_definition_of_done_eng.md` (feature manifest and label correctness)

## 3D Visualisation
- Cube: front = X/Y table icon (8 features + label).
- Left: setups → features.
- Right: floating plane with FEATURE_MANIFEST (7 X cols) + Y + closed_through_line.
- Back: 8 feature formulas or `label_uniqueness_weight` panel.
- Attached: sample weight matrix near node.

---

**Footer**: Pin this card to 3D model layer L7 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md` | Facts only from SOT.
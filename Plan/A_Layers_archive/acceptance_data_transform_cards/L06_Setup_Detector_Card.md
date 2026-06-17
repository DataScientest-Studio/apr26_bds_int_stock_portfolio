# L6 · Trend-line Setup Detector (OUTPUT Contract) — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L6 · Trend-line Setup Detector (OUTPUT Contract)

## Purpose (Cel)
Bridge raw candles → feature rows: produce setup objects (direction, L_trend, L_opp, t0, ATR, etc.) causally; own the 5 invariants + DET-09; algorithm in companion.

## Input / Output
**In**: `parquet/<TICKER>/ohlcv.parquet` (Train window, L5).  
**Out**: Setup objects (one per valid break) with 5 invariants; `direction` (±1), lines, `t0`, `ATR(t0)`, `R0`, `entry_candle`, etc.

See: [L6_setup_detector_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L6_setup_detector_eng.md) · [`../detector_algorithm_eng.md`](../ENG_companions/detector_algorithm_eng.md)

## Notebook / Artifact
- Output contract owned here (5 invariants)
- Reference impl: `detector_algorithm_eng.md`
- DET-09: reject setups with R0 ≤ 0 / ATR(t0) ≤ 0 / missing L_opp

## Tasks / Steps
1. Read Train-window parquets.
2. Run detector both directions (long/short).
3. Emit only causal setups (fits ≤ t0).
4. Enforce 5 invariants on every output object.
5. Count rejected setups (DET-09) in audit.

## QC Gates / DoD Items
- [ ] Every setup satisfies the 5 invariants.
- [ ] Causality: no future candle used for t0 decision.
- [ ] DET-09 rejections counted (do not vanish).
- [ ] Output schema matches contract (table in SOT).
- [ ] `closed_through_line` flag correct.

## Dependencies
- Previous: L5 (Time split, train window only)
- Next: L7 (Features X + Y, training matrix)
- Cross-cutting owners: `00_definition_of_done_eng.md` (causality and detector invariants)

## 3D Visualisation
- Cube with trend-line graphic on front (resistance/support lines).
- Left: parquet candles → setups.
- Right: setup objects table (direction, L_trend, L_opp, t0, ATR, R0).
- Back: 5 invariants + DET-09 rejection counter.
- Attached: long/short direction arrows.

---

**Footer**: Pin this card to 3D model layer L6 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L6_setup_detector_eng.md` | Facts only from SOT.
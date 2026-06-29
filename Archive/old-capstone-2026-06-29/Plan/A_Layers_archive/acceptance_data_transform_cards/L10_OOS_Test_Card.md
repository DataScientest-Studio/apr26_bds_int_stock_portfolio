# L10 · OOS Test — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L10 · OOS Test

## Purpose (Cel)
One-shot frozen evaluation on untouched OOS window: run detector + features + model, apply entry rule (p≥0.60), triple-barrier exits; produce 503×metrics matrix + distribution report. Never tune after seeing results.

## Input / Output
**In**: Frozen `strategy_*.py` from L9, OOS parquets (L5).  
**Out**: 503×{PF, Sharpe, MDD%, TIM%, WR%, trades} matrix (canonical order), hash register, results report.

See: [L10_oos_test_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L10_oos_test_eng.md) · [`00_definition_of_done_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_definition_of_done_eng.md)

## Notebook / Artifact
- OOS window dates: 2024-01-02 → 2026-05-29 (frozen, never tuned)
- Entry rule: probability p ≥ 0.60
- Exit rules: TP = R0, SL = moving L_opp(t), time-barrier = 24 candles
- Metrics canonical order in matrix: PF · Sharpe · MDD% · TIM% · WR% (plus trades count)

## Tasks / Steps
1. Hash all strategy files → register (freeze).
2. Single OOS run: detector → X features → model → p.
3. Apply entry rule + triple-barrier exits.
4. Compute 503×6 metrics matrix.
5. Produce distribution report; zero tuning after results.

## QC Gates / DoD Items
- [ ] Strategy hashes registered before any OOS run.
- [ ] OOS result never returns to tuning.
- [ ] Metrics matrix complete (503 assets).
- [ ] One-shot only (no iterative OOS peeking).
- [ ] Artifacts immutable post-hash.

## Dependencies
- Previous: L9 (frozen artifacts, hash registered)
- Next: none (end of pipeline, final verdict)
- Cross-cutting owners: `00_definition_of_done_eng.md` (OOS one-shot rule)

## 3D Visualisation
- Cube: front = OOS matrix icon (503 assets).
- Left: frozen strategy.py + OOS window.
- Right: metrics table (PF · Sharpe · MDD · TIM · WR).
- Back: "one-shot · hash registered" panel.
- Attached: results distribution chart plane.

---

**Footer**: Pin this card to 3D model layer L10 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L10_oos_test_eng.md` | Facts only from SOT.
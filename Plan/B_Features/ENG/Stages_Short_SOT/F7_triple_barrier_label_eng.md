# F7 · Triple-barrier label — Y + sample weight (SOT)

A **scaffold / data-handling Stage** (produces no `f{stage}_…` ids): attach the supervised target the XGB will
learn, and a weight that de-biases overlapping windows. Values inlined from the Pipeline-A build SOT
([A_Layers/L7](../../../A_Layers/ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md)).

- Input: the feature rows (F2–F6) + the entry/setup times; uses bars `≤ t0 + H` only for the outcome.
- **Triple-barrier outcome** `Y ∈ {0, 1}` over the horizon `H = 24` candles from the entry candle `t0`:
  - **TP** — first touch of the take-profit level (`+R0`) → `Y = 1`.
  - **SL** — first touch of the moving opposing line `L_opp(t)` → `Y = 0`.
  - **time** — neither barrier hit by `t0 + H` → `Y = 0` (close-based resolution).
- **Sample weight** = `label_uniqueness_weight = mean_{t ∈ W_i}(1 / c_t)`, where `c_t` ≥ 1 is the number of
  label windows overlapping candle `t`; down-weights overlapping (non-independent) examples.
- **Outputs:** Output A = per-candle table (with the entry signal `Y_entry`); Output B = per-setup training
  matrix (one row per example: the X columns + target `Y` + `label_uniqueness_weight`).
- Family: none (produces a label + weight, not features).
- Output: `Y` + `sample_weight` → joined with X at [F8](F8_assemble_x_dq_eng.md).

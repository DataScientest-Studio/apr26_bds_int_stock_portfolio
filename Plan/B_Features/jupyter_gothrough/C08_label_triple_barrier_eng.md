# C08 · Label Y — triple barrier (scaffold · A_Layers L7)

Build the supervised target from the future OHLC path — needed so F6/F7 have something to predict.

- Realizes: [F7](../ENG/Stages_Short_SOT/F7_triple_barrier_label_eng.md) — data-handling Stage (inlines A_Layers L7); applied **per-bar** here, not per detector-setup.
- Role: scaffold cell.
- Input: `ohlcv` ([C01](C01_f0_load_raw_ohlcv_eng.md)) and `split` ([C02](C02_time_split_eng.md)).
- Does:
  - for each candidate bar `t0`, walk the future path to the time barrier and resolve the triple barrier (TP / SL / timeout), **first touch wins**, close-based (definition owned by [L7](../../A_Layers/ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md)).
  - set the label horizon `H` to match the purge buffer reserved in [C02](C02_time_split_eng.md).
  - compute the **average-uniqueness sample weight** for overlapping label windows (per [L7](../../A_Layers/ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md)).
- Produces: `y` (triple-barrier outcome per bar), `sample_weight`, and the `label_config` (TP/SL rule, `H`, barrier mode) — kept for the C13 manifest.
- Guards: the label is the **only** forward-looking quantity and is confined by the purge/embargo so no Train label reaches into OOS; no feature at `t0` may depend on bars `> t0` (label-leakage ban, [`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md)).
- Check: every `[t0, t0+H]` window respects the C02 boundary (purge assertion); `y` aligned to `ts`; `sample_weight > 0`.
- Output: `y`, `sample_weight`, `label_config` → [C09](C09_assemble_x_audit_eng.md).

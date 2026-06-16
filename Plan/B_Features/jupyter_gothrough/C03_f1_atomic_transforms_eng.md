# C03 · F1 — Atomic transforms (feature Stage F1)

Compute the point-wise F1 features from F0, on one bar or an adjacent pair.

- Realizes: [F2](../ENG/Stages_Short_SOT/F2_atomic_transforms_eng.md).
- Role: feature-stage cell.
- Input: `ohlcv` from [C01](C01_f0_load_raw_ohlcv_eng.md).
- Does: compute each F1 feature id by its canonical formula (owned by [F1](../ENG/Stages_Short_SOT/F2_atomic_transforms_eng.md); not restated here), applying the guard functions from [`00_guards_and_windows_eng.md`](../ENG/Stages_Short_SOT/00_guards_and_windows_eng.md).
- Produces (F1 ids; families/formulas owned by [F1](../ENG/Stages_Short_SOT/F2_atomic_transforms_eng.md) and [`00_families_eng.md`](../ENG/Stages_Short_SOT/00_families_eng.md)): `f2_candle_range`, `f2_candle_body_abs`, `f2_candle_body_signed`, `f2_lower_wick`, `f2_upper_wick`, `f2_body_pct`, `f2_close_position`, `f2_r_cc`, `f2_gap_open`, `f2_tp`, `f2_ohlc4`, `f2_volume_dollar`, `f2_volume_log`.
- Guards: bar `t` (and `t−1` for returns/gap) only — causal by construction; every division ε-guarded; `safe_log_ratio` NULLs dropped, never imputed.
- Check: no future-bar reference; guarded columns have no `NaN`/`Inf` (only intended `NULL` from `safe_log_ratio` on non-positive prices); families match the SOT.
- Output: the F1 columns appended to the working frame → [C04](C04_f2_rolling_temporal_eng.md) (rolling), [C06](C06_f4_classical_indicators_eng.md) (indicators), [C07](C07_f5_research_representations_eng.md) (stack).

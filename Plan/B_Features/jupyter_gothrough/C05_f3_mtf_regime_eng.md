# C05 · F3 — MTF / regime / context (feature Stage F3)

Resample 1h→1d, bucket into regimes and tag session phase — the context that conditions F4/F5.

- Realizes: [F4](../ENG/Stages_Short_SOT/F4_mtf_regime_eng.md).
- Role: feature-stage cell (first cell that **fits on Train**).
- Input: F1/F2 columns ([C03](C03_f1_atomic_transforms_eng.md), [C04](C04_f2_rolling_temporal_eng.md)) and `split` from [C02](C02_time_split_eng.md).
- Does:
  - resample 1h → 1d only and recompute F1/F2 on the coarser grid.
  - fit the regime **quantile / threshold cutoffs on the Train window only**, then apply them forward unchanged.
  - tag session phase from minute-of-session.
- Produces (F3 ids, all `meta` family): `f4_vol_regime`, `f4_volume_regime`, `f4_session_open_phase`, `f4_session_midday_phase`, `f4_session_close_phase`; plus the fitted `regime_cutoffs` (kept for the C13 artifact).
- Guards: cutoffs fit on **Train only** and frozen ([`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md)); regimes are causal (bars `≤ t`) and only *condition* other features (dashed context edges), never look ahead; resample is 1h→1d only.
- Check: `regime_cutoffs` computed from Train rows only; no OOS row touched while fitting; regime labels causal.
- Output: F3 context columns + `regime_cutoffs` → [C06](C06_f4_classical_indicators_eng.md), [C07](C07_f5_research_representations_eng.md).

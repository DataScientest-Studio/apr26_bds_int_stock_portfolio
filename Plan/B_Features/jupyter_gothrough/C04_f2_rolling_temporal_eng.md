# C04 · F2 — Rolling / temporal (feature Stage F2)

Roll F1 features over backward windows of length `n` to get momentum, volatility, volume-z and drawdown.

- Realizes: [F3](../ENG/Stages_Short_SOT/F3_rolling_temporal_eng.md).
- Role: feature-stage cell.
- Input: the F1 columns from [C03](C03_f1_atomic_transforms_eng.md).
- Does: compute each F2 feature over the trailing window ending at `t` inclusive, for the illustrative window set `n ∈ {5, 10, 20, 50}` on 1h (windows owned by [`00_guards_and_windows_eng.md`](../ENG/Stages_Short_SOT/00_guards_and_windows_eng.md); formulas by [F2](../ENG/Stages_Short_SOT/F3_rolling_temporal_eng.md)).
- Produces (F2 ids, one per window `n`): `f3_mom_n`, `f3_vol_return_std_n`, `f3_volume_z_n`, `f3_path_drawdown_n`.
- Guards: all windows **backward-only**; a feature is `NULL` until its window has rolled in (`t < n−1`) and NULLs are dropped, never imputed; rolling z-score uses `σ = 0 → 0`.
- Check: no centered/forward windows; warm-up NULLs present only before each window rolls in; values finite after warm-up.
- Output: the F2 columns → [C05](C05_f3_mtf_regime_eng.md) (regimes), [C06](C06_f4_classical_indicators_eng.md), [C07](C07_f5_research_representations_eng.md).

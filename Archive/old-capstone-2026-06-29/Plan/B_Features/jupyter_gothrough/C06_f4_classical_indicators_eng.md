# C06 · F4 — Classical indicators (feature Stage F4)

Compute the textbook indicators as ε-guarded functions of F1–F3.

- Realizes: [F5](../ENG/Stages_Short_SOT/F5_classical_indicators_eng.md).
- Role: feature-stage cell.
- Input: F1–F3 columns ([C03](C03_f1_atomic_transforms_eng.md)–[C05](C05_f3_mtf_regime_eng.md)).
- Does: compute each indicator at its textbook default period (canonical short forms owned by [F4](../ENG/Stages_Short_SOT/F5_classical_indicators_eng.md); extended derivations in companion [`../ENG/feature_formulas_eng.md`](../ENG/feature_formulas_eng.md)).
- Produces (F4 ids): `f5_rsi_14`, `f5_macd_hist_12_26_9`, `f5_atr`, `f5_obv`, `f5_adl`, `f5_stoch_k_14`, `f5_adx_14`, `f5_mfi_14`, `f5_vwap_distance`.
- Guards: all indicators causal (bars `≤ t`) and ε-guarded on every division; `f5_atr = mean_n(TR)` is the plain mean of TR (Plan-B convention), distinct from ADX's internal Wilder-smoothed TR.
- Check: no future-bar reference; periods match the SOT defaults; divisions guarded (no `Inf`); `f5_atr` is not reused as the ADX smoother.
- Output: the F4 columns → [C07](C07_f5_research_representations_eng.md) (stack) and the model-candidate space assembled in [C09](C09_assemble_x_audit_eng.md).

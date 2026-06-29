# F13 · Cross-asset entry table (SOT)

A **cross-asset / portfolio-facing Stage** (produces no `f{stage}_…` ids): aggregate the per-asset model
outputs across the universe into one wide binary table. This is the first Stage that operates **across** the
503 single-asset models rather than on one asset's OHLCV.

- Input: the per-asset calibrated XGB from [F10](F10_calibration_optuna_eng.md) (bundled as the [F12](F12_artifact_export_eng.md) artifact), for each asset in the universe.
- **Entry signal:** each per-asset model emits a **binary enter / no-enter** decision per bar `t` — `1` if the
  calibrated probability `≥ THRESHOLD_ENTRY`, else `0`.
- **Stack across the universe:** assemble the signals into a wide table — rows = time (bars), columns = **503
  assets**, cells ∈ `{0, 1}`. Aligned on `ts` across all assets.
- **Causality:** each cell at `t` is the causal output of that asset's model on bars `≤ t` (no look-ahead);
  see [00_leakage_contract_eng.md](00_leakage_contract_eng.md).
- Family: none (consumes models, produces a 0/1 matrix).
- Output: the **503-column binary entry matrix** → consumed by [F14](F14_cross_asset_correlation_eng.md).

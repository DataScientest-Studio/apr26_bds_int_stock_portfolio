# F11 · OOS evaluation (SOT)

A **scaffold / data-handling Stage** (produces no `f{stage}_…` ids): run the frozen per-asset XGB once over the
OOS window — the **only** time OOS is read. Values inlined from the Pipeline-A build SOT
([A_Layers/L11](../../../A_Layers/ENG/Layers_Short_SOT/L11_oos_test_eng.md)).

- Input: the per-asset calibrated XGB from [F10](F10_calibration_optuna_eng.md) + the OOS mask from
  [F1](F1_time_split_eng.md) (`2024-01-02 → 2026-05-29`).
- **Entry rule:** take a position when the calibrated probability `≥ THRESHOLD_ENTRY = 0.60`.
- **Metrics** (canonical order): **PF · Sharpe · MDD · TIM · WR** (+ trade count).
- **One-shot discipline:** OOS is read exactly once; the result never re-enters tuning or selection (no refit,
  no threshold search on OOS); see [00_leakage_contract_eng.md](00_leakage_contract_eng.md).
- Family: none (produces metrics, not features).
- Output: `oos_metrics` per asset → bundled by [F12](F12_artifact_export_eng.md).

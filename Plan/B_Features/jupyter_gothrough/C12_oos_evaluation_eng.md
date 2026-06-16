# C12 · OOS evaluation (scaffold · A_Layers L10)

The one-shot read of the frozen OOS window — the only place OOS is touched.

- Realizes: [F11](../ENG/Stages_Short_SOT/F11_oos_evaluation_eng.md) — data-handling Stage (inlines A_Layers L10); one-shot, single-asset.
- Role: scaffold cell.
- Input: `model`+`calibration_map` ([C11](C11_f7_calibration_optuna_eng.md)), `(X, y)` restricted to the OOS mask in `split` ([C02](C02_time_split_eng.md)).
- Does:
  - score the calibrated model on the **untouched OOS** window: `p = model(x)` over OOS bars.
  - report ranking + calibration quality (e.g. AUC-PR, calibration curve / Brier) and, under a fixed entry rule `p ≥ threshold`, the trading metrics in the L10 canonical order (PF · Sharpe · MDD · TIM · WR · trades).
- Produces: `oos_metrics` — the OOS report (ranking, calibration, trading metrics).
- Guards: **one-shot** — OOS is read here and nowhere else; results never flow back into [C10](C10_f6_feature_selection_eng.md)/[C11](C11_f7_calibration_optuna_eng.md) tuning (a new cycle = a new Train with a later OOS); the model is frozen before this cell ([L10](../../A_Layers/ENG/Layers_Short_SOT/L10_oos_test_eng.md)).
- Check: no cell after C11 refits on OOS; `oos_metrics` computed from OOS rows only; entry threshold fixed before scoring.
- Output: `oos_metrics` → [C13](C13_artifact_export_eng.md).

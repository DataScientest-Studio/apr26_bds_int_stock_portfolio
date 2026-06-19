# L9 · Optuna hyperparameter search (SOT)

Hyperparameter search for the XGBoost meta-labeler, on Train only. Output = `best_params.json` — no model file, no artifact.
Start condition = a non-FAIL L8 dashboard ([L8](L8_data_quality_eng.md)).

## Search

- Optuna tunes the XGBoost hyperparameters; it does **not** build the final model (that is [L10](L10_xgboost_strategy_eng.md)).
  - budget: 200 trials (`N_TRIALS`)
  - sampler: TPE (Tree-structured Parzen Estimator)
  - pruner: MedianPruner (`n_warmup_steps=2`)
  - objective: AUC-PR over purged walk-forward CV (k=4 folds), in Train only
  - OOS guard: an attempt to read OOS in this phase = exception
- One study per asset (long + short setups together); the best trial fixes that asset's hyperparameters.

## Output

- `best_params.json` — the best-trial hyperparameters per asset (consumed by [L10](L10_xgboost_strategy_eng.md)).
- `trial_history` (per-trial scores, pruned flags) + the Optuna study — diagnostics only, never shipped in a strategy file.
- No `.py` and no `MODEL_B64` here — the strategy artifact is built in [L10](L10_xgboost_strategy_eng.md).
- Parameter values (`N_TRIALS`, `CV_SCHEME`, …): see [00_parameters_eng.md](00_parameters_eng.md).

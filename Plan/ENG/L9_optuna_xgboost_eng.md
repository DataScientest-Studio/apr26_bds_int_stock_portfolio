# L9 · Optuna → XGBoost → strategy .py (summary)

- Optuna tunes the XGBoost hyperparameters.
  - budget: 200 trials
  - sampler: TPE
  - pruner: MedianPruner
  - objective: AUC-PR over purged walk-forward CV, in Train only
  - guard: an attempt to read OOS in this phase = exception
- XGBoost trains as `binary:logistic` (meta-labeling).
  - sample weights: `label_uniqueness_weight`
  - one model per `{asset × direction}` pair
  - champion = retrain on the full Train with the parameters of the best trial
- Result: files with the convention `strategy_<TICKER>.py` (target ×503).
  - `MODEL_B64`: model encoded in base64
  - `FEATURE_MANIFEST`: 7 X columns in frozen order
  - `LABEL_CONTRACT`: `TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24`
  - `THRESHOLD_ENTRY`: 0.60
  - `selfcheck()`: golden vectors checked at import
- The file imports standalone, with no access to the training data.
- The build is deterministic: the same run → the same file hash.

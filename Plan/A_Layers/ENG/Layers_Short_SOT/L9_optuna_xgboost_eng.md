# L9 · Optuna → XGBoost → strategy .py (SOT)

The heart of ML: tuning and training on Train, and a self-contained strategy file with the model in base64.
Start condition = a non-FAIL L8 dashboard ([L8](L8_data_quality_eng.md)).

## Tuning + training

- Optuna tunes the XGBoost hyperparameters.
  - budget: 200 trials (`N_TRIALS`)
  - sampler: TPE (Tree-structured Parzen Estimator)
  - pruner: MedianPruner (`n_warmup_steps=2`)
  - objective: AUC-PR over purged walk-forward CV (k=4 folds), in Train only
  - OOS guard: an attempt to read OOS in this phase = exception
- XGBoost trains as `binary:logistic` (meta-labeling).
  - sample weights: `label_uniqueness_weight`
  - one model per `{asset × direction}` pair
  - champion = retrain on the full Train with the parameters of the best trial (deterministic seed)
  - meta-labeling role: the model **filters** the trend-line setup signal (the primary signal comes from the detector); it does not search for trades.

## Strategy artifact contract

Final deliverable: **one self-contained `strategy_<TICKER>.py` per Asset** (target ×503), imported
standalone with no access to the training data. Mandatory sections:

| Section | Content |
|---|---|
| `MODEL_B64` | the XGBoost (`binary:logistic`) model serialized and **base64**-encoded (~180 kB), decoded and loaded at import |
| `FEATURE_MANIFEST` | the **7 X columns** in frozen order (without `closed_through_line`; see [L7](L7_features_x_label_y_eng.md)) |
| `LABEL_CONTRACT` | label-semantics identifier: `TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24` |
| `THRESHOLD_ENTRY` | decision threshold: `p = model(x)`, `p ≥ THRESHOLD_ENTRY → ENTRY`, else FLAT (`THRESHOLD_ENTRY = 0.60`) |
| `selfcheck()` | golden vectors (input → expected `p`) verified at import; any divergence → hard error |

- The build is **deterministic** (same run → same file hash).
- `THRESHOLD_ENTRY` is tuned only in Train, never on OOS.
- Parameter values (`N_TRIALS`, `THRESHOLD_ENTRY`, `CV_SCHEME`, …): see [00_parameters_eng.md](00_parameters_eng.md).
- Output: strategy files → frozen and tested in the OOS run ([L10](L10_oos_test_eng.md)).

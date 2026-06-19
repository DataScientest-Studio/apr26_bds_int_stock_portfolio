# L10 · XGBoost final training + b64 strategy artifact (SOT)

The final model and a self-contained strategy file **per asset**, with the model in base64.
Input = `best_params.json` ([L9](L9_optuna_tuning_eng.md)) + Train `X/y` + `FEATURE_MANIFEST`.

## Final training

- XGBoost trains as `binary:logistic` (meta-labeling).
  - hyperparameters: the best trial from [L9](L9_optuna_tuning_eng.md) (`best_params.json`)
  - sample weights: `label_uniqueness_weight`
  - one model per asset (trained on both directions; `direction` is the 8th input feature, not a partition)
  - champion = retrain on the full Train with the best-trial parameters (deterministic seed)
  - meta-labeling role: the model **filters** the trend-line setup signal (the primary signal comes from the detector); it does not search for trades.

## Strategy artifact contract

Final deliverable: **one self-contained `strategy_<TICKER>.py` per Asset** — `×<!--na:universe_size-->503<!--/na-->`
independent files, each with its **own** model, model hash and Train window. Imported standalone with no access to the
training data. Mandatory sections:

| Section | Content |
|---|---|
| `MODEL_B64` | the XGBoost (`binary:logistic`) model serialized and **base64**-encoded (~180 kB), decoded and loaded at import |
| `FEATURE_MANIFEST` | the **8 X columns** in frozen order — 7 geometric features + `direction` (without `closed_through_line`; see [L7](L7_features_x_label_y_eng.md)) |
| `LABEL_CONTRACT` | label-semantics identifier: `TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24` |
| `THRESHOLD_ENTRY` | decision threshold: `p = model(x)`, `p ≥ THRESHOLD_ENTRY → ENTRY`, else FLAT (`THRESHOLD_ENTRY = 0.60`) |
| `MODEL_HASH` | hash of the encoded model — the artifact identity registered before the OOS run (one per asset) |
| `TRAIN_WINDOW` | the Train window this model saw; the OOS window stays untouched (one window per asset) |
| `selfcheck()` | golden vectors (input → expected `p`) verified at import; any divergence → hard error |

- The build is **deterministic** (same run → same file hash).
- `THRESHOLD_ENTRY` is tuned only in Train, never on OOS.
- Per-asset independence: each of the `×<!--na:universe_size-->503<!--/na-->` files can be debugged, disabled, swapped or deployed on its own.
- Parameter values (`THRESHOLD_ENTRY`, `CV_SCHEME`, …): see [00_parameters_eng.md](00_parameters_eng.md).
- Output: strategy files → frozen and tested in the OOS run ([L11](L11_oos_test_eng.md)).

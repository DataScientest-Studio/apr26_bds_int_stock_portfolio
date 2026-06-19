# L10 · XGBoost final training + b64 strategy artifact (SOT)

The final model and a self-contained strategy file **per asset**, with the model in base64.
Input = `OPTUNAs_XGB_HPOs_best_params.json` ([L9](L9_optuna_tuning_eng.md)) + Train `X/y` (derived from the asset's `<TICKER>_ohlcv_1h.parquet` via [L4](L4_snapshot_parquet_eng.md)→[L6](L6_setup_detector_eng.md)→[L7](L7_features_x_label_y_eng.md)) + `FEATURE_MANIFEST`.
The champion is base64-serialized and embedded as `MODEL_B64` inside `strategy_<TICKER>.py`.

## Final training

- XGBoost trains as `binary:logistic` (meta-labeling).
  - hyperparameters: the best trial from [L9](L9_optuna_tuning_eng.md) (`OPTUNAs_XGB_HPOs_best_params.json`)
  - sample weights: `label_uniqueness_weight`
  - one model per asset (trained on both directions; `direction` is the 8th input feature, not a partition)
  - champion = retrain on the full Train with the best-trial parameters (deterministic seed)
  - meta-labeling role: the model **filters** the trend-line setup signal (the primary signal comes from the detector); it does not search for trades.

## Acceptance objective

Per-asset selection follows the hard-coded strategy objective ([00_conventions_eng.md](00_conventions_eng.md)).

- The per-asset **champion** (the XGB retrained in L10 on [L9](L9_optuna_tuning_eng.md)'s best params — see Final training) is evaluated under Triple-Barrier exits on **Train only** (no OOS access) at the frozen `THRESHOLD_ENTRY = 0.60`, and accepted per the objective: **maximize PF** → **minimize MaxDD** → **minimize realized TIM** (time-in-market / underwater time); **WR** informational.
- Once accepted, the artifact is **frozen** (`MODEL_HASH` registered) and handed to the one-shot OOS run ([L11](L11_oos_test_eng.md)); the OOS result never returns to selection.

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
- `THRESHOLD_ENTRY` is a frozen constant (`0.60`), validated on Train, never fit on OOS — identical for every asset.
- Per-asset independence: each of the `×<!--na:universe_size-->503<!--/na-->` files can be debugged, disabled, swapped or deployed on its own.
- Parameter values (`THRESHOLD_ENTRY`, `CV_SCHEME`, …): see [00_parameters_eng.md](00_parameters_eng.md).
- Output: strategy files → frozen and tested in the OOS run ([L11](L11_oos_test_eng.md)); each ships inside its asset's `<TICKER>/` deliverable folder ([L12](L12_endproduct_eng.md)).

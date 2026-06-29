# L9 · Optuna → XGBoost → strategy.py — Master Layer Card (Acceptance Form)

**Project**: S&P 500 ML Pipeline A (L1–L10) | **Print size**: A5 landscape | **Status**: Draft

---

## Layer Name
L9 · Optuna → XGBoost → strategy.py

## Purpose (Cel)
Tune (200 TPE trials) + train binary:logistic XGB on Train (purged CV); emit self-contained `strategy_<TICKER>.py` artifact (model base64 + selfcheck); deterministic build.

## Input / Output
**In**: Output B (Train) + non-FAIL L8 gate.  
**Out**: `strategy_<TICKER>.py` per asset (imports standalone, `selfcheck()` PASS, hashable), hyperparams from Optuna.

See: [L9_optuna_xgboost_eng.md](../../A_Layers/ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md)

## Notebook / Artifact
- `N_TRIALS=200`, TPE sampler, MedianPruner
- Objective: AUC-PR, purged walk-forward k=4
- Artifact: base64 model + `selfcheck()`

## Tasks / Steps
1. Guard: OOS never read in this phase.
2. Optuna 200 trials on Train only.
3. Train final XGB with best params + sample weights.
4. Export `strategy_*.py` (deterministic, hash).
5. Verify `selfcheck()` and import standalone.

## QC Gates / DoD Items
- [ ] 200 trials completed, no OOS leakage.
- [ ] `selfcheck()` PASS on every artifact.
- [ ] Build deterministic (same input → same hash).
- [ ] Strategy imports without external deps beyond declared.
- [ ] L8 was PASS before start.

## Dependencies
- Previous: L8 (Gate must PASS, quality dashboard)
- Next: L10 (OOS test, one-shot frozen)
- Cross-cutting owners: `00_definition_of_done_eng.md` (deterministic artifact & selfcheck)

## 3D Visualisation
- Cube: front = Optuna + XGBoost chart icons.
- Left: Output B + non-FAIL gate.
- Right: `strategy_<TICKER>.py` file meshes (base64 model).
- Back: "200 trials · TPE · AUC-PR" panel.
- Attached: hyperparam table or selfcheck badge.

---

**Footer**: Pin this card to 3D model layer L9 | See full flow: `viz/main_data_flow.html` | SOT owner: `ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md` | Facts only from SOT.
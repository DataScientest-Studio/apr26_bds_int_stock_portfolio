# F14 · Cross-asset correlation → augmented model (SOT)

The top **cross-asset / portfolio-facing Stage** (produces no `f{stage}_…` ids): let correlated peers'
entry signals inform each asset's model. **The end of the Plan-B Stage stack.**

- Input: the 503-column binary entry matrix from [F13](F13_cross_asset_entry_table_eng.md) + each asset's
  selected top-20 features from [F9](F9_feature_selection_eng.md).
- **Correlation study:** measure pairwise correlation / co-occurrence of the binary entry columns,
  **fit on the Train window only**.
- **Peer selection (per target asset):** select the most informative *other* assets' entry columns (0/1) —
  the target's correlated peers — to use as extra features.
- **Augmented feature set:** `top-20 ⊕ selected peers' entries` → retrain a **cross-asset XGB** (same Optuna
  tuning + probability calibration discipline as [F10](F10_calibration_optuna_eng.md)).
- **Anti-leakage:** correlation + peer selection are computed **inside Train folds only** (no selection
  leakage); a peer's entry used at bar `t` is causal (`≤ t`). See [00_leakage_contract_eng.md](00_leakage_contract_eng.md).
- Family: none (consumes the entry matrix + features, produces a model).
- Output: the **cross-asset (portfolio-aware) calibrated XGB** — the end of Plan B.

# F9 · Feature selection (SOT)

A **model-facing Stage** (not a feature Stage — produces no `f{stage}_…` ids): from the full F2–F6 candidate
space, choose the **best, non-overfitting** subset. SHAP-like importance + anti-overfitting methods. Extended
methodology + worked example: companion [../selection_calibration_spec_eng.md](../selection_calibration_spec_eng.md).

- Input: the assembled candidate matrix `X` (all F2–F6 features) from [F8](F8_assemble_x_dq_eng.md).
- **SHAP-like importance:** per-feature Shapley-value-style attribution of the model output, averaged over samples — a signed, additive contribution per feature.
- **Anti-overfitting selection (all mandatory):**
  - **stability selection** — keep a feature only if it is important **across resamples/folds** (selection frequency ≥ a threshold), not on a single split.
  - **permutation importance** — drop a feature whose permuted-importance gain is within noise of zero.
  - **redundancy / cluster pruning** — cluster correlated features; keep one representative per cluster.
  - **nested CV** — importance and the selected subset are computed **inside training folds only** (no selection leakage; see [00_leakage_contract_eng.md](00_leakage_contract_eng.md)).
  - **parsimony** — prefer the smallest subset within 1 SE of the best CV score (the working size is the **least-overfitting top-20**).
- Family: none (consumes features, produces a subset).
- Output: the **selected, robust subset — the least-overfitting top-20** → consumed by [F10](F10_calibration_optuna_eng.md).

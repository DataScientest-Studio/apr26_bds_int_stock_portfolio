# F6 · Research representations (SOT)

Stack F2–F5 → standardize → learn / apply a representation. Every fitted object and standardizer is fit on a
**Train window only** (see [00_leakage_contract_eng.md](00_leakage_contract_eng.md)); the API is
`transform(X) → features`; all windows look backward only. Method derivations live in the companion
[../feature_formulas_eng.md](../feature_formulas_eng.md).

| Feature id | Family | Definition |
|---|---|---|
| `f6_pca_8` | meta | PCA, 8 components, on the standardized F2–F5 stack |
| `f6_dwt_db4_l3` | meta | discrete wavelet (Daubechies-4) energies, 3 levels |
| `f6_ae_8` | meta | autoencoder code, 8 dimensions |
| `f6_seq_lstm32` | meta | sequence embedding (LSTM hidden = 32) |

- Input: the standardized stack of F2–F5 features (`f6_stack`).
- All four are `meta` family (synthesis/embedding of other features).
- Fitted basis / weights are frozen after Train and applied forward unchanged (no refit on OOS).
- Output: F6 representations join the model-candidate feature space consumed by [F9](F9_feature_selection_eng.md).

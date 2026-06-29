# C07 · F5 — Research representations (feature Stage F5)

Stack F1–F4, standardize, then fit/apply the learned representations — all frozen after Train.

- Realizes: [F6](../ENG/Stages_Short_SOT/F6_research_representations_eng.md).
- Role: feature-stage cell (**fits on Train**).
- Input: F2–F5 columns ([C03](C03_f1_atomic_transforms_eng.md)–[C06](C06_f4_classical_indicators_eng.md)) and `split` from [C02](C02_time_split_eng.md).
- Does:
  - assemble the standardized F2–F5 stack (`f6_stack`); fit the standardizer on **Train only**.
  - fit each representation on Train, then apply forward unchanged via `transform(X) → features` (methods owned by [F5](../ENG/Stages_Short_SOT/F6_research_representations_eng.md); derivations in companion [`../ENG/feature_formulas_eng.md`](../ENG/feature_formulas_eng.md)).
- Produces (F5 ids, all `meta` family): `f6_pca_8`, `f6_dwt_db4_l3`, `f6_ae_8`, `f6_seq_lstm32`; plus the fitted `standardizer` + representation bases/weights (kept for the C13 artifact).
- Guards: standardizer and every basis/weight fit on **Train only**, frozen forward, no refit on OOS ([`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md)); all windows backward-only.
- Check: fitted objects derived from Train rows only; OOS produced purely by `transform`; representation output dims match the SOT (`pca_8`, `ae_8`, `lstm32`, `dwt_db4_l3`).
- Output: F5 columns + fitted `standardizer`/bases → the candidate space assembled in [C09](C09_assemble_x_audit_eng.md); fitted objects → [C13](C13_artifact_export_eng.md).

# Selection & calibration spec — F9 / F10 (+ F13 / F14 cross-asset) (companion)

> **Subordinate to the SOT.** The canonical short statements of F9 (feature selection) and F10 (calibration)
> are owned by [`Stages_Short_SOT/F9_feature_selection_eng.md`](Stages_Short_SOT/F9_feature_selection_eng.md)
> and [`Stages_Short_SOT/F10_calibration_optuna_eng.md`](Stages_Short_SOT/F10_calibration_optuna_eng.md); the
> anti-leakage rules by [`Stages_Short_SOT/00_leakage_contract_eng.md`](Stages_Short_SOT/00_leakage_contract_eng.md).
> This document is the **methodology** companion (the analogue of Pipeline A's `quality_gate_spec_eng.md`):
> rationale, the procedure, and a worked example. It restates no canonical value; on any divergence the SOT wins.

These two Stages turn the **feature space** (F2–F6) into a **robust, calibrated model**. They are theoretical
(Plan B is decoupled from any store); the goal is **generalization, not in-sample fit**.

## F9 — feature selection (choose the best, non-overfitting subset)

The enemy is overfitting the *selection* itself: pick features that happen to score well on one split and the
choice will not generalize. The procedure defends against that at every step.

1. **SHAP-like importance.** For a candidate model, attribute the output to each feature with a Shapley-value
   estimate (signed, additive, per-sample, averaged). This ranks features by *marginal contribution*, not raw
   correlation.
2. **Stability selection.** Repeat ranking across many resamples / CV folds; keep a feature only if its
   selection frequency ≥ a threshold. A feature important on one split but not others is **rejected**.
3. **Permutation importance.** Confirm each survivor: permute it and measure the score drop. If the drop is
   within noise of zero, drop the feature.
4. **Redundancy / cluster pruning.** Cluster correlated features; keep one representative per cluster (fewer,
   less-collinear inputs → lower variance).
5. **Nested CV.** Every step above runs **inside training folds only** — the outer fold is never touched by
   selection. This is what prevents selection leakage.
6. **Parsimony (1-SE rule).** Among subsets within one standard error of the best CV score, choose the
   **smallest**. Fewer features ⇒ less variance ⇒ better OOS behaviour.

**Output:** a small, stable, non-redundant feature subset that earned its place across resamples.

## F10 — calibration (Optuna tuning + probability calibration)

1. **Optuna search.** Sampler = TPE; pruner = MedianPruner. The search space covers model hyperparameters
   (and may include the F9 thresholds).
2. **Objective.** A CV metric (e.g. AUC-PR) over **purged walk-forward CV in Train only**. Folds are purged +
   embargoed so a fold's labels never leak across its boundary. **Reading OOS during tuning is a contract
   violation.**
3. **Probability calibration.** The tuned model emits raw scores; map them to calibrated probabilities with
   Platt (sigmoid) or isotonic regression, **fit on a held-out fold** (not the fold used to fit the model).
4. **Determinism.** Seeds + fitted-object hashes ⇒ the same run reproduces the same tuned, calibrated model.

## Worked example (the honest path)

- Candidates: ~120 features (F2–F6). Nested 5-fold CV.
- F6: SHAP ranking → stability selection (freq ≥ 0.6) drops ~70 → permutation prunes ~15 noise features →
  cluster pruning collapses ~12 correlated pairs → parsimony picks the least-overfitting **top-20** within 1 SE of best.
- F7: **XGBoost** on the top-20; Optuna (TPE, MedianPruner, 200 trials) maximizes mean AUC-PR over purged
  walk-forward CV on Train; isotonic calibration on a held-out fold.
- F13 / F14 (cross-asset): each per-asset XGB emits a binary enter/no-enter signal → stack into a 503-column 0/1
  table → study correlation (Train-only) → append the most informative peers' entries to the top-20 → cross-asset XGB.
- Result: a calibrated XGB on the top-20 (then optionally augmented by correlated peers' entries), tuned without
  ever reading OOS. (Illustrative — Plan B is decoupled from any store.)

## Why this is the gate (analogy to Pipeline A's L8/L9)

Pipeline A blocks training on a red quality dashboard (L8) and tunes with Optuna (L9). Plan B has no store to
gate, so **anti-overfitting selection + leakage-free calibration are the gate**: a feature or model that
cannot survive stability selection, permutation, and Train-only CV does not proceed.

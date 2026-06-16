# 00 · Leakage contract (SOT)

Canonical home for the anti-leakage principles that make a feature / selection / calibration **valid**. This
is the theoretical "definition of done" for Plan B (it has no store gate; validity is the gate).

## Causality

- Every feature at bar `t` uses **only** bars `≤ t` (back to F0). Zero look-ahead.
- All rolling windows and lags look **backward only** (no centered/forward windows).
- The only conditioning allowed is a **regime** computed from bars `≤ t` (dashed edges in the viz).

## Time split (F1) — the backbone

- **F1** defines disjoint Warm-up / Train / OOS windows + purge (24) + embargo (5 sessions) + purged
  walk-forward CV folds, **before** any feature is fit. Every fit-on-Train Stage below depends on it; the OOS
  window is read exactly once, at **F11**.

## Fit-on-Train-only

- Every **fitted** object is fit on a **Train window only**, then applied forward unchanged:
  - F4 regime cutoffs (quantile / threshold buckets).
  - F6 representations (PCA basis, wavelet/AE/sequence parameters) and their standardizers.
  - F9 selection (importance estimates, the selected top-20 subset).
  - F10 calibration (model hyperparameters, the probability-calibration map).
  - F14 cross-asset correlation + peer selection (the correlation matrix and the per-asset peer set).
- The fit/apply API is `transform(X) → features`; the OOS window is never read while fitting.

## Selection-leakage (F9)

- Importance and the selected subset are computed **inside cross-validation folds** (nested CV), never on the
  full set and never on OOS.
- Standardization / imputation statistics are computed on the **training fold only**, then applied to the
  validation fold.
- Anti-overfitting is mandatory, not optional: a feature is kept only if it is important **across resamples**
  (stability), not on a single split.

## Calibration-leakage (F10)

- Optuna's objective is scored on **purged walk-forward CV within Train only**; reading OOS during tuning is a
  contract violation.
- Probability calibration is fit on a **held-out** fold (not the fold used to fit the model).

## OOS-read-once (F11)

- The OOS window is evaluated **exactly once** (F11), with the frozen model and a fixed `THRESHOLD_ENTRY`; the
  result never re-enters selection, tuning, or threshold search.

## Cross-asset-leakage (F13 / F14)

- The 503-column entry matrix (F13) is built from per-asset model outputs that are each causal (`≤ t`); no cell
  uses future bars.
- Cross-asset correlation and per-target **peer selection** (F14) are computed **on Train only**; a peer's entry
  used at bar `t` is causal (`≤ t`), never a future or same-bar look-ahead.

## Determinism

- Same input + same seed → same features, same selected subset, same calibrated model (seeds + fitted-object
  hashes make every stage reproducible).

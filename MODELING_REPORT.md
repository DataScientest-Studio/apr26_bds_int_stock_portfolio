---
title: "Modeling Report"
subtitle: "Per-Asset XGBoost Triple-Barrier Classifier — Baseline, Boosting vs Bagging, Interpretability & Deep-Learning Outlook"
author:

- Gabriel Marchesan Almeida
- Paweł Flak
- Marcus Schürstedt
date: "today"
keywords: [machine learning, finance, XGBoost, gradient boosting, random forest, triple-barrier, purged walk-forward, Optuna, Kelly, S&P 500]
subject: "Liora APR26 BDS INT — Data Scientist Capstone Project"
description: "Rendering 2 modeling report: a per-asset XGBoost triple-barrier classifier with purged walk-forward CV, Optuna HPO and Kelly sizing, a measured XGBoost-vs-RandomForest comparison, an interpretability menu, and a deferred deep-learning plan."
lang: en

# --- Eisvogel template variables -------------------------------------------

titlepage: true
titlepage-color: "0B3D91"
titlepage-text-color: "FFFFFF"
titlepage-rule-color: "FFFFFF"
titlepage-rule-height: 2
logo-width: 100mm

toc: true
toc-own-page: true
toc-depth: 3

# Page layout

papersize: a4
geometry:

- top=25mm
- bottom=25mm
- left=25mm
- right=25mm
fontsize: 11pt
mainfont: "Arial"
monofont: "Menlo"

# Link colors: must be xcolor-named colors (not raw hex).

linkcolor: "NavyBlue"
urlcolor: "NavyBlue"
toccolor: "NavyBlue"

# Code blocks

listings: true
listings-no-page-break: true
code-block-font-size: \footnotesize

# Header / footer

header-left: "Modeling Report"
header-right: "Liora APR26 BDS INT"
footer-left: "Marchesan · Flak · Schürstedt"
footer-right: "thepage"

---

\newpage

# Executive Summary

This is the **modeling report** for the Liora capstone — the content the growing
project report calls **Rendering 2 / §8 (Modeling)**. It documents the machine
learning that is *actually implemented* in the repository: a **per-asset, supervised
classifier** that turns 1-hour S&P 500 price bars into **Triple-Barrier-labelled
trade setups**, trains **one XGBoost (gradient-boosting) model per asset**, tunes it
with **Optuna** under a **purged walk-forward** cross-validation, sizes positions with
**fractional Kelly**, and is evaluated strictly **out-of-sample (OOS)**.

Two design questions the Liora brief asks for are answered with **measured numbers**,
not assertions:

- **Bagging vs Boosting.** We trained a **RandomForest** (bagging) baseline against the
tuned **XGBoost** (boosting) on identical features and identical CV folds. Boosting
wins on **all 10 assets** (mean AUC-PR advantage **+0.027**); RandomForest sits close
to the no-skill floor.
- **Interpretability.** A menu of five tree-interpretability methods is laid out with a
recommended minimal default; this rendering keeps the section **descriptive** in line
with the project's minimalism value, and defers the heavier methods explicitly.

**Deep learning is not implemented.** There is no PyTorch / TensorFlow / Keras in the
codebase — the model is XGBoost only. Deep learning is a documented "**if time
permits**" item with a concrete plan and an acceptance gate (§6).

**Headline result, stated honestly.** The cross-validated signal is **weak but clean**:
`cv_auc_pr` ≈ 0.50–0.55 across assets. Out of sample, only **TSLA (+10.4 %, PF 1.55)**
and **JPM (PF 1.76)** are positive; **AAPL and XOM lose ≈ 5 %**; and **4 of 10 assets
never trade** at the 0.6 probability gate — i.e. the system is conservative, not
overfit-aggressive. As decision support, the per-asset edge is **not yet deployable
capital**, and we present it as a methodologically defensible, leakage-controlled
negative-leaning result.


| Milestone    | Deadline   | Sections covered            | Status        |
| ------------ | ---------- | --------------------------- | ------------- |
| Rendering 1  | 2026-06-03 | §2 – §7 (data → features)   | **Delivered** |
| Rendering 2  | 2026-07-01 | Modeling §1 – §9 (this doc) | **Delivered** |
| Final report | 2026-07-08 | Revisions + opening/closing | Not started   |


> **Disclaimer:** This project is decision support for a beginner investor, **not**
> financial advice. Every number below is **out-of-sample on past data** and is not a
> forecast.

\newpage

# 1. Scope and report-vs-implementation reconciliation

## 1.1 What this report covers

The Liora **Step 3 (Modeling)** deliverable, per `Formalities/Timeline.md`, must cover:
*baseline models → metrics, optimization and model comparison → bagging/boosting →
deep learning → interpretability → scientific & business conclusions*. This document
maps to those requirements one-to-one:


| Step-3 requirement                | Where it lives here |
| --------------------------------- | ------------------- |
| Learning target & features        | §2                  |
| Baseline models                   | §3                  |
| Metrics, optimization, comparison | §4                  |
| Bagging / boosting                | §5                  |
| Deep learning                     | §6                  |
| Interpretability                  | §7                  |
| Scientific & business conclusions | §9                  |


## 1.2 The design changed between renderings (a documented pivot)

Rendering 1 (`Formalities/Rendering1/REPORT.md`) described a **three-stage portfolio
recommender**: cluster the S&P 500 by risk/return, rank stocks *within* clusters with a
regression model, and recommend top-*N* per cluster under a sector cap, on **daily**
bars with a plain `TimeSeriesSplit`. During modeling that design was **superseded** by
the system documented here. Recording superseded/failed approaches is itself a mentor
requirement (meeting 2026-05-28), so we state the change plainly:


| Rendering-1 design (planned)           | Rendering-2 implementation (actual)              | Why the change                                 |
| -------------------------------------- | ------------------------------------------------ | ---------------------------------------------- |
| Unsupervised clustering by risk/return | Removed                                          | No supervised target; hard to defend to a jury |
| Within-cluster return **regression**   | Per-asset **binary classifier** (Triple-Barrier) | A clean, tradeable label with leakage control  |
| **Daily** bars                         | **1h** primary + 1d/1w/cross-TF context features | Richer intra-asset structure                   |
| Plain `TimeSeriesSplit`                | **Purged walk-forward + embargo**                | Removes label-overlap leakage                  |
| Sector cap / recommendation list       | Per-asset **Kelly** sizing + OOS backtest        | Direct economic evaluation per asset           |


The recommender narrative will be reconciled in the final report; this modeling report
describes **what runs in the code today**.

\newpage

# 2. Problem framing and the learning target

## 2.1 From price bars to a supervised label (Triple-Barrier)

Every eligible 1h bar `t0` is a **candidate trade**. Its **side** is taken from 1h
momentum, `direction = sign(log_return_5[t0])` (a zero momentum bar is skipped). The
trade is then simulated under the **ATR Triple-Barrier** contract `TripleBarrier.ATR.v1`
(`pipeline.py: generate_candidate_events`, `simulate_trade`):

- **Entry** fills at the **next bar open**: `entry = open[t0+1] · (1 + side · slippage)`.
- **Barrier half-width** `= ATR14[t0] · 1.0` (symmetric). Target `= entry + side · width`;
stop `= entry − side · width`.
- **Time barrier** `H = 24` bars. If neither barrier is touched, the trade exits at a
scheduled close (`scheduled_moc_close`).
- **Costs** are charged: commission **1 bp** + slippage **2 bp**.
- **Label** `Y = 1` if the **net-of-cost** per-unit return is **> 0**, else `Y = 0`.

**What it shows.** This is **binary classification**, not regression: the target is "did
this Triple-Barrier setup win after costs?". Because wins/losses are roughly balanced
per asset (positive rate ≈ 0.47–0.52, see §5), **AUC-PR** — not raw accuracy — is the
honest metric.

## 2.2 The feature space (X)

The model sees **56 numeric features**, namespaced by timeframe and concatenated in a
deterministic order (`config/feature_namespaces.json`):


| Namespace  | IDs     | Count | Content                                                        |
| ---------- | ------- | ----- | -------------------------------------------------------------- |
| `1h`       | 1–17    | 17    | 1-hour indicators (the decision clock)                         |
| `1d`       | 101–117 | 17    | Daily indicators, projected **as-of** to the 1h decision time  |
| `1w`       | 201–217 | 17    | Weekly indicators, projected **as-of** to the 1h decision time |
| `multi_tf` | 901–905 | 5     | Cross-timeframe alignment / spread features                    |


Each per-timeframe block carries the same families: **returns** (`log_return_1/5/20`),
**trend** (`dist_to_sma_20/50`, `sma_20_sma_50_ratio`, `close_z_score_20`), **momentum**
(`rsi_14`, MACD line/signal/hist), **volatility** (`atr_pct_14`,
`realized_volatility_20`, Bollinger `%b` + bandwidth), **volume** (`volume_z_score_20`)
and the **`direction`** sign. The five `multi_tf` features summarise agreement across
timeframes (`momentum_alignment_multi`, `rsi_spread_1h_1d`, `volatility_ratio_1h_1d`,
`macd_hist_alignment_multi`, `price_vs_sma_alignment_multi`).

**Commentary.** Two properties matter for modeling: (a) **all features are numeric** —
there are **no categorical columns**, so no encoding step is needed (a simplification
versus Rendering 1's encoding plan); and (b) the 1d/1w/cross-TF projections legitimately
produce **NaN** early in a series, which XGBoost ingests via **native missing-value
handling** — no imputation layer is added. This follows the project's stated value:
*use the library's built-in before adding logic*.

## 2.3 Train / OOS partition and leakage control

The series is split strictly by time (`config/pipeline_parameters.json`):


| Segment | Window                      |
| ------- | --------------------------- |
| Warmup  | 2016-01-04 → 2016-10-14     |
| Train   | 2016-10-17 → 2023-12-29     |
| **OOS** | **2024-01-02 → 2026-05-29** |


Leakage is controlled two ways. **(1) Purge:** any training setup whose label horizon
would reach into OOS is dropped — the guard enforces `t0 + H + embargo ≤ oos_start`
(`purge_train_setups`). **(2) Purged walk-forward CV** inside Train: 4 contiguous
validation folds, where a fold's training set keeps only setups with
`t0 + H < val_start − embargo` (`purged_wf_folds`). With `PURGE_CANDLES = H = 24` and
`EMBARGO_BARS = 35`, the combined no-peek span between a label and the next usable bar is
**H + 35 = 59 bars**. The OOS window is never read during fitting, tuning, or sizing.

\newpage

# 3. Baseline models

Two baselines frame how much the model actually adds.

- **No-skill floor.** For AUC-PR the floor equals the **positive rate** (prevalence). On
these assets that is ≈ **0.47–0.52** (the `Pos-rate` column in §5). Any model must beat
this to be meaningful.
- **Untuned XGBoost.** The project ships an explicit `fallback_params` block used whenever
CV is infeasible — this is the honest "first iteration": `max_depth 3, eta 0.1, subsample 0.9, colsample_bytree 0.9, min_child_weight 1.0, reg_lambda 1.0, n_estimators 100`.

**What it shows (measured).** In the §5 comparison, the **untuned XGBoost** already
clears the prevalence floor on most assets, and **Optuna tuning adds a further, modest
lift on every asset** (baseline → tuned AUC-PR rises on 10/10). The realistic ceiling is
low — `cv_auc_pr` tops out around 0.55 — which sets honest expectations for the OOS
economics in §4 and §9.

\newpage

# 4. Metrics, optimization and model comparison

## 4.1 Metrics

- **Training / selection metric: AUC-PR** (`eval_metric = "aucpr"`; Optuna direction
`maximize`). For a near-balanced but economically asymmetric "win-after-costs" target,
AUC-PR is more informative than ROC-AUC because it focuses on the precision of the
positive (trade-worthy) class.
- **Decision threshold:** a trade fires only when the model probability `p ≥ THRESHOLD_ENTRY = 0.6` (`run_engine`). A high gate trades precision for recall — it is
the direct reason some assets trade rarely or never (§9).
- **OOS economic metrics** (`oos_metrics.db`): profit factor (PF), return %, max drawdown
%, win rate %, trade count, time-in-market %. Strategy ranking (`STRATEGY_OBJECTIVE`)
is **PF (max) → drawdown (min) → time-in-market (min)**, with win rate informational.

## 4.2 Hyper-parameter optimization (Optuna)

XGBoost is tuned with **Optuna**: **TPE** sampler (seed 42), **MedianPruner** (2 warmup
steps), **200 trials**, maximizing mean **AUC-PR** over the 4 purged walk-forward folds
(`layer7_optuna`). The search space (`config/xgboost_optuna_search_space.json`):


| Hyper-parameter    | XGBoost name                       | Type  | Range        | Scale   |
| ------------------ | ---------------------------------- | ----- | ------------ | ------- |
| `max_depth`        | `max_depth`                        | int   | [2, 5]       | linear  |
| learning rate      | `eta`                              | float | [0.02, 0.30] | **log** |
| row subsample      | `subsample`                        | float | [0.6, 1.0]   | linear  |
| column subsample   | `colsample_bytree`                 | float | [0.6, 1.0]   | linear  |
| `min_child_weight` | `min_child_weight`                 | float | [1.0, 10.0]  | linear  |
| L2 regularization  | `reg_lambda` → `lambda`            | float | [0.5, 5.0]   | linear  |
| number of trees    | `n_estimators` → `num_boost_round` | int   | [40, 300]    | linear  |


*Example fitted model (AAPL):* `max_depth 5, eta 0.192, subsample 0.748, colsample_bytree 0.965, min_child_weight 9.15, reg_lambda 3.88, n_estimators 115` →
`cv_auc_pr = 0.541`.

A **second, nested** optimization calibrates the **Kelly fraction** λ on a grid of 20
points in [0.05, 1.0], maximizing **Train out-of-fold log-growth** (`calibrate_kelly`).
Live sizing is `f = clip(λ·(2p − 1), 0, KELLY_CAP=1.0)`. **Neither** optimization reads
OOS.

## 4.3 Cross-asset OOS results (data anchor — read from `oos_metrics.db`)

One architecture, ten independent per-asset fits, evaluated on the same OOS window:


| Ticker | Trades | Win % | PF   | Return %   | Max DD % | Time-in-mkt % | CV AUC-PR |
| ------ | ------ | ----- | ---- | ---------- | -------- | ------------- | --------- |
| XOM    | 263    | 48.67 | 0.88 | −5.16      | 7.55     | 36.85         | 0.514     |
| AAPL   | 236    | 48.73 | 0.88 | −5.63      | 15.68    | 39.12         | 0.541     |
| TSLA   | 74     | 59.46 | 1.55 | **+10.36** | 4.13     | 11.02         | 0.554     |
| JPM    | 71     | 64.79 | 1.76 | +0.23      | 0.05     | 11.60         | 0.513     |
| AMZN   | 6      | 33.33 | 0.23 | −0.73      | 0.83     | 1.46          | 0.532     |
| GOOGL  | 0      | —     | —    | 0.00       | 0.00     | 0.00          | 0.533     |
| JNJ    | 0      | —     | —    | 0.00       | 0.00     | 0.00          | 0.506     |
| META   | 0      | —     | —    | 0.00       | 0.00     | 0.00          | 0.507     |
| MSFT   | 0      | —     | —    | 0.00       | 0.00     | 0.00          | 0.521     |
| NVDA   | 0      | —     | —    | 0.00       | 0.00     | 0.00          | 0.523     |


**What it shows.** Tradeability is highly asset-dependent under one shared recipe. **Two
of six trading assets are profitable** (TSLA, JPM); the two high-activity names (XOM,
AAPL) lose ≈ 5 %; and **four assets never clear the 0.6 gate**, so they hold cash. This
is the primary "model comparison" deliverable: same model, very different outcomes.

\newpage

# 5. Bagging vs Boosting

## 5.1 Boosting — what we actually run

XGBoost is **gradient-boosted trees**: shallow trees added **sequentially**, each one
fitted to the residual errors of the current ensemble, combined with shrinkage `eta`
(`pipeline.py: _xgb_train`, `objective="binary:logistic"`, `booster="gbtree"`). The
boosting-specific controls are exactly the tuned knobs in §4.2: tree depth, learning
rate, tree count, and L2 regularization.

## 5.2 Bagging — the concept, and where it already lives inside XGBoost

**Bagging** (bootstrap aggregation) trains many learners **in parallel** on bootstrap
resamples and averages them to **reduce variance** — RandomForest is the canonical
example. XGBoost is not a bagging method, but it borrows bagging's variance-reduction
idea **inside** the boosting loop via two tuned parameters:

- `subsample ∈ [0.6, 1.0]` — each boosting round uses a random **row** sample;
- `colsample_bytree ∈ [0.6, 1.0]` — each tree uses a random **feature** sample.

Together these make our XGBoost a **stochastic gradient booster** — boosting with a
bagging-style randomization baked in.

## 5.3 Measured comparison — XGBoost vs RandomForest (data anchor)

To answer the mentor's explicit request (2026-05-28), we trained a **RandomForest**
(bagging) baseline against the tuned **XGBoost** (boosting) on the **same features**,
the **same purged walk-forward folds**, and the **same AUC-PR metric**
(`reports/compare_xgb_vs_rf.py`, 300-tree RF, seed 42). One asymmetry is itself a
finding: **RandomForest cannot consume NaN**, so the 1d/1w/cross-TF gaps were
**median-imputed** (fit on the training fold only); XGBoost needed **no imputation**.


| Ticker | Setups | Folds | Pos-rate | Baseline XGB | **Tuned XGB** | RandomForest | Δ (XGB − RF) |
| ------ | ------ | ----- | -------- | ------------ | ------------- | ------------ | ------------ |
| AAPL   | 12 565 | 4     | 0.500    | 0.521        | **0.541**     | 0.504        | +0.037       |
| AMZN   | 12 573 | 4     | 0.514    | 0.521        | **0.532**     | 0.514        | +0.018       |
| GOOGL  | 12 573 | 4     | 0.491    | 0.502        | **0.533**     | 0.494        | +0.039       |
| JNJ    | 12 526 | 4     | 0.482    | 0.491        | **0.506**     | 0.499        | +0.008       |
| JPM    | 12 541 | 4     | 0.483    | 0.505        | **0.513**     | 0.491        | +0.022       |
| META   | 12 564 | 4     | 0.487    | 0.485        | **0.507**     | 0.490        | +0.017       |
| MSFT   | 12 551 | 4     | 0.473    | 0.486        | **0.521**     | 0.469        | +0.052       |
| NVDA   | 12 569 | 4     | 0.502    | 0.509        | **0.523**     | 0.506        | +0.017       |
| TSLA   | 12 570 | 4     | 0.522    | 0.546        | **0.554**     | 0.516        | +0.039       |
| XOM    | 12 531 | 4     | 0.493    | 0.492        | **0.514**     | 0.498        | +0.016       |


**What it shows.** **Boosting beats bagging on all 10 assets** (mean advantage
**+0.027** AUC-PR; range +0.008 to +0.052). RandomForest hovers near each asset's
**prevalence floor** (`Pos-rate`), i.e. it extracts little signal here, while tuned
XGBoost shows a small but **consistent** edge. As a cross-check, the **Tuned XGB** column
reproduces the stored `cv_auc_pr` from §4.3 to three decimals on every asset, confirming
the comparison uses the production CV exactly.

**Why boosting here.** On small, noisy, tabular financial tables, sequential
error-correction (boosting) extracts the faint signal better than variance-averaging
(bagging); boosting also keeps XGBoost's **native missing-value** handling, which removed
an imputation step that RandomForest required.

\newpage

# 6. Deep Learning — not yet implemented

## 6.1 Current status

There is **no deep learning** in this project. `requirements.txt` pins `xgboost==3.3.0`
and contains **no** PyTorch, TensorFlow or Keras; there are no neural-network classes
anywhere in the code. Deep learning is a deliberate **"if time permits"** item (Timeline
action list; Paul Grolier's DL masterclass, 2026-06-11), **deferred** to a later
rendering — exactly as stated here.

## 6.2 Why trees first (rationale, not avoidance)

- **Sample size.** The learning units are **setups**, and the per-asset positive class is
modest — a regime where gradient-boosted trees typically beat neural nets.
- **Tabular, engineered inputs.** The 56 features are already informative indicators, not
raw sequences; trees exploit such tables directly.
- **Determinism & reproducibility** are project hard-constraints (`seed_everything`,
`XGBOOST_N_JOBS = 1`, pinned libraries) and are easier to guarantee with XGBoost.
- **Native missing values** remove an imputation layer (see §5.3).
- **Minimalism / no ballast** — the project deliberately keeps the dependency surface and
per-asset deliverable small.

## 6.3 What we would try later (concrete, gated)

A small **MLP / TabMLP** on the same 56-feature X, same purged walk-forward folds, same
AUC-PR objective, would be the lightest deep-learning baseline. **Acceptance gate:** it
ships only if it beats the **tuned-XGBoost CV AUC-PR**; otherwise it does not. Sequence
models (LSTM / temporal CNN over raw bar windows) are noted as a stretch idea, explicitly
**out of scope** for this rendering.

\newpage

# 7. Interpretability

Per the project's minimalism value, this rendering presents interpretability as a clear
**menu** with a recommended minimal default, and **defers** the heavier methods rather
than adding dependencies now. No importance numbers are computed in this rendering.

## 7.1 The menu (five options)


| #   | Method                                                | New dependency         | Cost                 | Output                                                             |
| --- | ----------------------------------------------------- | ---------------------- | -------------------- | ------------------------------------------------------------------ |
| 1   | **Native XGBoost importance** (gain / cover / weight) | none (xgboost)         | trivial, no retrain  | global feature ranking                                             |
| 2   | TreeSHAP (global + local)                             | `shap`                 | moderate             | global + per-setup attributions                                    |
| 3   | Permutation importance (on OOS)                       | `scikit-learn`         | moderate (re-scores) | model-agnostic global ranking                                      |
| 4   | Partial dependence / ICE                              | `scikit-learn` + plots | moderate             | shape of a feature's effect                                        |
| 5   | **By-construction interpretability**                  | none                   | free                 | explicit label / side / sizing rules + documented feature formulas |


## 7.2 Recommended minimal default

For the final report we recommend shipping **Option 1 + Option 5**:

- **Option 1 (native importance)** is essentially free — the per-asset booster is already
embedded in `strategy_<TICKER>.py`, so `gain`/`cover`/`weight` rankings can be read off
the trained model **without retraining and without new dependencies**.
- **Option 5 (by-construction)** is already true of the design and needs nothing: the
**label** is an explicit Triple-Barrier rule; the **side** is a transparent
`sign(log_return_5)`; **sizing** is a closed-form Kelly clip `f = clip(λ(2p−1), 0, cap)`; and **every feature** has a documented formula, unit and timeframe in
`Features/`. The pipeline is interpretable *globally* (which features the booster uses)
and *by construction* (the rules around the model are all explicit).

## 7.3 What we defer (and why)

**TreeSHAP** (Option 2) gives the best local, per-trade explanations but adds the `shap`
dependency — defer to the final report, and only if the jury asks for per-trade
attributions. **Permutation importance** and **PDP/ICE** (Options 3–4) are useful but add
surface area; defer them. The deferral is a direct application of the README's
**no-ballast** rule: add an interpretability dependency only when it earns its place.

\newpage

# 8. From model to deployable artifact

Each asset's trained booster is frozen into a self-contained, self-verifying file
`Assets/<TICKER>/strategy_<TICKER>.py` (`asset_writers.py`, `strategy_meta`):

- the model is serialized with `booster.save_raw()` and embedded as a **base64** string;
- a `MODEL_HASH` (SHA-256 of the raw bytes) guards integrity on load;
- **golden vectors** (the first few training rows) and their predictions are stored, and a
`selfcheck` asserts byte-identical predictions when the file is loaded.

This satisfies the defense requirement of **no re-training at runtime** (Timeline Step 5)
and, together with `seed_everything`, `XGBOOST_N_JOBS = 1` and pinned libraries, makes the
OOS results **reproducible**. The artifact is a frozen predictor, not a notebook to re-run.

\newpage

# 9. Results, scientific & business conclusions

## 9.1 Scientific conclusions

- The cross-validated signal is **weak but methodologically clean**: `cv_auc_pr` ≈
0.50–0.55 with leakage controlled by purge + embargo and a never-touched OOS window.
- **Boosting > bagging** is established with a measured, fold-matched comparison (+0.027
mean AUC-PR; 10/10 assets, §5.3), and **tuning > untuned** on 10/10 (§3, §5.3).
- The conservative 0.6 gate means **4 of 10 assets hold cash** OOS — the system errs
toward *not trading* rather than over-trading a weak edge.

## 9.2 Business conclusions

- Only **TSLA (+10.4 %, PF 1.55)** and **JPM (PF 1.76)** are OOS-positive; **AAPL and XOM
lose ≈ 5 %**; AMZN is marginally negative on 6 trades. Net read: as decision support,
**the current per-asset edge is not yet deployable capital.** This is reported as an
honest, jury-defensible result, and the disclaimer stands.

## 9.3 Threats to validity

Survivorship bias carried from Rendering 1 (§5.1 there); single-market / USD-only scope;
genuinely weak AUC-PR; the RandomForest comparison used median imputation where XGBoost
used native missing; and the with-vs-without-outlier study (mentor's SNDK protocol) is
not yet run on this universe.

## 9.4 Roadmap to the final report (2026-07-08)

Add native + (optionally) SHAP importances (§7); run the with-vs-without-outlier study;
optionally add the gated MLP deep-learning baseline (§6); and reconcile the Rendering-1
recommender narrative with the implemented per-asset classifier.

\newpage

# Appendices

## A. Reproducibility

```bash
cd Project/Structure
python -m pip install -r requirements.txt          # now includes scikit-learn==1.7.2
# 1) per-asset pipeline (data -> features -> Optuna -> Kelly -> OOS), if rebuilding assets:
make run-universe                                   # writes Assets/<T>/ + oos_metrics.db
# 2) the XGBoost-vs-RandomForest model comparison (§5.3):
python reports/compare_xgb_vs_rf.py                 # prints the table; writes xgb_vs_rf_results.json
```

The §4.3 cross-asset table is read directly from `oos_metrics.db`; the §5.3 comparison is
produced by `reports/compare_xgb_vs_rf.py`. No metric in this report is hand-entered.

## B. Computing environment

Python 3.12; `xgboost 3.3.0`, `optuna 4.8.0`, `numpy 2.5.0`, `pandas 2.2.3`,
`pyarrow 24.0.0`, `duckdb 1.5.4`, `scikit-learn 1.7.2`. Determinism: fixed seed 42,
`XGBOOST_N_JOBS = 1`, pinned dependency set. The PDF is rendered with Pandoc + XeLaTeX
using the Eisvogel template (same recipe as Rendering 1's `reports/build_pdf.sh`).

## C. Static visualization app

`Plan/index.html` (`main_data_flow.html`, `configurations.html`, `glossary.html`,
`dashboard.html`) is the static, no-retraining companion to the oral-defense demo.

## D. Glossary

Triple-Barrier label, ATR, AUC-PR, ROC-AUC, purged walk-forward, embargo, TPE sampler,
MedianPruner, fractional Kelly, stochastic gradient boosting, bagging / bootstrap
aggregation, native missing-value handling, TreeSHAP, look-ahead leakage, profit factor.

## E. Bibliography

- López de Prado, M. (2018). *Advances in Financial Machine Learning*. Wiley — Triple-Barrier labeling, purged cross-validation, embargo, label uniqueness.
- Chen, T. & Guestrin, C. (2016). *XGBoost: A Scalable Tree Boosting System*. KDD.
- Breiman, L. (2001). *Random Forests*. Machine Learning 45(1).
- Akiba, T. et al. (2019). *Optuna: A Next-generation Hyperparameter Optimization Framework*. KDD.
- Lundberg, S. & Lee, S. (2017). *A Unified Approach to Interpreting Model Predictions* (SHAP). NeurIPS — listed for the deferred interpretability option.
- Kelly, J. L. (1956). *A New Interpretation of Information Rate*. Bell System Technical Journal.


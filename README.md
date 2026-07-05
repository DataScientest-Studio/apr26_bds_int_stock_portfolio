# liora-project-ml-engineering — per-asset XGBoost pipeline (S&P 500)

A self-contained, **presentation-ready** per-asset **XGBoost** trading study over S&P 500 bars,
with a client-facing **ML Basket Simulator** on top. Clone it and the app + dashboard render
immediately from the sealed results — nothing to train.

## Run it — two commands

```bash
make deps      # once: .venv + pinned requirements
make app       # the demo: Streamlit basket simulator on :8501, already showing the sealed results
```

Every other surface is read-only and instant:

| command | what it does |
|---|---|
| `make app` | ML Basket Simulator — pick tickers (each = $1000), see the basket over the OOS window (:8501) |
| `make on` | the **Plan** site (index, configurations, glossary, dashboard, Procedure-Lego) on :8000 (`make off` stops) |
| `make dashboard` | refresh the OOS feed → `plan/data/dashboard.json` |
| `make verify` | reproduce the demo tickers from the bundled mini-bars — matches the sealed rows |
| `make run-asset TICKER=AAPL` | re-run one asset's L1–L9 notebook → `Assets/AAPL/` (7 files) + a results row |

## What ships sealed (clone → show)

The results are committed, so a fresh clone shows the app + dashboard with zero training:

| path | what it is |
|---|---|
| `data/oos_metrics.db` | the one-shot OOS result row per asset (395) — read by the app & dashboard |
| `data/per_asset_feature_overrides.json` | the per-asset feature subset the search selected |
| `data/bars_demo.duckdb` | **mini bars** (15 recognizable tickers) so `make verify` reproduces on a clone |
| `plan/data/dashboard.json` | the prebuilt dashboard feed |

The **full** bars store (`data/liora.duckdb`, 160 MB, all 503 tickers) is **not** committed — it is
built from an external upstream S&P 500 store and exceeds GitHub's limit. So the app shows all 395
sealed results standalone; `make verify` reproduces the 15 demo tickers from the bundled mini-bars;
and the full universe needs the upstream store: `make build-db` (set `SP500_DUCKDB=...` to point at it).

## Repo layout

```
data/     sealed store — oos_metrics.db + per-asset selections + mini demo bars (+ full liora.duckdb, ignored)
src/      the ML engine — pipeline (L1–L9), run_asset (notebook runner), notebook_template.ipynb,
          build_db, build_dashboard, bars, asset_writers  +  config/ (JSON)  +  Features/ (registries)
app/      the Streamlit basket simulator (app.py)
plan/     the static presentation site (index / configurations / glossary / dashboard / procedure_lego)
docs/     Layers_Short_SOT.md — the Tier-3 replication blueprint
tools/    build_demo_bars.py (mini-bars builder) + verify_repro.py
```

## Research integrity — OOS is read once, never optimized

Every choice — the XGBoost hyper-parameters (Optuna), the per-asset feature subset, and the operating
point (entry threshold, Kelly fraction) — is made on the **Train** window alone, scored by purged
walk-forward cross-validation. The **OOS** window is read **exactly once per asset**, at the verdict
step, and reported as-is; it never feeds back into any decision. Optimizing against OOS would be
research nonsense (fitting the test set). The pipeline is deterministic (`seed_everything`,
`XGBOOST_N_JOBS=1`), so the same input reproduces the same OOS row — which is what `make verify` checks.
The v2 pipeline was **audited by independent adversarial reviewers** across the feature, multi-timeframe,
CV, HPO and calibration paths — verdict: no look-ahead and no OOS-optimization; the 1d/1w context is
joined by close-time availability (`merge_asof` backward), so no in-progress coarse bar leaks into a
mid-session decision; and every Train-side scorer (L7 HPO, L8 calibration) carries a fail-closed assert
that its CV folds stay strictly before the OOS boundary.

## How the strategy works — one coherent procedure, applied identically to every asset

The **same procedure runs for every ticker**; the ENTRY_GATE, barrier ratio, Kelly cap and search space
are fixed global constants (never per-asset, never fitted to the test period). What differs per asset —
the selected feature subset, the XGBoost hyper-parameters, the operating point — are all **outputs** of
this identical procedure, decided on **Train data only**.

**1 — The trading strategy (meta-labeling).** A *primary* rule proposes trades; a *secondary* model
decides which to take. Primary: direction = `sign(log_return_5)`, kept only when the move is significant
(`|log_return_5| ≥ 0.15 · realized_volatility_20`, the fixed causal `ENTRY_GATE`). Label: an **asymmetric
ATR Triple Barrier** — take-profit `2·ATR14`, stop `1·ATR14` (reward:risk `b = 2`), time barrier `H = 24`
bars; `Y = 1` if that trade nets positive. Secondary: an **XGBoost** classifier on the per-asset feature
subset predicts `p = P(Y=1)`. Execution: one position at a time, enter if `p ≥ θ`, size by **payoff-aware
fractional Kelly** `f = clip(λ·(p − (1−p)/b), 0, cap)` — exactly `λ·(2p−1)` when the barrier is symmetric,
larger (correctly) at `2:1`. Fees + slippage both sides, mark-to-close equity. Assets whose model never
clears `θ` on OOS honestly fall back to a **buy-and-hold benchmark** rather than forcing trades.

**2 — Optuna tuning (per asset, Train only).** Optuna searches the XGBoost hyper-parameters
(`max_depth/eta/subsample/colsample/min_child_weight` + regularizers `reg_lambda/reg_alpha/gamma` +
`n_estimators`) and **maximizes the model's own Train out-of-fold trading log-growth** — the deployed
engine over a coarse (θ,λ) grid — **not** a ranking score like AUC-PR. So the hyper-parameters are
chosen for **profit** (`STRATEGY_OBJECTIVE.primary = profit_factor_max`), the fix for the old
`OPTUNA_OBJECTIVE: auc_pr` miscalibration. Purged walk-forward CV; AUC-PR is reported only.

**3 — Feature selection (per asset, Train only).** Each asset's optional-feature subset is chosen by a
forward search scored on Train CV behind an overfit gate, and recorded in
`data/per_asset_feature_overrides.json` (provenance = the Train-CV metric; the always-on 1h core is
never overridable). The feature *set* therefore differs by asset — but it is an **output of the uniform
Train-only procedure**, exactly like the per-asset hyper-parameters; nothing is hand-set and nothing
reads OOS.

**4 — Train is optimized; OOS is the honest result.** Steps 1–3 look **only** at the Train window
(2016–2023), scored by purged + embargoed walk-forward CV. Then, with every choice frozen, the strategy
is run **once** on OOS (2024 → 2026): candidates generated once, scored once, simulated once — **exactly
the number you would have gotten standing on the first OOS day (2024-01-02) with only prior data, having
built the strategy on that data**. No OOS value ever flows back into any choice (enforced by asserts;
independently audited).

## Honest full-universe result — v2's strategy levers did NOT beat the baseline

Reported transparently, because the research discipline is the point. On a small dev sample (~18
tickers) v2 looked like a clear win (e.g. AAPL profit factor 1.21 → 1.89). But the **one-shot OOS over
the full ~400-asset universe** — the real test — tells a different, honest story: **v2 does not improve
the aggregate.** Median profit factor fell (0.87 → 0.57) and the fraction abstaining to the buy-and-hold
benchmark jumped (≈32% → ≈67%), because the **asymmetric 2:1 barrier** makes wins rare enough that most
assets never clear the entry threshold. On the assets that *do* trade in both versions, v2 is a slight
improvement (median PF 0.87 → 0.92), but that does not offset the mass abstention. The small dev sample
simply flattered the result — which is exactly why the honest test is the whole universe, read once.

**What stands:** the *methodological* fixes are correct and worth keeping — Optuna now optimizes
tradeable **log-growth** instead of AUC-PR (the fix for `OPTUNA_OBJECTIVE`), the generalized Kelly is
mathematically exact (`2p−1` at `b=1`, byte-identical to the old rows), regularization (`reg_alpha`,
`gamma`) is wired, and the pipeline is audited leak-free. **What did not earn its keep:** the *strategy*
levers (the 2:1 barrier + the entry gate) over-fit the small sample and do not generalize. The sealed
results below are the honest v2 numbers as-produced; the `data/*OLD*` backup and the `main` /
`preparing_to_present` branches retain the prior baseline for comparison.

## Pipeline layers (L1 → L9)

| Layer | What it does |
|---|---|
| L1–L3 | Raw 1h OHLCV (Alpaca) → external upstream DuckDB → `data/liora.duckdb` (`bars_1h`), verbatim |
| L4 | Clean 1h OHLCV + deterministic 1d / 1w roll-ups (parquet) |
| L5 | Warmup / Train / OOS split with purge + embargo (OOS unread until the verdict) |
| L6 | Candidate side = `sign(log_return_5)` behind a causal `ENTRY_GATE`; **asymmetric** ATR Triple-Barrier (TP `2·ATR14` / SL `1·ATR14`, `b=2`), H=24; namespaced 1h/1d/1w features |
| L7 | Optuna tunes XGBoost (+`reg_alpha`/`gamma`) by **Train out-of-fold trading LOG-GROWTH** (not AUC-PR); operating point (θ, Kelly λ) calibrated on Train OOF; generalized Kelly `f=λ(p−(1−p)/b)` |
| L8 | XGBoost trains on full Train, embedded as base64 in `strategy_<TICKER>.py` |
| L9 | One-shot OOS verdict → results row, README, and the 7-file `Assets/<TICKER>/` folder |

Features are namespaced and concatenated in a deterministic order (`1h` 01–99, `1d` 101–199,
`1w` 201–299, `multi_tf` 901–999), resolved from `src/config/feature_namespaces.json`. Full contract:
`docs/Layers_Short_SOT.md`. Per-asset deliverable = 7 files (executed notebook, 1h/1d/1w parquet,
Optuna best-params, base64 strategy artifact + selfcheck, OOS README).

MIT-style coursework demo. `main` / `preparing_to_present` keep the full research apparatus (the
continuous feature-search loop, the build/check doc-gate); this `show_able` branch is the trimmed exhibit.

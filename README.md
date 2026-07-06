# S&P 500 ML Portfolio — the unified two-tier project (branch `LSTM_XGB_DONE`)

One coherent **Streamlit** application over two research tracks of the same S&P 500 project:

- **Track A — sealed per-asset pipelines**: **XGBoost** (1h bars, multi-timeframe) and **LSTM**
  (daily bars), each at the common **v2** standard (profit-aligned Optuna, generalized Kelly,
  purged + embargoed CV, **one-shot OOS 2024→2026**) and **independently audited leak-free**.
  Clone it and the app renders immediately from the sealed results — nothing to train.
- **Track B — ranking recommender** (vendored from the parent project's 6-year export): the
  9-question risk questionnaire → profile → rule-based portfolio packages over Random-Forest
  63-day-return rankings — presented honestly as the **exploratory tier**.

The two tiers never share a results table; every number carries its tier badge. The bridge between
them is the **portfolio rule, not the model scores** — preset packages on the sealed tier use
strictly **pre-OOS inputs** (Train-CV score, ≤ 2023-12-29 risk stats, static sectors), because
Track B's rankings are dated at the *end* of the sealed OOS window and would be look-ahead.
Full write-up: **`docs/UNIFIED_APP.md`**.

## Run it — two commands

```bash
make deps      # once: one .venv + pinned deps (CPU torch + xgboost + streamlit + matplotlib …)
make app       # the unified multi-page app on :8503
```

| command | what it does |
|---|---|
| `make app` | Unified app: Project Report · Data Explorer · Risk Profile · Recommender (Track B) · Basket Simulator (Track A) · Methodology & Integrity |
| `make test-app` | correctness gates (pre-OOS fail-closed, package rule, HODL seal) + AppTest smoke of every page |
| `make verify-xgb` | reproduce the XGBoost demo tickers from `xgb/`'s bundled mini-bars == the sealed rows |
| `make verify-lstm` | reproduce a diverse LSTM sample from `lstm/`'s committed manifest == the sealed rows |
| `make preoos` / `make seal-xgb-hodl` | offline producers of the committed app inputs (already run and committed) |

## Layout

```
app/     the UNIFIED Streamlit app — app.py (st.navigation entry), page_*.py, package_builder.py,
         risk_assessment.py, plots.py, common.py, data/ (tickers.csv, preoos_inputs.csv, trackB/ CSVs)
xgb/     the XGBoost pipeline (1h, L1–L9) — src/ engine, data/ (oos_metrics.db 498 + mini bars), plan/ site
lstm/    the LSTM pipeline (daily, D1–D9) — flat engine, data/ (sp500_1d.duckdb) + oos_metrics.db 496, dashboard/ site
fs/      the WO-FS feature-selection study engine (not mounted in the app; run via make fs-*)
tools/   seal_xgb_hodl.py · make_preoos_inputs.py · test_app.py
docs/    UNIFIED_APP.md (the app + tier design) · PROJECT_STATE.md (Track-A handoff, audits, re-seal)
README.md  Makefile  requirements.txt  .gitignore
```

Each pipeline is vendored **exactly as committed and verified** on its `*_STRATEGY_OPTIMISATION`
branch — each still runs and `make verify`-reproduces on its own.

## Honest status — read `docs/PROJECT_STATE.md` first

This is a **scientific** project, so the headline is honest: the sealed numbers are the **strategy-v2**
results, and the one-shot OOS over the *full* universe showed **v2 does not beat the prior baseline** —
XGBoost is clearly worse (median profit factor 0.87 → 0.57; ~⅔ of assets abstain to buy-and-hold under
the 2:1 barrier), LSTM is a wash (0.984 → 0.962). A small dev sample flattered the result; the whole
universe read once is the honest test. In the strong 2024→2026 bull window the models beat their own
buy-and-hold benchmark on a minority of assets (XGB 64/498) — shown, not hidden. **What is correct and
worth keeping** — the *methodology*: Optuna optimizes tradeable **log-growth** (not AUC-PR), the
generalized Kelly is mathematically exact (`2p−1` at `b=1`, byte-identical to the old rows), and both
pipelines are audited free of look-ahead and OOS-optimization. Track B's verdict is equally honest: a
weak-but-positive **exploratory** rank signal (walk-forward Spearman ≈ 0.06, no purge, gross returns),
plus a genuine leakage catch (`history_days` removed) and a deep-learning model tested and rejected.

## Research integrity (Track A, both pipelines)

Every choice — hyper-parameters, per-asset feature subset, operating point (θ, Kelly λ, direction) — is
made on the **Train** window alone, scored by purged + embargoed walk-forward cross-validation with
fold-causal normalization. The **OOS** window (2024 → 2026) is generated and scored **exactly once per
asset**, at the verdict step, and reported as-is — *exactly the number you would have gotten standing on
the first OOS day (2024-01-02) with only prior data*. No OOS value ever feeds back into any decision
(enforced by fail-closed asserts in the HPO, the operating-point calibration, and the feature search;
independently audited). Deterministic per seed, so `make verify-*` reproduces the sealed rows.

Coursework/research demo. Source pipelines: `1000-LSTM-Liora` and `liora-project-ml-engineering`
(`main` carries the parent project's report corpus and Track-B experiment folders).

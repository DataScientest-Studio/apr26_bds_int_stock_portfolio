# 10000-xgb-lstm-liora

A **unified, standalone** research project that consolidates two per-asset ML trading studies over the
S&P 500 into one presentable exhibit: **XGBoost** (1h bars, multi-timeframe) and **LSTM** (daily bars),
each brought to a common **v2** standard (profit-aligned Optuna, generalized Kelly, one-shot OOS) and
**independently audited leak-free**. Clone it and the app renders immediately from the sealed results —
nothing to train.

## Run it — two commands

```bash
make deps      # once: one .venv + pinned deps (CPU torch + xgboost + streamlit …)
make app       # the demo: shared ML Basket Simulator on :8503, dropdown XGBoost (default) / LSTM
```

| command | what it does |
|---|---|
| `make app` | ML Basket Simulator — pick a model (XGBoost/LSTM), pick tickers (each $1000), see the basket over that model's OOS window |
| `make verify-xgb` | reproduce the XGBoost demo tickers from `xgb/`'s bundled mini-bars == the sealed rows |
| `make verify-lstm` | reproduce a diverse LSTM sample from `lstm/`'s committed manifest == the sealed rows |

## Layout — symmetric at the top, each subproject self-contained

```
xgb/     the XGBoost pipeline (1h, L1–L9) — src/ engine, data/ (oos_metrics.db 498 + mini bars), plan/ site, its own Makefile
lstm/    the LSTM pipeline (daily, D1–D9) — flat engine, data/ (sp500_1d.duckdb) + oos_metrics.db 496, dashboard/ site, its own Makefile
app/     the SHARED Streamlit basket simulator (reads both sealed stores via a method dropdown)
docs/    PROJECT_STATE.md — the full handoff: what was done, the re-seal, prior versions, and what to do next
README.md  Makefile  requirements.txt  .gitignore
```

Each subproject is vendored **exactly as it was committed and verified** on its `*_STRATEGY_OPTIMISATION`
branch — so each still runs and `make verify`-reproduces on its own. The internal layouts differ (XGB
uses `src/`, LSTM is flat); unifying them is a documented item for the refactor.

## Honest status — read `docs/PROJECT_STATE.md` first

This is a **scientific** project, so the headline is honest: the sealed numbers are the **strategy-v2**
results, and the one-shot OOS over the *full* universe showed **v2 does not beat the prior baseline** —
XGBoost is clearly worse (median profit factor 0.87 → 0.57; ~⅔ of assets abstain to buy-and-hold under
the 2:1 barrier), LSTM is a wash (0.984 → 0.962). A small dev sample flattered the result; the whole
universe read once is the honest test. **What is correct and worth keeping** — the *methodology*:
Optuna now optimizes tradeable **log-growth** (not AUC-PR), the generalized Kelly is mathematically
exact (`2p−1` at `b=1`, byte-identical to the old rows), regularization is wired, and both pipelines are
audited free of look-ahead and OOS-optimization. **What did not earn its keep** — the *strategy* levers
(asymmetric 2:1 barrier + entry gate).

`docs/PROJECT_STATE.md` is the reference for the upcoming refactor: it records every change and why, the
re-sealing process and verdict, the correctness contract (math / algo-trading / investment principles),
and the concrete next candidates (e.g. profit-Optuna-only with a symmetric barrier). The prior baselines
remain on the source repos' `main` / `show_able` branches.

## Research integrity (both pipelines)

Every choice — hyper-parameters, per-asset feature subset, operating point (θ, Kelly λ, direction) — is
made on the **Train** window alone, scored by purged + embargoed walk-forward cross-validation with
fold-causal normalization. The **OOS** window (2024 → 2026) is generated and scored **exactly once per
asset**, at the verdict step, and reported as-is — *exactly the number you would have gotten standing on
the first OOS day (2024-01-02) with only prior data*. No OOS value ever feeds back into any decision
(enforced by fail-closed asserts in the HPO, the operating-point calibration, and the feature search;
independently audited). Deterministic per seed, so `make verify-*` reproduces the sealed rows.

Coursework/research demo. Source pipelines: `1000-LSTM-Liora` and `liora-project-ml-engineering`.

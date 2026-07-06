# PROJECT STATE & HANDOFF — 10000-xgb-lstm-liora

*Reference for the upcoming refactor. Records what exists, what was done, how the re-sealing went, the
honest verdict, the correctness contract, and the concrete next steps. Read this before changing code.*

Last updated: 2026-07-05.

---

## 1. What this repo is

A consolidation of **two per-asset ML trading pipelines** — `xgb/` (XGBoost, 1h bars) and `lstm/` (LSTM,
daily bars) — each vendored **as-committed** from its `v2` branch, next to a **shared** Streamlit basket
app (`app/`). It is a **clean state + infrastructure** for forward decisions: the methodology is correct
and audited, the results are honest (and, as it turns out, not an improvement over baseline — see §5).
Each subproject remains independently runnable and `make verify`-reproducible.

**Provenance (source of record):**

| subproject | source repo | branch @ commit | layout | sealed rows |
|---|---|---|---|---|
| `xgb/` | `liora-project-ml-engineering` | `XGB_STRATEGY_OPTIMISATION` @ `4142554` | `src/` | 498 |
| `lstm/` | `1000-LSTM-Liora` | `LSTM_STRATEGY_OPTIMISATION` @ `a87f26f` | flat | 496 |
| shared `app/` | `1000-LSTM-Liora` | `two_show_branches_merged` @ `ada0cd6` | METHODS-registry | — |

Baselines (pre-v2) are preserved on each source repo's `main` (`9417e80` / `2e80905`) and `show_able`
(`38a1d38` / `e845c7f`) branches, and in the `*OLD*` backup DBs the re-seal saved.

---

## 2. The two source pipelines (shared design)

Both are **meta-labeling** strategies with identical trade mechanics (the LSTM engine is a port of the
XGBoost parent), differing only in the model and bar frequency.

- **Universe/data.** `lstm/`: daily S&P 500 bars bundled in-repo (`lstm/data/sp500_1d.duckdb`, ~18.5 MB,
  503 symbols, 2016→2026). `xgb/`: 1h bars — a 5.6 MB **mini** store (`xgb/data/bars_demo.duckdb`, 15
  demo tickers) ships committed for `make verify`; the full 160 MB `xgb/data/liora.duckdb` stays **local
  + gitignored** (built from an external Alpaca upstream), needed only to re-run beyond the demo set.
- **Layers.** L1–L3 raw bars → store; L4 clean + (XGB) deterministic 1d/1w roll-ups; L5 warmup/Train/OOS
  split with **purge (=H) + embargo**; L6 candidates + Triple-Barrier label; L7 Optuna HPO on purged
  walk-forward CV; L8 operating-point calibration + final refit + base64 strategy artifact; L9 **one-shot
  OOS** → results row + per-asset folder.
- **Splits.** Warmup 2016 · Train 2017–2023 · OOS 2024-01-02 → 2026 (XGB ends 2026-05-29, LSTM 2026-04-30).
  H=10 (LSTM daily) / H=24 (XGB 1h); embargo 10 / 35 bars.
- **Determinism.** `seed_everything`, single-threaded model (`XGBOOST_N_JOBS=1` / torch 2 threads,
  deterministic algorithms). A rerun reproduces the OOS row **byte-identically** — what `make verify`
  checks. XGB `run_asset` executes `notebook_template.ipynb` (nbconvert); LSTM `run_asset` is a script.

---

## 3. The v2 changes (what was done + WHY)

The starting complaint: *"profit factor too low; Optuna doesn't calibrate the right values."* Grounded
in the sealed baseline it was real (median PF ≈ 0.98, win rate ≈ 51%, ~no edge). The **self-documented**
smoking gun in XGB: `OPTUNA_OBJECTIVE: "auc_pr"` while `STRATEGY_OBJECTIVE.primary: "profit_factor_max"`.
Five levers were applied to **both** pipelines (each Train-CV-validated, OOS read once):

| Lever | Change | Why | Correctness |
|---|---|---|---|
| **A — Optuna → profit** | HPO objective **AUC-PR → mean Train OOF trading LOG-GROWTH** (run engine over a coarse θ/λ grid), reusing the operating-point machinery | select hyper-params for *profit*, the stated objective — the fix for the miscalibration | log-growth is the Kelly-optimal geometric-growth criterion; fail-closed pre-OOS assert added |
| **A — regularize** | add `weight_decay`+`num_layers` (LSTM) / `reg_alpha`+`gamma` (XGB, now *forwarded* in `_xgb_train`) | reduce the Train→OOS gap | standard regularization |
| **B — asymmetric barrier** | `TB_ATR_MULTIPLIER` → `TB_ATR_TP`/`TB_ATR_SL` = 2/1 | PF headroom (bigger wins than losses) | label still `Y=net>0` |
| **B — generalized Kelly** | `f = clip(λ·(p − (1−p)/b), 0, cap)`, `b = TP/SL` | payoff-aware sizing | **= `λ·(2p−1)` at b=1 → byte-identical to the old rows (proven on AAPL/KO)** |
| **C — entry gate** | keep candidates only when `|log_return_5| ≥ 0.15·realized_volatility_20` | fewer noise-level setups | fixed, causal (features at t0); `enabled=false` = the old every-bar set |
| **D — feature search → profit** | (LSTM) `evaluate()` metric AUC-PR → OOF log-growth | select features for tradeability | XGB: worker not ported to `show_able`; committed per-asset overrides feed v2 |
| **E — operating point (XGB)** | `calibrate_kelly` generalized to joint (θ,λ); **θ PINNED to [0.60]** | per-asset θ calibration was tried and **over-fit** (AAPL OOS PF 1.89→0.99); machinery kept, config-driven | LSTM calibrates (θ,λ,direction); XGB's fixed θ is the HODL cause under 2:1 |

---

## 4. Anti-leakage audit (both pipelines: CLEAN)

Each pipeline was run through an **adversarial 5-dimension audit** (feature/entry-gate/barrier
look-ahead, OOS boundary/read-once, CV/normalization integrity, HPO/calibration semantics, per-asset
uniformity/determinism), with an independent verify pass that tried to *refute* every finding.

- **No look-ahead:** every feature/gate/barrier input uses data ≤ close[t0]; the only next-bar refs are
  the legitimate entry/exit fills. **XGB multi-timeframe is causal** — 1d/1w context is joined by
  close-time availability (`merge_asof` backward), so an in-progress coarse bar never leaks into a
  mid-session decision (verified — a subtle spot).
- **No OOS optimization:** Train candidates purged (`t0+H+embargo ≤ oos_start`, asserted); HPO +
  calibration + feature search all carry **fail-closed pre-OOS asserts**; OOS generated + scored
  **exactly once** at L9, feeding no decision; `cv_auc_pr` is report-only.
- **Fold-causal normalization:** each CV fold's stats use rows before its embargo boundary; OOS uses
  frozen full-Train stats.
- **One procedure per asset:** the ENTRY_GATE, barrier ratio, Kelly cap and search space are fixed
  global constants; the per-asset feature subset + hyper-params + operating point are **Train-only
  outputs** of the identical procedure (not per-asset hand-tuning, not OOS-derived).

The lone audit "leak" verdict was a *wording* point — per-asset feature overrides mean the feature *set*
isn't literally identical across assets — which the verifier itself refuted as "Train-CV-derived, not
OOS-tuned." **Bottom line: no data leakage, no OOS-fitting.**

---

## 5. The re-sealing + the HONEST verdict

**Process.** Both universes were re-run under v2 on a 16-core box: resumable parallel runners (skip
tickers already sealed), **live CPU/RAM rebalancing** (e.g. XGB up to 10 workers @ OMP=1, LSTM up to 7 @
2 threads), bars **warmed into the page cache** so workers read from RAM. Each finished with
`make verify` reproducing the demo/sample rows **byte-identically**. XGB skipped 5 recent IPOs, LSTM 7.

**Verdict (one-shot OOS over the FULL universe — the honest test):**

| | XGBoost (498) | LSTM (496) |
|---|---|---|
| median profit factor | 0.87 → **0.57** | 0.984 → **0.962** |
| PF > 1 | 109/395 → 52 | 230 → 221 |
| buy-and-hold abstention | 32% → **67%** | ~7% → ~8% |
| trading assets (both ≥10 trades) | PF 0.87 → 0.92 (n=73) | PF 0.999 → 0.977 (n=370) |
| result | **clearly worse** | **wash / marginally worse** |

**Why.** The 2:1 asymmetric barrier makes wins rare → probabilities rarely clear the entry threshold. XGB
uses a **fixed θ=0.60**, so two-thirds of assets produce **zero model trades** and fall back to
buy-and-hold; LSTM calibrates θ down, so it keeps trading and lands near-neutral. On the assets that do
trade, v2 is a slight edge — but that doesn't offset the mass abstention.

**Key lesson (record it):** the small dev samples (~18–20 tickers) showed a clear win (e.g. AAPL PF
1.21→1.89) and **misled** the decision. **Validate any strategy change on the full universe, read once,
before believing it.**

---

## 6. What stands vs what to reconsider (for the refactor)

**KEEP (correct, worth carrying forward):**
- Profit-aligned Optuna objective (Train OOF log-growth), with the pre-OOS asserts.
- Generalized Kelly `f = clip(λ·(p − (1−p)/b), 0, cap)` (exact, byte-identical at b=1).
- Regularization in the search space (weight_decay/num_layers · reg_alpha/gamma).
- The audited **leak-free structure** + **one-shot-OOS** discipline + determinism.

**RECONSIDER / REVERT (did not earn their keep):**
- The **asymmetric 2:1 barrier** + the **entry gate** — they over-fit the small sample and don't
  generalize; they are the cause of the aggregate degradation (esp. XGB's mass HODL).
- For XGB specifically: if asymmetric barriers stay, **calibrate θ per asset** (a fixed θ=0.60 with a
  2:1 label is the direct HODL cause). But note θ-calibration *itself* over-fit in the L8 test — a
  more conservative θ grid or a nested-CV calibration may be needed.

**Untested candidate to try first (cheapest honest experiment):** **profit-Optuna-only** — keep Lever A
(profit objective + regularization + anti-leak) but **revert the barrier to symmetric (1:1) and disable
the entry gate**. This isolates whether the *methodological* fix alone is neutral-or-better. Set
`TB_ATR_TP = TB_ATR_SL = 1` and `ENTRY_GATE.enabled = false`, re-seal both universes once, read OOS once,
compare to baseline. (Config-only change; no code edits.)

---

## 7. Correctness contract (the presentation must stand on this)

- **Mathematics.** Kelly derivation: for a b:1 payoff, `f* = p − (1−p)/b`; at b=1, `f* = 2p−1` (the
  even-money case) — proven byte-identical to the pre-v2 sealed rows. The HPO/calibration objective is
  **log-growth** `Σ log(E_end/E0)`, the correct geometric-growth (Kelly-optimal) criterion, not a proxy.
- **Algo-trading.** Textbook meta-labeling (primary momentum+gate entry, secondary ML win-probability
  filter), asymmetric reward:risk with fractional Kelly, **purged walk-forward CV with embargo**, an
  operating point chosen **out-of-fold**, and an honest **buy-and-hold benchmark** shown next to the
  model — each a standard, citable practice.
- **Investment principle / no leakage.** Everything is decided on **Train only**; OOS is read **once**
  and reported as-is — *as if standing on the first OOS day with only prior data*. Enforced by asserts,
  independently audited. Deterministic, so results are reproducible (`make verify-*`).

---

## 8. Open normalization items for the refactor

1. **Unify the internal layout** — `xgb/` uses `src/`, `lstm/` is flat; the sealed store is
   `xgb/data/oos_metrics.db` vs `lstm/oos_metrics.db`. Pick one convention (e.g. `src/` + `data/` for
   both) and repoint the shared app.
2. **One engine vs two** — the trade engine (`run_engine`, `simulate_trade`, Triple Barrier, purged
   folds, generalized Kelly) is duplicated; consider a shared `engine/` both models import.
3. **One venv / one requirements** — already unified at the root (`make deps` symlinks `.venv` into each
   subproject); fold the per-subproject requirements away.
4. **XGB buy-and-hold feed** — the LSTM dashboard carries `hodl_return_pct`; XGB's does not, so the app
   shows the benchmark only for LSTM. Bake it from the local full store (mirror LSTM's `hodl_returns`).
5. **Feature-search parity** — the LSTM search worker was realigned to the profit metric; the XGB worker
   lives on `preparing_to_present` (not vendored). Port + realign if the loop matters going forward.
6. **The strategy decision** — implement §6: try profit-Optuna-only first, then decide on barriers/gate.

---

## 9. How to reproduce / verify

```bash
make deps                 # one .venv + pinned deps
make app                  # shared basket simulator (:8503), dropdown XGBoost/LSTM
make verify-xgb           # xgb demo tickers reproduce the sealed rows byte-identically
make verify-lstm          # lstm sample reproduces
# to re-run beyond the XGB demo set you need the full local xgb/data/liora.duckdb (gitignored, 160 MB)
```

The sealed stores (`xgb/data/oos_metrics.db` 498, `lstm/oos_metrics.db` 496), both dashboards, the mini
XGB bars, and the full LSTM daily bars ship committed — a fresh clone shows everything with zero training.

# 1000-LSTM-Liora

A minimal, fully reproducible per-asset **LSTM** trading pipeline over daily S&P 500
bars, with a client-facing basket demo on top. **Clone it and it runs** — the daily
data store *and the sealed OOS results* ship inside the repo, so the Streamlit app and
dashboard render immediately with nothing to train; nothing is downloaded at runtime,
every number is deterministic for the pinned environment, and `make verify` reproduces
any asset from the committed manifest. Architectural sibling of the XGBoost project
`liora-project-ml-engineering`: same research discipline (Triple-Barrier labels, purged
walk-forward CV, Kelly sizing, one-shot OOS), different model class.

**Run & use:**

```bash
make deps                      # one-time: .venv + pinned CPU-only deps (torch)
make app                       # ML Basket Simulator (Streamlit) — shows sealed results NOW: :8502
make on                        # OOS dashboard (static, sortable): http://localhost:8010/dashboard.html
make stats                     # honest one-shot-OOS results snapshot (read-only)
make verify                    # reproduce a diverse sample from the committed manifest == sealed rows
make run-asset TICKER=AAPL     # re-train one asset + one-shot OOS — reproduces its row
```

## How the strategy works — one coherent logic, applied identically to every asset

The **same four-step procedure runs for every ticker**; nothing is hand-tuned per asset and no
global constant is fitted to the test period. Per-asset differences (which features, which
hyper-parameters, which operating point) are all *outputs* of this identical procedure, decided on
**Train data only**.

**1 — The trading strategy (meta-labeling).** A *primary* rule proposes trades; a *secondary* model
decides which to take.
- **Primary (entry):** direction = `sign(log_return_5)` (5-day momentum), kept only when the move is
  significant — `|log_return_5| ≥ 0.15 · realized_volatility_20` (a fixed causal noise filter, the
  `ENTRY_GATE`). Every input is known at the decision close `t0`.
- **Barrier / label:** an **asymmetric ATR Triple Barrier** — take-profit at `2·ATR14`, stop at
  `1·ATR14` from the next-open entry (reward:risk `b = 2`), time barrier `H = 10` sessions. The label
  is `Y = 1` if that trade nets positive after costs.
- **Secondary (the LSTM):** a 1–2 layer LSTM over the 60-session window of causal, Train-normalized
  features predicts `p = P(Y=1)`.
- **Execution (the engine):** one position at a time; enter only if `p ≥ θ`; size by **payoff-aware
  fractional Kelly** `f = clip(λ·(p − (1−p)/b), 0, cap)` — which is exactly the classical `λ·(2p−1)`
  when the barrier is symmetric (`b = 1`), and larger, correctly, when wins pay `2:1`. Fees +
  slippage both sides, mark-to-close equity, halt on capital depletion.

**2 — Optuna tuning (per asset, Train only).** Optuna runs a small seeded study over the LSTM
hyper-parameters — `hidden ∈ {16,32,64}`, `lr`, `dropout`, **`weight_decay` (L2 regularization)** and
**`num_layers ∈ {1,2}`** — and **maximizes the model's own Train out-of-fold trading log-growth**
(Σ log(end/start) from the engine above), *not* a ranking score like AUC-PR. So the hyper-parameters
are chosen for **profit**, measured by purged walk-forward cross-validation. Regularization
(`weight_decay`) is in the search because the hard part is not fitting Train — it is generalizing to
the unseen window.

**3 — Feature selection (per asset, Train only).** Beyond the 13 always-on CORE features, a forward
search adds features from an OPTIONAL bank one at a time, scored by the **same** Train out-of-fold
log-growth, behind an **overfit gate**: a feature must lift the score by a minimum margin, help in a
majority of folds, and survive a complexity penalty and averaging over independent seeds — otherwise
it is not added. The winning subset is the asset's feature manifest. A Claude-proposed feature DSL
can grow the bank, but every proposal is causal by construction.

**4 — Train is optimized; OOS is the honest result.** Steps 1–3 look **only** at the Train window
(2017–2023), scored by purged + embargoed walk-forward CV with fold-causal normalization. Then, with
every choice frozen — hyper-parameters, features, operating point (`θ, λ, direction`) — the strategy
is run **once** on the out-of-sample window (2024 → 2026): candidates generated once, scored once,
simulated once. **This is exactly the number you would have gotten if you had stood on the first OOS
day (2024-01-02) with only the data up to then, built the strategy on that data, and let it run.** No
OOS value ever flows back into any choice — enforced by hard purge/OOS-boundary asserts in the code,
and independently audited for look-ahead / OOS-leakage across the feature, normalization, CV, HPO and
calibration paths. See *Research integrity* below.

## Research integrity — the out-of-sample window is read once and never optimized

This is the methodological core, so it leads the document. **Nothing about the strategy is
ever chosen by looking at the out-of-sample (OOS) result.** Every decision — the LSTM
hyper-parameters, the per-asset feature subset, the operating point (entry threshold θ, Kelly
fraction λ, trade direction), and every feature Claude Sonnet proposes — is made on the **Train**
window alone (2017–2023), scored by purged walk-forward cross-validation. The OOS window
(2024 → 2026) is then read **exactly once per asset**, at the very end, and reported as-is.

The self-improving feature-search loop **raises Train-side predictiveness, not the OOS number.**
When a new feature lifts an asset's Train CV past the overfit gate, that asset is re-run and its
single OOS read is refreshed — but the OOS result never feeds back into *which* features, model,
or operating point get chosen. Optimizing against OOS would be **research nonsense**: it silently
fits the test set, and any "edge" so produced is an artifact of look-ahead, not a real signal.
Keeping OOS strictly one-way — read, report, never tune — is what makes the numbers an honest
estimate of unseen-data performance.

The discipline is *enforced*, not merely promised: purge + embargo assertions guarantee no
training label window crosses into OOS, and **every place that scores a trade on Train — the HPO
objective (D7), the operating-point calibration (D8), and the feature search — carries a
fail-closed assert that the fold's label horizon stays strictly before the OOS boundary**; every CV
fold normalizes with fold-causal stats only (no scaler leakage into validation); the OOS window is
normalized with frozen full-Train stats; the feature-selection score uses a light fixed model
averaged over independent seeds, so a subset is picked for its *features*, not for one lucky init or
for anything OOS; the Sonnet proposal DSL is causal by construction (the future is not expressible);
and `make stats` recomputes every quoted figure directly from the one-shot rows, so no result is ever
hand-copied. The v2 pipeline was additionally **audited by independent adversarial reviewers** across
the feature, normalization, CV, HPO and calibration paths — verdict: no look-ahead and no
OOS-optimization; every value that differs per asset is an *output* of the identical Train-only
procedure, never a hand-set or test-fitted constant.

## What ships sealed (clone → show, zero training)

This repo is a **sealed presentation**: the results are committed, so a fresh clone renders the
app and dashboard immediately — no training required. Four small artifacts carry the frozen state:

| File | What it is |
|---|---|
| `oos_metrics.db` | the one-shot OOS result row per asset (495) — what the app & dashboard read |
| `per_asset_feature_overrides.json` | the feature subset the search selected for each asset (444) |
| `features_proposed.json` | the Claude-Sonnet Deep-Research feature bank (14 causal-DSL features) |
| `dashboard/data/dashboard.json` | the prebuilt dashboard feed (model vs buy-and-hold) |

`make verify` re-runs a diverse sample from *these committed files* and asserts each reproduces its
committed OOS row byte-identically — the "clone it and every number reproduces" guarantee. Everything
else (training scratch in `Assets/`, the RAM feature cache, the live search state) stays gitignored
and regenerable. The self-improving search + Sonnet proposer (`make search-on` / `make search-agent-on`)
can be relaunched to grow the bank further; the sealed artifact is a snapshot of that process, not a
dead end.

## Documentation tiers

| Tier | Role | Artifact | Entry point |
|---|---|---|---|
| 1 | Client app | ML Basket Simulator — `app.py` | `make app` → `http://localhost:8502` |
| 2 | Backend explanation | this README + the OOS dashboard | `make on` → `http://localhost:8010/dashboard.html` |
| 3 | Replication blueprint | the D1–D9 layer table + model card + per-asset contract below | rebuild the modules from this document alone |

## Pipeline layers (D1 → D9)

| Layer | Name | What it does |
|---|---|---|
| D1 | Bundled daily store | `data/sp500_1d.duckdb::bars_1d` — 503 symbols × daily OHLCV, 2016-01-04 → 2026-05-22 (1,269,084 rows, 18.5 MB). The frozen input; no acquisition code in this repo. |
| D2 | Load + source QC | One ticker ordered by date; monotone unique dates, finite positive OHLC, high/low bounds, volume ≥ 0 — any violation ⇒ `RuntimeError`, never cleaned. |
| D3 | Time split | Warmup **2016** · Train **2017-01-01 → 2023-12-31** · OOS **2024-01-01 → 2026-04-30**; purge = H = 10 sessions + embargo 10 bars, asserted per event. |
| D4 | Daily features | 13 causal indicators per session (returns, SMA distances, volume z-score, ATR%, realized vol, RSI, Bollinger, MACD histogram), z-scored with **TRAIN-only** per-asset stats; inside CV every fold uses its own **fold-causal** stats (rows strictly before the fold's embargo boundary). |
| D5 | Candidates + label | Primary = `sign(log_return_5)` behind a fixed causal **ENTRY_GATE** (`\|log_return_5\| ≥ 0.15·realized_volatility_20`); **asymmetric** ATR Triple Barrier (TP `2·ATR14` / SL `1·ATR14`, reward:risk `b=2`), entry next open, costs both sides (1 bp + 2 bp); `Y = 1[net > 0]`; label-uniqueness weights. |
| D6 | Sequence tensor | Per candidate: the 60-session window of normalized features ending at t0 — everything derives from data ≤ close[t0]; non-finite windows are excluded, never imputed. |
| D7 | LSTM HPO | 20 seeded Optuna trials (TPE + median pruner) over hidden/lr/dropout/**weight_decay**/**num_layers**; objective = **mean Train out-of-fold trading LOG-GROWTH** (run_engine over a coarse θ/λ grid) over purged walk-forward CV (k=4) — hyper-parameters chosen for profit, not AUC-PR. A hard assert keeps every fold's label horizon pre-OOS. |
| D8 | Refit + Kelly λ | Final refit on full Train (epoch count from the best trial's fold early stops); Kelly λ calibrated on Train out-of-fold log-growth with the **full label horizon** per fold (end = last val t0 + H, provably pre-OOS by the purge invariant); deterministic grid, ties → smallest λ. |
| D9 | One-shot OOS | OOS candidates generated and scored exactly once; trade engine (per-asset calibrated θ, **generalized Kelly** `f = clip(λ·(p−(1−p)/b), 0, cap)` with `b = TP/SL`, fees + slippage, mark-to-close equity); zero model trades ⇒ honestly-labeled HODL fallback. |

## Model card

- **Architecture**: 1–2 layer `nn.LSTM` (searched) over `(60, F)` z-scored windows → dropout →
  linear head → logit of the Triple-Barrier win. Loss = BCE-with-logits, `pos_weight`
  class balance × label-uniqueness weights.
- **HPO**: 20 trials, `TPESampler(seed=42)` + `MedianPruner(warmup=2)`; space:
  hidden ∈ {16, 32, 64}, lr ∈ log[1e-4, 1e-2], dropout ∈ [0, 0.5], **weight_decay ∈ log[1e-6, 1e-2]**,
  **num_layers ∈ {1, 2}**. **Objective = mean Train out-of-fold trading log-growth** (the deployed
  engine, coarse θ/λ grid), so hyper-parameters are selected for profit; AUC-PR is reported only.
  Early stopping per fold on the fold's own validation AUC-PR (patience 4, max 25 epochs, batch 128) —
  a smooth within-fold stop signal, never OOS. Each CV fold is normalized with **fold-causal** z-score
  stats (no scaler leakage into validation); single-class folds are excluded.
- **Determinism**: seeds re-planted before every fold/refit; `torch.use_deterministic_algorithms(True)`,
  2 CPU threads, seeded numpy batching, no DataLoader workers, pinned wheels. A rerun
  reproduces `best_params.json` and the OOS row **byte-identically** (verified).
- **Cost**: ~30 s wall / ~520 MB peak RSS per asset on a 4-core CPU box (no GPU needed).

## Data provenance (acquisition detached)

The repo ships `data/sp500_1d.duckdb` — a deterministic roll-up of an upstream Alpaca
S&P 500 1h store: bars grouped by ET session day, O=first / H=max / L=min / C=last /
V=sum (`tools/build_data.py`, kept as auditable provenance; cloners never run it).
The roll-up was parity-checked row-for-row against the parent project's independently
derived per-asset daily parquets. Prices are **raw** (corporate actions deferred — see
Limitations).

## Per-asset deliverable (`Assets/<TICKER>/`, 3 files + 1 side-effect)

1. `best_params.json` — HPO winner, CV score, Kelly λ, frozen normalization stats.
2. `strategy_<TICKER>.py` — standalone artifact: LSTM `state_dict` embedded as base64
   with a SHA-256 `MODEL_HASH` asserted on load, frozen `NORM_STATS`, golden-vector
   selfcheck (`python3 strategy_<T>.py` — needs only torch + numpy).
3. `<TICKER>_README.md` — the OOS report: capital path, feature table, trade ledger.
4. Side-effect: one UPSERT into `oos_metrics.db` — the row the Basket Simulator and
   the dashboard read.

OOS discipline: the OOS window is read **exactly once**, after HPO, Kelly calibration
and the final refit are all frozen. Purge/embargo assertions guarantee no training
label window crosses the OOS boundary.

## Per-asset feature selection + the self-improving loop

Beyond the fixed CORE features, each asset can search a per-asset subset of an OPTIONAL
feature bank — because the right features differ by asset, and giving the LSTM *all* of
them overfits (28 features on ~1700 daily samples). `feature_search.py` (`make search-on`)
does forward selection per ticker: it scores each optional feature's marginal Train CV
AUC-PR (a light fixed model, so the score reflects the feature, not the tuning), then
greedily grows the subset while CV improves, and **applies a subset only if it beats
core-only by `min_gain`** — a Train-only overfit guard. The winning subset is written to
`per_asset_feature_overrides.json` and the asset is re-run once (its single OOS read).

The bank itself can grow. `make search-agent-on` starts a **Claude Sonnet `/loop`** that
reads the emerging results and proposes NEW features as small expressions in a safe DSL
(`.claude/commands/lstm-search-steer.md`). The worker is the sole validator: every proposal
is parsed under a whitelist grammar (vars `o/h/l/c/v`; `shift(n≥1)`, `rolling_*`, `ewm`,
`zscore`, `rank`, `log`, …), so **any expression that parses is causal by construction** —
the future is not expressible. Valid, non-constant, uniquely-named proposals get an id
(501+) and enter the search pool automatically. The agent writes only the control file;
it never touches code, state, or the OOS window.

This is the honest lever for *edge*: the operating-point calibration (θ/λ/direction) fixes
structural flatness, but only better features move the underlying predictiveness.

## Results & honesty

**Strategy-v2 full-universe verdict (reported transparently — the discipline is the point).** On a
small dev sample (~20 tickers) v2 looked like a modest win (median PF 0.91 → 1.00). But the **one-shot
OOS over the whole ~500-asset universe** — the real test — says v2 does **not** beat the baseline: median
profit factor 0.984 → **0.962**, and on the 370 assets that trade in both versions the median PF is a
wash-to-slightly-worse (0.999 → 0.977, only 174/370 beat the old version). The small sample flattered the
result. **What stands:** the *methodological* fixes are correct and kept — Optuna now optimizes tradeable
**log-growth** (not AUC-PR), the generalized Kelly is exact (`2p−1` at `b=1`, byte-identical to the old
rows), weight-decay regularization is in the search, and the pipeline is audited leak-free. **What did
not earn its keep:** the *strategy* levers (the asymmetric 2:1 barrier + the entry gate) over-fit the
small sample and do not generalize. The sealed numbers below are the honest v2 rows as-produced; the
prior baseline is preserved on `main` and in the `*OLD*` backup. (The XGBoost sibling shows the same —
in fact worse, because its fixed entry threshold sends ~⅔ of assets to buy-and-hold under the 2:1 label.)

The OOS window (2024→2026) was a strong bull market — buy-and-hold beat most active daily
strategies over it (HODL median ≈ +20%). This project therefore optimizes and reports
**process correctness**, not a claim of beating the market. `make stats` prints the current
one-shot snapshot; at the time of writing, across ~500 assets: ~52% end positive, **~31% beat
their own buy-and-hold benchmark**, **0 zero-trade fallbacks** (down from 191 before the
operating-point calibration — every asset now actually trades), median profit factor ≈ 1.0, and
a median Train `cv_auc_pr` ≈ 0.56 (base rate 0.50 — a weak but *real* ranking signal). The
reading is deliberately unspun: a daily LSTM does not systematically beat a bull, and the
numbers say so.

What the project *does* demonstrate is **method**: Train-only model/feature/operating-point
selection, a one-shot OOS read (never optimized — see *Research integrity* above), byte-identical
determinism, an overfit-gated self-improving feature loop, and — on the dashboard (`make on`) and
in every asset README — the model result shown **next to its `hodl_return_pct` benchmark** so the
comparison is never hidden. A `baseline_summary.json` snapshots the pre-improvement distribution
for a before/after read.

## Limitations (research demo, stated plainly)

- **Survivorship bias**: the universe is the current S&P 500 constituents applied to
  history.
- **Corporate actions deferred**: prices are raw; splits appear as price cliffs
  (NVDA's −59.6% HODL row crosses its 2024 10:1 split — the honest consequence of
  raw prices, kept on purpose and labeled).
- The fill model (close-trigger → next-open exit, fixed bps costs) is a simulation
  contract, not broker-proof execution.
- Per-asset capital paths are independent; the basket is a sum, not a portfolio
  optimizer.
- The HPO budget is deliberately small (10 trials) — the point is a clean, cheap,
  reproducible pipeline, not a state-of-the-art forecaster.

## Quickstart (fresh clone)

```bash
git clone https://github.com/flak92/1000-LSTM-Liora.git
cd 1000-LSTM-Liora
make deps                      # ~5 min: venv + pinned CPU torch
make app                       # THE demo — sealed results, on :8502 (nothing to train)
# — everything below is optional, to reproduce the sealed results yourself —
make verify                    # a diverse sample reproduces the committed OOS rows
make run-asset TICKER=AAPL     # re-train one asset (~30 s) — its OOS row matches what shipped
make on                        # sortable OOS dashboard (model vs buy-and-hold) on :8010
```

**What to show a class in 60 seconds:** `make app` → *Start* → click a handful of tickers →
*Calculate basket* → the basket's LSTM return appears next to the same basket's buy-and-hold, with
the sidebar explaining the ML + Deep-Research scheme. Then `make verify` to prove every number
reproduces from the committed manifest, and point at the *Research integrity* section: the
out-of-sample window is read once and never optimized.

MIT licensed. Built as a coursework demo; see `change-on-lstm.md` in the parent
repository for the full conversion work order.

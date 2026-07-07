# The Unified Streamlit App — one project, two evaluation tiers

*Prepared on branch `LSTM_XGB_DONE` as the presentation deliverable; written to slot into the final
report's Streamlit appendix at merge time. All UI and documentation in English. Nothing trains at
runtime — the app is a viewer over committed artifacts.*

## What it unifies

The project produced two research tracks that answer **different questions under different
standards of evidence**:

| | **Track A — sealed per-asset pipelines** | **Track B — ranking recommender** |
|---|---|---|
| Question | Will *this* proposed trade net positive? | Which stocks rank best on 63-day forward return? |
| Models | XGBoost (1h, multi-timeframe) + LSTM (daily), per asset | Ridge / RF / **RF-no-history** (selected) / XGBoost / PyTorch MLP |
| Label | Triple-Barrier (TP 2×ATR / SL 1×ATR), `Y = net>0` after costs | Continuous 63-trading-day forward return |
| Validation | Purged + embargoed walk-forward CV; **one-shot OOS 2024→2026 read once**; fail-closed asserts; adversarial audit; byte-reproducible | Fixed split + 13-fold walk-forward **without purge/embargo**; gross returns; selection on the test split |
| Sizing / costs | Generalized Kelly; 1bp + 2bp per side | Equal-weight top-N; no execution model |
| Benchmark | Per-asset buy & hold, same OOS window | Universe average per fold |
| Honest verdict | v2 did **not** beat baseline; the *method* is the product | Weak-but-positive exploratory rank signal (WF Spearman ≈ 0.06) |

The unified app keeps the tracks on separate pages with **permanent tier badges** and never mixes
their numbers in one table.

## Pages

1. **Project Report** — the two-track narrative, the methodology ladder, the honest verdicts, and
   how the tracks connect without cheating.
2. **Data Explorer** — the parent project's Exploration section + 6 mentor-validated DataViz plots,
   each with its live "statistical validation" expander, recomputed from the committed daily store
   (`lstm/data/sp500_1d.duckdb`, 503 tickers, 2016→2026, raw prices — stated on the page).
3. **Risk Profile** — the 9-question investor questionnaire (ported 1:1). Submitting stores
   `st.session_state["risk_answers"]`; an additive score maps to Conservative / Balanced /
   Aggressive plus portfolio size and sector exclusions.
4. **Recommender (Track B)** — the parent's recommendation page over the **vendored** CSVs
   (`app/data/trackB/`): preference controls prefilled from the questionnaire, the verbatim
   selection rule on `predicted_63d_return`, model metric tiles, walk-forward table, feature
   importances, the five-model comparison ("deep learning tested, not selected"), CSV export.
   The tier badge marks everything as exploratory; package returns are predictions, not backtests.
5. **Basket Simulator (Track A)** — the sealed demo: pick a model (XGBoost / LSTM), pick tickers
   ($1000 each), read the basket's **realized one-shot OOS** outcome against the same basket's
   buy-and-hold. New: **preset packages** — the same profile rule as Track B, but computed from
   **strictly pre-OOS inputs** (see below), pre-selecting the grid; manual clicking still works.
6. **Pipeline Blueprint (Track A)** — the sealed lego map embedded as end-of-project
   documentation: 17 procedure blocks (bottom→top = the pipeline order, welded by declaration),
   an XGBoost/LSTM view switch, and a per-block "HOW WE THOUGHT · WHAT WE LEARNED" record —
   the lessons-learned way to remember the whole build.
7. **Methodology & Integrity** — why "sealed" means something, what the exploratory tier lacks,
   shared limitations (survivorship, raw prices/splits, IEX volumes, bull OOS window), and the
   rules of engagement the app enforces.

## The look-ahead problem, and how the app avoids it

Track B's rankings are dated **2026-06-08** — the *end* of Track A's OOS window
(2024-01-02 → 2026-05-29/04-30). Selecting tickers by those rankings and then displaying their
sealed OOS results would be **look-ahead selection** — the exact failure mode the sealed tier was
built to prevent. The preset packages therefore use only inputs knowable before the OOS window:

| Input | Source | As-of |
|---|---|---|
| Ranking score | `cv_auc_pr` — Train-CV AUC-PR sealed in each `oos_metrics` row | Train only (≤ 2023) |
| Volatility cap / momentum filter | `app/data/preoos_inputs.csv` from the committed daily store (`tools/make_preoos_inputs.py`, **fail-closed** on any date > 2023-12-29) | 2023-12-29 |
| Sector (cap + exclusions) | `app/data/tickers.csv` (static GICS metadata) | static |

The selection rule itself is the parent project's, ported verbatim (greedy pick, ≤ sector share,
per-profile volatility caps 0.35/0.50/0.80, relax-only-the-vol-cap when underfilled, equal weight);
the three objectives become unit-free z-score analogues because `predicted_63d_return` cannot be
used. The rule was fixed ex-ante in the parent project and is never tuned against displayed
outcomes. Since the sealed rows were published before the rule was ported, preset baskets are
presented as an *illustration of a fixed rule* — not a new out-of-sample claim.

## Fixes and additions made for the unified app

- **XGB buy-and-hold feed sealed** (`tools/seal_xgb_hodl.py`): after the v2 re-seal,
  `xgb/plan/data/dashboard.json` carried `hodl_return_pct` on 0/498 assets — the simulator's
  default method had no benchmark. Re-sealed with the LSTM feed's exact convention (first open →
  last close over the OOS window) from the committed daily store: **498/498**, model beats
  buy-and-hold on 64/498 (honest: a strong bull window).
- **Pre-OOS inputs table** (`tools/make_preoos_inputs.py` → `app/data/preoos_inputs.csv`):
  498 tickers, volatility/momentum as of ≤ 2023-12-29, fail-closed assert.
- **Vendored Track-B artifacts** (~150 KB): tickers.csv + rankings/metrics/walk-forward/feature-
  importance CSVs, taken verbatim from the parent project's 6-year export.
- **App restructured** into `st.navigation` multipage (defense requirement: multi-tab, aesthetic,
  no runtime training). The WO-FS feature-selection study (Polish) is no longer mounted in the
  app; the `fs/` engine remains in the repo untouched.

## Known limitations (stated, not hidden)

- **Raw prices** in the Track-A store: corporate actions deferred; a split-crossing ticker's
  absolute numbers (e.g. NVDA 2024) are path arithmetic, not economics. Engine and benchmark use
  the same store, so comparisons are internally consistent.
- **Survivorship**: today's constituents applied backward — flatters every universe benchmark.
- **Track B evaluation holes** (no purge/embargo, gross, overlapping labels, test-split selection)
  are described on the Methodology page and badged on the Recommender page.
- **Fold significance**: Track B's 9/13 walk-forward "wins" are not significant at conventional
  levels; the app words it as exploratory evidence.

## Future work (documented, not built)

- **The discipline bridge:** re-run the RF ranking under Track-A discipline — 63-trading-day purge
  in the walk-forward, embargo, the branch cost model, baskets simulated over the sealed OOS
  window against a universe-HODL benchmark. That would produce the one line honestly placeable
  next to Track-A baskets. Until it runs, the tracks are presented as non-comparable by design
  (and even then it lands on an already-published window — post-hoc, and must be labeled so).

## Run & verify

```bash
make deps        # one .venv (CPU torch + xgboost + streamlit + matplotlib/seaborn)
make app         # the unified app on :8503
make test-app    # correctness gates + AppTest smoke of every page
make verify-xgb  # sealed-tier reproducibility (byte-identical rows)
make verify-lstm
```

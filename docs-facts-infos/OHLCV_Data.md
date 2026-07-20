# OHLCV Data — sources, processing and verification

This document describes the **data** in the project: where it comes from, how it is processed
into features and labels, and what verification on real sealed bars confirmed.
Every fact has a source (file / measurement). Status: 2026-07-19, epoch **`2026-07-golden-v5`** (split-adjusted bars),
branch `Stable_Presentable_Version`.

> **Map of references to code and data:** this document describes the data processing as it
> ran on the **research branch** `to_give_up_and_show`, and cites that branch's file layout.
> On this branch the counterparts exist: `src/xgb/pipeline.py`, `src/lstm/pipeline.py`,
> `src/shared/op_select.py`, `config/{xgb,lstm}.json`, `data/results.db`. **Exclusively on
> the research branch**, however, live: the bar stores (the daily `data/sp500_1d.duckdb` and
> the hourly `liora.duckdb`), the bar-loading module `xgb/src/bars.py` with the split
> correction, `xgb/src/corporate_actions.py` together with the `cross_bar_qc` gate and the
> `splits_sp500.csv` / `overrides.csv` tables, the orchestration layer (`run_asset.py`,
> `iterators/`, the `oos_read_ledger.jsonl` ledgers), and the working
> `<T>_ohlcv_1h.parquet` parquets. This branch carries the **result** of that processing:
> 993 sealed artifact folders and `data/results.db` (integrity verifiable offline via
> `make verify`).

## 1. Data sources

Two raw OHLCV streams, one per model:

- **XGB → 1-hour (1h) bars** — S&P 500, one `<T>_ohlcv_1h.parquet` per asset (research
  branch; this branch does not carry bars — see the reference map above).
- **LSTM → daily (1d) bars** — S&P 500, from the `data/sp500_1d.duckdb` store (research
  branch; this branch does not carry bars — see the reference map above).

**The 1d and 1w intervals in the XGB files are NOT a third data source** — they are
**computed from the same 1h stream** as multi-interval context (`CONTEXT_TIMEFRAMES = ("1d","1w")`,
`src/xgb/pipeline.py`). The hourly bars are aggregated into daily and weekly candles and
then **causally** projected back onto the hourly axis (merge_asof after the close of the
completed day/week). Hence the features with `_1d`/`_1w` suffixes (e.g. `volume_z_score_20_1w`)
and the cross-interval alignment features. The `<T>_ohlcv_1w.parquet` snapshot in the
working folders is that same aggregation materialized (for reproduction), not a separate input.

## 2. How the data is processed

The chain: **OHLCV → features / sequences → triple-barrier labels (Train) → per-asset models**.

- **Quality gates (QC) at load time** — time monotonicity, no duplicates, OHLC sanity
  (high ≥ max(open,close), low ≤ min(open,close)), prices > 0, volume ≥ 0
  (`src/xgb/pipeline.py` layer4, `src/lstm/pipeline.py` load_bars).
- **Rolling features** — windows by bar index (rolling(20) etc.), consistent between Train and OOS.
- **1h→1d/1w aggregation** — open = first bar, high = max, low = min, close = last, volume = sum;
  grouping by ET session / ISO week; the context becomes available only once the period completes.
- **Labels** — asymmetric ATR triple-barrier (TP = 2×ATR, SL = 1×ATR); decision at
  close[t0], entry filled at the next session's open; purge/embargo keeps the Train label
  horizon away from OOS. The model makes **the ENTRY decision only**, under a frozen TP/SL
  contract — TP and SL are mechanical barriers, not a model decision.
- **Zero imputation** — missing values are not filled; rows with a non-finite CORE feature are
  excluded from the candidates, optional XGB features may carry NaN (the tree's missing
  branch), LSTM windows with incomplete data are skipped (no fabricated values).

## 3. What verification confirmed (the processing core is healthy)

An in-depth verification (4 independent reviewers, measurements on AAPL, NVDA, ABNB, COIN, CEG,
GEHC, MSFT, VLTO + scans of the entire 498-ticker universe):

| Data area | Result |
|---|---|
| 1h→1d/1w aggregation + causality | ✅ fully correct |
| Per-bar QC gates | ✅ working (498-parquet scan clean) |
| Session features / rolling windows around gaps | ✅ correct and consistent Train↔OOS |
| NaN / warmup / eligibility / LSTM windows | ✅ zero NaN in the core, zero imputation |
| Trade mechanics across gaps | ✅ fair (fill at the real open) |

Evidence:
- **Bit-for-bit aggregation**: manual reconstruction of the 1d/1w candles = **0.0 max error** vs the
  code and vs the sealed parquets (5 tickers, including the ABNB/COIN/GEHC IPOs), with correct
  handling of partial sessions and shortened holiday sessions.
- **Causality proven by truncation**: truncating the input at the boundary of a completed week
  leaves ALL `_1d/_1w`/multi_tf columns bit-identical — **zero forward leakage**;
  a mid-week Wednesday takes the previous period.
- **QC works**: crafted bad frames (duplicate, high<low, price≤0, negative volume) raise
  RuntimeError; the 498-parquet scan = 0 duplicates / 0 non-monotonic / 0 OHLC violations /
  0 negative volume.
- **NaN / warmup**: leading feature NaNs = exactly the window size; the training-matrix core
  = 0 NaN / 0 Inf; IPO-era warmup does not leak (VLTO: 49 bars filtered out); the LSTM
  windows dropped at the finiteness gate are EXCLUSIVELY warmup ones (zero holes in the
  middle of the history); the `n + n_nan == candidates` bookkeeping balances to the row.
- **Trades across gaps**: decision at close[t0], fill at the REAL open of the next session
  with slippage (the overnight/weekend gap is borne, not a fantasy price); purge/embargo
  `t0+H+embargo ≤ oos_start` verified; uniqueness weights in (0,1].

## 4. Splits — CLOSED (epoch 2026-07-golden-v5, 2026-07-19)

The defect described earlier (bars not corrected for splits) **has been fixed at the source**
and the entire pipeline recomputed on the corrected data.

**How it was fixed.** No authoritative source of the factors existed on the server (LEAN has
only 22 sample tickers, without NVDA/AMZN/AVGO; the vendor API returns 401), so the event
table was built **from the data + human review**:
- a detector with a **narrowed** ratio set `{3:2, 2..8, 10, 15, 20, 25, 50}` + inverses —
  a dense grid (8:5, 5:3, 7:4) made **crashes fit better than genuine
  splits** (the FISV −44% crash matched 8:5 with a 0.10% residual), which produced a 17.6% error in both directions;
- **review of all 126 candidates**: 88 auto-accepted, of which 10 removed as false
  positives (the DELL/DD/PNR spin-offs, the KDP special dividend, the PG&E/OPEC/CVNA/TTD/VRT crashes),
  and 5 added by hand (SHW 3:1 and ROL 3:2 just beyond the threshold; HLT and DD 1:3 reverse splits interwoven
  with spin-offs; EXE 1:200 distorted by bankruptcy). **Result: 83 events / 69 tickers**,
  each with a justification in `overrides.csv`. The override table itself holds **28 entries** in total;
  their net effect on the auto-accepted set is the removals and additions described
  (88 → 83 events). Canonical bookkeeping: `Research_Consistency_Report.md` §3.5.
- The correction is applied in `xgb/src/bars.py:load_bars()` (research branch) **on the 1h bars, BEFORE the roll-up**
  (prices × factor, volume ÷ factor); the daily LSTM store rolls up from the same
  corrected stream, so 1h and 1d are consistent by construction.
- `CORP_ACTIONS_POLICY` stopped being dead configuration — `A_adjusted` genuinely branches the code.

**Correctness evidence (measured, not declared):**
| Test | Result |
|---|---|
| LEAN anchor (AAPL) | factor **0.25 → 1.00** — hit exactly |
| Negative control | **434 tickers with no events bit-identical** to the raw bars |
| **Surgical scope of the correction** | of the 497 XGB models comparable across epochs, **436 bit-identical with v4**; only **61** changed — exactly the ones with splits (the v5 universe seals 498 XGB rows) |
| Gaps after the correction | NVDA −90.1% → −0.77%, CMG −98% → +0.98%, AMCR +404.6% → +0.93% |
| 1h↔1d consistency | roll-up == store, exactly (2612 sessions) |
| Cross-bar gates | fire on **every** raw split, **0/503 alarms** after the correction |

The base of **503** in the two rows above is the number of tickers in the **bar store** (434 with
no events + 69 with events), not the number of sealed models: XGB seals 498
rows, LSTM 495 — tickers without a complete set of bars never reach training.

**Effect on the results** (these numbers were previously untrue):
| | v4 (raw) | v5 (corrected) |
|---|---|---|
| NVDA HODL | −56.3% | **+336.6%** |
| CMG HODL | −98.6% | **−27.9%** |
| AVGO HODL | −62.4% | **+276.5%** |
| AMCR HODL | +294.0% | **−20.4%** (reverse-split mirage) |
| beats-HODL XGB | 85/498 | **72/498** |
| beats-HODL LSTM | 143/495 | **129/495** |
| tickers with HODL < −50% | 33 | **22** |

An independent adversarial review predicted these values from the event table alone
(NVDA ~+339%, CMG ~−25%, AVGO ~+280%, AMCR ~−21%, beats-HODL 72 and 131) — the full retrain
confirmed them, which is strong evidence that the correction did exactly what it was meant to do.

**Conscious limitations, stated explicitly:**
- splits **below 3:2 are not detectable from bars** (a scan at |gap|>10% yields ~1000
  random coincidences) — we skip them and document that;
- **spin-offs and special dividends are NOT corrected** — for a price benchmark these are real
  drops, the same class as a dividend;
- volume corroboration is a **review flag, not a gate** (it fails in both directions);
- the only external truth anchor is the LEAN file for AAPL.

## 5. Minor data-quality close-outs (improvements)

- **QC extension**: the current gates check per-bar sanity; a session-completeness /
  flat-bar check is worth adding. 3 market-wide days with incomplete data
  (2021-04-19, 2021-10-25, 2022-03-08; + 2018-05-02/03) collapse the session into a single flat
  bar — **3825 flat bars across 475 tickers (0.4% of all)**, all in Train, the impact
  small and limited to a narrow rolling window. **Closed:** in v5 covered by an explicit
  gate (`cross_bar_qc` in `xgb/src/pipeline.py`, research branch — flat bars with
  share-based thresholds).
- **CLOSE-based barrier detection** is inherently conservative on the win-rate side by ~5 pp (the tighter
  1×ATR SL is touched intra-bar more often than the 2×ATR TP); the mechanism is in the code.
  **Closed:** the direction and scale are described in `docs/METHODOLOGY.md` §6 (the "Barrier
  timing" row).
- **Tuning a sentence in the document** — **Closed:** `docs/METHODOLOGY.md` already defines the
  label by the sign of the net return ("Y = 1 iff the realized net return of the barrier trade is
  positive", with the note that this is a stricter condition than "TP before SL"), consistent with
  the code (`src/lstm/pipeline.py:354`).
- The `*_alignment_multi` features in early history degrade to the available intervals instead
  of becoming NaN — causal and leak-free; to be documented as intended.

## 6. Order of work and the core message about the data

1. **Split correction** — delivered in epoch v5 (section 4 — CLOSED).
2. **Console design — completed** — the console shipped as a four-page Streamlit console over
   the finished `data/results.db` (sole access module `app/data.py`); the split correction
   is documented in `docs/METHODOLOGY.md` §6 (the "Corporate actions" row) rather than on
   a console page.
3. **Communicating what matters most** — the data is a means, not an end:

> This is not about training an artifact for training's sake (maximum fit to the
> data is the road to overfitting). Training is **steered toward `golden_calibration`** —
> we look for a calibrated, NOT-overfitted description of the market (feature value ranges in XGB /
> state sequences in the LSTM), stable enough to act as a **transactional ENTRY filter**
> under a frozen TP/SL contract. This is "cherry-picking of not-overfitted features": one-SE
> plateau per family → simplest representative → economic acceptance → evidence-driven
> boundary proposals. The measure of success is an **auditable system** that shows
> when the model knows enough to signal ENTRY — and when it should stay idle.
> The quality and honesty of the DATA (including the split correction) is the foundation of this
> calibration: well-described data → a credible per-asset filter.

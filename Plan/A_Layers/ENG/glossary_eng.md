# GLOSSARY — S&P 500 ML pipeline (term dictionary)

> **Subordinate to the SOT.** This is a **term dictionary** — concise definitions of every concept in
> Pipeline A. It is **not** the canonical source: the authoritative parameters, formulas, schemas, QC
> predicates and naming forms are owned by [`Layers_Short_SOT/`](Layers_Short_SOT/). Where an entry needs a
> build-critical artifact (a formula, a value, a full table), it **points to the SOT** rather than restating
> it; on any divergence, the SOT wins.

Order = layer by layer (L1 → L10), the way data flows bottom-to-top in the `1 Overview` view of
`viz/main_data_flow.html`; concepts that apply to every layer are gathered under *Cross-cutting concepts*.
Canonical naming forms and notation are owned by
[`Layers_Short_SOT/00_conventions_eng.md`](Layers_Short_SOT/00_conventions_eng.md); parameter values by
[`Layers_Short_SOT/00_parameters_eng.md`](Layers_Short_SOT/00_parameters_eng.md).

---

## Cross-cutting concepts (view `0 Anti-leakage`)

- **ML pipeline** — the whole flow from raw market data to the strategy file and the OOS test; 10 levels L1–L10.
- **S&P 500 universe** — the set of **503 tickers**; the list is pinned in `config/universe.txt`.
- **Asset** — any instrument with OHLCV data; the pipeline is independent of price scale and timeframe.
- **Candle / OHLCV** — a single bar with the five fields `open, high, low, close, volume`.
- **TF (timeframe)** — candle resolution; default `1h`.
- **t / t0** — `t` = candle index (integer after sorting); `t0` = `entry_candle`. Notation owned by `00_conventions_eng.md`.
- **Causality / zero look-ahead** — for candle `t` we use only data from candles `≤ t`; the only forward-looking object is the label window from `t0`. Verified by a CI test.
- **Determinism** — the same input state → the same result; via seeds, artifact hashes and manifests.
- **One-shot** — the OOS window is tested once, after freezing the artifacts; the result never returns to tuning.
- **Gate** — an automatic pass-on condition (QC on the L3 load; a non-FAIL L8 dashboard before training).
- **Parameters** — the only configuration site is `config/params.json`; **all values owned by `00_parameters_eng.md`** (`TF`, `H`, `MIN_TOUCHES`, `W_ATR`, `W_VOL`, `ATR_VARIANT`, `PRICE_VIEW`, `THRESHOLD_ENTRY`, `PURGE_CANDLES`, `EMBARGO_SESSIONS`, `N_TRIALS`, `CV_SCHEME`, `EPS`, …).

---

## L1 · Source: Alpaca SIP · S&P 500 (503)

- **Alpaca Market Data API** — the source of candles; API-key authorization only (headless, no OAuth).
- **feed = sip** (consolidated tape) — one authoritative quote source; no mixing of feeds.
- **RTH session** — regular trading hours 09:00–16:00 ET; ~7 1h candles per session day.
- **cron :05** — incremental update every hour at minute `:05`; **session guard** = no-op outside ET market hours.
- **upsert / idempotency** — a ~5-day-lookback top-up overwrites the tail; repeating the fetch does not change the state.
- **raw prices** — no split/dividend adjustments (open risk **R1**, corporate actions).
- **volume required** — for this universe, missing volume = hard fail QC.

## L2 · LEAN ZIP store (510 zip · prices ×10000)

- **LEAN** — the archive format (QuantConnect): one CSV file per ticker inside a ZIP.
- **1 zip = 1 ticker** — the entire ticker history in `<ticker>.zip`; **510 zip** = 503 universe + a few non-constituents.
- **headerless CSV** — row `YYYYMMDD HH:MM,open,high,low,close,volume`.
- **prices ×10000** (deci-cents) — prices stored as integers; zero floating-point errors in the archive.
- **naive ET timestamp** — local exchange time (`America/New_York`), without a timezone.
- **source of truth / rebuild** — the whole L3 database can be rebuilt from the ZIPs; edits are append/replace per ticker.
- **ET-naive → UTC tz-aware conversion** — done only by the F1 reader at the read boundary (contract in `00_input_contract_eng.md`).

## L3 · DuckDB: raw + VIEW ohlcv_1h (USD) · QC-01…QC-11

- **DuckDB** — the analytical database (file `*.duckdb`) into which we load the ZIPs.
- **`raw_ohlcv_1h` table** — verbatim data (`symbol VARCHAR · ts TIMESTAMP · open/high/low/close BIGINT ×10000 · volume BIGINT`).
- **BIGINT** — 64-bit integer; holds the prices ×10000 and the volume.
- **VIEW `ohlcv_1h`** — a named view of prices in USD (`/10000.0`); a view, not a copy → zero storage duplication.
- **`price_view = raw_usd_view`** — the semantic name of the input price view (contract in `00_input_contract_eng.md`); one value per dataset.
- **`_meta`** — schema metadata: `schema_version`, source, `built_at`, row/symbol counters.
- **upsert per symbol** — `DELETE-then-INSERT`; uniqueness of `(symbol, ts)` guaranteed by the process + QC.
- **QC gate / QC-01…QC-11** — 11 load-validation predicates (a load that fails any is **not published**); the predicate set is owned by [`Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md`](Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md).
- **key numbers** — 8 841 820 rows · 503 symbols · database 166 MB · range 2016-01-04 → rolling.

## L4 · Snapshot → parquet OHLCV per ticker

- **atomic snapshot** — a consistent copy of the database at a single point in time; transformations never read the live store.
- **torn-read guard** — a retry if the source changed during the copy.
- **JSON manifest** — snapshot metadata: `rows / symbols / ts_min / ts_max / price_view`.
- **materialization (`COPY … TO parquet`)** — DuckDB SQL that writes a parquet per ticker.
- **`parquet/<TICKER>/ohlcv.parquet`** — the path convention; **503 files**, `zstd`.
- **clean columns / zero derived columns** — only `timestamp · open · high · low · close · volume`; features come only at L7.
- **parity** — after materialization, row and symbol counts must match the snapshot.
- **IN-07** — `price_view = raw_usd_view` written into the snapshot manifest.

## L5 · Split: warm-up / train / OOS (+ purge / embargo)

- **time split** — splitting the series into three disjoint windows; the foundation of OOS-result credibility.
- **WARM-UP / TRAIN / OOS** — three disjoint windows; only Train is touched repeatedly; OOS is frozen and tested once. Dates owned by [`Layers_Short_SOT/L5_time_split_eng.md`](Layers_Short_SOT/L5_time_split_eng.md).
- **indices, not files per window** — windows are sets of indices on one continuous series (the rolling lookback crosses boundaries).
- **rolling lookback** — the longest backward window of a feature: `max(W_ATR, W_VOL) = 20` candles.
- **purge** — a training row whose label window `[t0, t0+H]` crosses a window boundary is removed; operates on **setups**.
- **embargo** — a buffer after the Train→OOS boundary covering rolling-feature autocorrelation.
- **purged walk-forward CV** — the CV scheme inside Train; folds also separated by purge+embargo.
- **boundary assertion** — a CI test: no `[t0, t0+H]` window crosses a window boundary.

## L6 · Trend-line setup detector

- **detector** — we define the **output contract**, not the geometric algorithm; contract owned by [`Layers_Short_SOT/L6_setup_detector_eng.md`](Layers_Short_SOT/L6_setup_detector_eng.md), reference geometry in [detector_algorithm_eng.md](detector_algorithm_eng.md).
- **setup** — a single occurrence of a trend-line structure (formation → entry → outcome).
- **`direction` (±1)** — `+1` long (break up through resistance) · `−1` short (break down through support).
- **`L_trend(t)` / `L_opp(t)`** — the traded line / the opposing line (the stop loss sits on `L_opp`); both linear fits `a·t + b`.
- **`topo_candles` / touchpoint** — candle indices touching `L_trend`; touches strictly before `t0` (break ≠ touch).
- **`MIN_TOUCHES` / `TOUCH_TOL`** — the touch-validation count and tolerance (values in `00_parameters_eng.md`); dedup: one swing-touch.
- **`entry_candle` (t0)** — the first candle with `sign·(close[t] − L_trend(t)) > 0` after line validation (close-based break).
- **`R0` / `take_profit_level` / `time_barrier_candle`** — risk unit `abs(close[t0] − L_opp(t0))`; TP level; `t0 + H`. Definitions owned by L6 SOT.
- **ATR (Wilder, `W_ATR`)** — causal average true range; in L6 only the touch-tolerance scale and the DET-09 guard (a feature normalizer in L7).
- **DET-09** — a setup with `R0 ≤ 0`, `ATR(t0) ≤ 0` or missing `L_opp` is rejected **and counted** in the audit (never silently dropped).

## L7 · Features X + label Y (triple barrier)

- **transformer** — computes exactly 8 columns at `t0` (Feature Set v1); the 8 formulas + guards + the 7-X manifest + Output A/B schema are owned by [`Layers_Short_SOT/L7_features_x_label_y_eng.md`](Layers_Short_SOT/L7_features_x_label_y_eng.md).
- **Feature Set v1 (8 features)** — `distance_to_trend_line · distance_to_opposing_line · risk_if_entered_pct · bar_return_pct · body_to_range_ratio · volume_z_score · touch_count · closed_through_line`.
- **`FEATURE_MANIFEST` (7 X)** — the model's feature vector = the 8 columns minus `closed_through_line`; order frozen.
- **`closed_through_line` (audit)** — at `t0` definitionally `=1` (break invariant); an audit column, outside X.
- **`risk_if_entered_pct` ⚠** — simultaneously an X feature and a parameter of the Y geometry (it defines R0) → mandatory ablation (guardrail R7).
- **z-score** — a standardized value `(x − mean)/std` from the rolling window `W_VOL`; `std = 0 → 0`.
- **triple barrier / label Y (`TB_v1.1`)** — the trade outcome; iterating `t` from `t0+1` to `t0+H`, first-touch, close-based (TP → `Y=1`; SL on moving `L_opp(t)` → `Y=0`; time → `Y=0`).
- **`label_uniqueness_weight`** — sample weight (average uniqueness): overlapping `[t0, tb]` windows do not count as independent; formula `weight_i = mean_{t∈W_i}(1/c_t)` owned by L7 SOT.
- **Output B / Output A** — the training matrix (one row per setup, schema frozen) / an optional per-candle inspection table.
- **partition `{asset_id} × {direction}`** — a separate dataset/artifact for each asset × direction pair.

## L8 · Quality validation: stores + transforms (dashboard)

- **quality validation** — measures and reports, **fixes nothing**. Counters, parities, `summary.json` schema and aggregation owned by [`Layers_Short_SOT/L8_data_quality_eng.md`](Layers_Short_SOT/L8_data_quality_eng.md); thresholds in `00_parameters_eng.md`; rationale + dashboard layout in [quality_gate_spec_eng.md](quality_gate_spec_eng.md).
- **parities** — agreement of counts across stores: zip → DuckDB · DuckDB → parquet · parquet → Output B.
- **gaps** — in-session = 0 (hard fail) · overnight/weekend = counted (normal) · filled gaps = 0 (we fill nothing).
- **zero-values** — `volume = 0` bars · `high == low` (zero-range) · prices ≤ 0 (must be 0).
- **alarms (OK / WARN / FAIL)** — each counter has a threshold; any FAIL = gate closed → L9 blocked.
- **`reports/quality/summary.json` / `dashboard.html`** — the single truth (counters + statuses + input hash) and its self-contained render.

## L9 · Optuna → XGBoost → strategy .py (base64)

- **Optuna / TPE / MedianPruner** — the hyperparameter tuner (TPE sampler, MedianPruner); start condition = a non-FAIL L8 dashboard.
- **`N_TRIALS` / AUC-PR objective / purged walk-forward CV** — the trial budget, the CV objective, and the fold scheme (Train only); value in `00_parameters_eng.md`.
- **OOS guard** — in the tuning/training phase an attempt to read OOS = exception.
- **XGBoost `binary:logistic` / meta-labeling** — the model returns `p(TP)` and **filters** the detector's setup signal (it does not look for trades).
- **champion** — retrain on the full Train with the best trial's parameters; one model per `{asset × direction}`; deterministic seed.
- **`strategy_<TICKER>.py`** — a self-contained artifact (target ×503), imported standalone; sections `MODEL_B64`, `FEATURE_MANIFEST`, `LABEL_CONTRACT`, `THRESHOLD_ENTRY`, `selfcheck()` owned by [`Layers_Short_SOT/L9_optuna_xgboost_eng.md`](Layers_Short_SOT/L9_optuna_xgboost_eng.md).
- **deterministic build** — the same run → the same file hash.

## L10 · OOS test: 503 assets × metrics

- **OOS test** — one run over the OOS window; the entry rule and TB exits are owned by [`Layers_Short_SOT/L10_oos_test_eng.md`](Layers_Short_SOT/L10_oos_test_eng.md).
- **hash registry** — the hash of each artifact recorded before the test; from that moment the files are immutable.
- **results matrix `503 × metrics`** — aggregation per asset, canonical order **PF · Sharpe · MDD · TIM · WR** (+ trades).
  - **PF** — gross profits / gross losses · **Sharpe** — informational, caution at low TIM · **MDD %** — max drawdown · **TIM %** — time in market · **WR %** — win-rate · **trades** — the denominator of significance.
- **distribution report** — distributions across the universe, top/bottom assets, the share with PF > 1; we look for a **distribution**, not a single star.
- **one-shot** — the OOS result never goes back into tuning.

---

## Naming forms & feature explanation

The canonical naming forms (DuckDB, `VIEW ohlcv_1h`, the `PF · Sharpe · MDD · TIM · WR` order, `QC-01…QC-11`,
`warm-up`, `raw_usd_view`, the `L1–L10` reservation, the global numbers) are owned by
[`Layers_Short_SOT/00_conventions_eng.md`](Layers_Short_SOT/00_conventions_eng.md). Use them verbatim.

What the features *are* and where they come from is explained separately in
[feature_explanation_plan_b_eng.md](../../B_Features/feature_explanation_plan_b_eng.md): an OHLCV → feature
DAG with its **own feature-stage scheme F0–F5** (never `L#`) and ids `f{stage}_…`. It is a helper for
understanding features — **not** part of the Pipeline-A SOT and **not** a build pipeline.

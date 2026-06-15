# GLOSSARY — S&P 500 ML pipeline glossary (English)

Glossary of every concept needed to understand the data-flow rules that the 3D
visualization (`viz/main_data_flow.html`) explains. This is the fully-English version of the project
glossary: headwords and layer titles are given exactly as they appear in the visualization,
with English explanations. **Order = layer by layer (L1 → L10)** — the way data flows from
bottom to top in the `1 Overview` view; concepts that apply to every layer are gathered in
the *Cross-cutting concepts* section.

**viz ↔ documents mapping:** the **L1–L10** numbering is consistent between the visualization and
the layer summaries `L1…L10_*_eng.md`; the setup detector is its own level **L6**. **Technical
contract (inlined in this package):** [build_contract_eng.md](build_contract_eng.md) (input/detector/
features/label/splits/outputs/artifact/params/QC/DoD); the reference detector algorithm is
[detector_algorithm_eng.md](detector_algorithm_eng.md); the L8 gate is
[quality_gate_spec_eng.md](quality_gate_spec_eng.md); parameters are in [`../config/params.json`](../config/params.json).
The upstream `docs/SPEC.md`, `FLOW/`, and `docs/PIPELINE_REVIEW_CONFIGURABLES.md` are provenance only.

**Notation:** `t` = candle index (integer position after ascending sort by time);
`t0` = entry candle (`entry_candle`); `sign` = `direction`; `c/o/h/l/v` = close/open/high/low/volume of candle `t`.

---

## Cross-cutting concepts (view `0 Anti-leakage`)

Apply to every layer; the visualization shows them in the cross-cutting `0 Anti-leakage` view.

- **ML pipeline** — the whole flow from raw market data to the strategy file and the OOS test; 10 levels L1–L10 in the visualization.
- **S&P 500 universe** — the set of **503 tickers** of the S&P 500 index; the list is pinned in `config/universe.txt`.
- **Asset** — any instrument with OHLCV data; the pipeline is independent of price scale and timeframe (`build_contract_eng.md` §Scope).
- **Candle** — a single **OHLCV** bar (`open, high, low, close, volume`) in a given timeframe.
- **OHLCV** — the five candle fields: open, high, low, close, volume.
- **TF (timeframe)** — candle resolution; default `1h` (`build_contract_eng.md` §Parameters).
- **t / t0** — `t`: candle index (integer after sorting); `t0` = `entry_candle`, the position-opening candle. All line functions, `H` and the purge operate on the index, not on the timestamp.
- **Causality / zero look-ahead** — the overriding rule: for candle `t` we use only data from candles **≤ t**. No feature, line or decision depends on the future (the only exception: the explicit label window counted forward from `t0`). Verified by a causality test in CI.
- **Determinism** — the same input state → the same result; guaranteed by **seeds**, **artifact hashes** and **manifests** at every stage.
- **One-shot** — we test the OOS window **once**, after freezing the artifacts; the OOS result never goes back into tuning.
- **Gate** — an automatic pass-on condition (QC on the L3 load, green L8 dashboard before training).
- **Parameters** — the only place for configuration = `config/params.json` (`build_contract_eng.md` §Parameters); zero thresholds hardcoded in the code. The most important: `TF`, `H=24`, `MIN_TOUCHES=2`, `W_ATR=14`, `W_VOL=20`, `ATR_VARIANT=wilder`, `PRICE_VIEW=raw_usd_view`, `THRESHOLD_ENTRY=0.60`, `PURGE_CANDLES=H`, `EMBARGO_SESSIONS=5`, `N_TRIALS=200`, `CV_SCHEME=purged walk-forward`, `EPS=1e-9`.

---

## L1 · Source: Alpaca SIP · S&P 500 (503)

The only source of market data: hourly OHLCV candles for the whole universe.

- **Alpaca Market Data API** — the source of candles; authorization with an API key only (headless, no OAuth).
- **feed = sip** (consolidated tape) — one authoritative quote source; no mixing of feeds.
- **RTH session** — regular trading hours **09:00–16:00 ET**; gives ~7 1h candles per session day.
- **cron :05** — incremental update every hour at minute `:05`.
- **session guard** — outside ET market hours (Mon–Fri) the cron does nothing (no-op).
- **upsert** — a top-up with a ~5-day lookback overwrites the tail of the series; re-running with the same window gives the same state.
- **idempotency** — a property of the fetch: repeating it does not change the state.
- **raw prices** — they arrive without split/dividend adjustments; adjustment = a deliberate decision of later layers (open risk **R1** — corporate actions).
- **volume required** — for this universe, missing volume = hard fail QC (`build_contract_eng.md` §Input).

## L2 · LEAN ZIP store (510 zip · prices ×10000)

A durable, compact archival store in LEAN format — the source of truth for rebuilding the database.

- **LEAN** — the archive format (QuantConnect): one CSV file per ticker inside a ZIP.
- **1 zip = 1 ticker** — the entire ticker history in one file (`<ticker>.zip`).
- **headerless CSV** — row: `YYYYMMDD HH:MM,open,high,low,close,volume`.
- **prices ×10000** (deci-cents) — prices stored as integers (e.g. `$185.12 → 1851200`); zero floating-point errors in the archive.
- **naive ET timestamp** — local exchange time (`America/New_York`), without a timezone.
- **510 zip** — 503 universe tickers **+ a few non-constituents**; 139 MB in total.
- **source of truth / rebuild** — the whole L3 database can be rebuilt from the ZIPs.
- **append/replace per ticker** — never a partial edit inside the CSV.
- **ET-naive → UTC tz-aware conversion** — done only by the F1 reader at the read boundary (`build_contract_eng.md` §Input); in the archive the time stays naive.

## L3 · DuckDB: raw + VIEW ohlcv_1h (USD) · QC-01…QC-11

The canonical analytical database: raw integers in the table, USD in the view, quality gated on every load.

- **DuckDB** — the analytical database (file `*.duckdb`) into which we load the ZIPs.
- **`raw_ohlcv_1h` table** — verbatim data: `symbol VARCHAR · ts TIMESTAMP · open/high/low/close BIGINT ×10000 · volume BIGINT`.
- **BIGINT** — 64-bit integer; holds the prices ×10000 and the volume.
- **VIEW `ohlcv_1h`** — a named view of prices in USD (`open/10000.0, …`); a view, not a copy → **zero storage duplication**.
- **`price_view = raw_usd_view`** — the semantic name of the input price view from the contract (`build_contract_eng.md` §Input/§Parameters); one value per dataset (manifest), guarantees a repeatable result.
- **`_meta`** — schema metadata: `schema_version`, source, `built_at`, row/symbol counters.
- **upsert per symbol** — `DELETE-then-INSERT`; uniqueness of `(symbol, ts)` guaranteed by the process + QC.
- **QC gate** — an automatic load-validation rule; a load that does not pass QC is **not published**.
- **QC-01…QC-11** — 11 quality gates (padlock icons in the visualization): QC-01 `high ≥ low` · QC-02 `high ≥ max(o,c) · low ≤ min(o,c)` · QC-03 no duplicate `(symbol, ts)` · QC-04 zero NULL in o/h/l/c/v · QC-05 prices > 0 · QC-06 volume ≥ 0 · QC-07 universe 503/503 · QC-08 candles/day ∈ [5,9] · QC-09 ts within session 09:00–16:00 ET · QC-10 ts strictly increasing per symbol · QC-11 date range and counters match `_meta`.
- **key numbers** — 8 841 820 rows · 503 symbols · database 166 MB · range 2016-01-04 → rolling.

## L4 · Snapshot → parquet OHLCV per ticker

Read isolation: an atomic database snapshot materialized as clean OHLCV per ticker (zero features).

- **atomic snapshot** — a consistent copy of the database at a single point in time; transformations never read the live store.
- **torn-read guard** — a retry if the source changed during the copy (protection against an inconsistent read).
- **JSON manifest** — snapshot metadata: `rows / symbols / ts_min / ts_max / price_view`.
- **materialization (`COPY … TO parquet`)** — DuckDB SQL that writes a parquet per ticker.
- **`parquet/<TICKER>/ohlcv.parquet`** — the path convention; **503 files**, `zstd` compression.
- **clean columns / zero derived columns** — only contract §2: `timestamp · open · high · low · close · volume`; features are computed only by the transformer (L7).
- **parity** — after materialization we check that the row and symbol counts match the snapshot.
- **IN-07** — `price_view = raw_usd_view` written into the snapshot manifest (input repeatability).

## L5 · Split: warm-up / train / OOS (+ purge / embargo)

Time hygiene: three disjoint windows per asset with hard buffer zones at the boundaries.

- **time split** — splitting the series into three disjoint windows; the foundation of OOS-result credibility.
- **WARM-UP** (`2016-01-04 → 2016-10-14`) — roll-in of the rolling windows; **no training and no detection**.
- **TRAIN** (`2016-10-17 → 2023-12-29`) — the only window touched repeatedly: detection, features, Optuna (CV), training.
- **OOS** (`2024-01-02 → 2026-05-29`) — **frozen**: one test run; zero tuning after looking at the results.
- **indices, not files per window** — windows are sets of indices on one continuous series (the rolling lookback crosses boundaries, so cutting files would be wrong).
- **rolling lookback** — the longest backward window of a feature: `max(W_ATR=14, W_VOL=20)` = **20 candles**.
- **purge (`= H = 24 candles`)** — a training row whose label window `[t0, t0+H]` crosses a window boundary is **removed** (the label must not "reach" into OOS); the purge operates on **setups**, not on candles.
- **embargo (`≈ 5 sessions`, ~35 candles)** — a buffer after the Train→OOS boundary; covers the autocorrelation of the rolling features (≥ 20 candles of lookback).
- **purged walk-forward CV** — the cross-validation scheme inside Train; the folds are also separated by purge+embargo.
- **boundary assertion** — an automatic test: no `[t0, t0+H]` window crosses a window boundary (DoD F4).

## L6 · Trend-line setup detector

The bridge between raw candles and feature rows: a causal detector returns geometric setup objects (contract §3).

- **detector** (contract §3) — we define the **output contract**, not the geometric algorithm.
- **setup** — a single occurrence of a trend-line structure (formation → entry → outcome).
- **`direction` (±1)** — `+1` long (break upward through resistance) · `−1` short (break downward through support).
- **`L_trend(t)`** (traded line) — the traded line = linear fit `a_t·t + b_t` through the touchpoints (resistance for long, support for short).
- **`L_opp(t)`** (opposing line) — the opposing line, on which the stop loss sits = linear fit `a_o·t + b_o`.
- **`topo_candles` / touchpoint** — the set of candle indices touching `L_trend`; touches **strictly before `t0`** (break ≠ touch).
- **`MIN_TOUCHES` (2)** — the minimum number of touches that validate the line.
- **`TOUCH_TOL`** — line-touch tolerance = `0.25 ×ATR` (see `detector_algorithm_eng.md` / `config/params.json`); dedup: one swing-touch.
- **`entry_candle` (t0)** — the first candle with `sign·(close[t] − L_trend(t)) > 0` after line validation (close-based break).
- **`R0`** (risk unit) — `abs(close[t0] − L_opp(t0))`; one (geometric) unit of risk.
- **`take_profit_level`** — `close[t0] + direction · R0` (fixed level).
- **`time_barrier_candle`** — `t0 + H` (`H=24` candles).
- **ATR (Wilder, `W_ATR=14`)** — average true range computed causally from a window ending at `t` inclusive; appears **only as a feature normalizer** (L7).
- **DET-09** — invariant: a setup with `R0 ≤ 0`, `ATR(t0) ≤ 0` or a missing `L_opp` is **rejected and counted in the audit** (it does not vanish silently).

## L7 · Features X + label Y (triple barrier)

Transformation of setup objects into a training matrix: row = setup, features computed at `t0`, target = outcome per triple barrier.

- **transformer** — computes exactly 8 columns at `t0` (Feature Set v1).
- **Feature Set v1 (8 features)** — `distance_to_trend_line` (`sign·(c − L_trend)/ATR`) · `distance_to_opposing_line` (`sign·(c − L_opp)/ATR`, headroom to SL) · `risk_if_entered_pct` (`abs(c − L_opp)/c · 100`) · `bar_return_pct` (`(c − c[t−1])/c[t−1] · 100`) · `body_to_range_ratio` (`abs(c − o)/max(ε, h − l)`) · `volume_z_score` (`(v − mean_20)/std_20`, `std=0 → 0`) · `touch_count` (`count(topo_candles ≤ t)`) · `closed_through_line` (`1 if sign·(c − L_trend) > 0`).
- **`FEATURE_MANIFEST` (7 X)** — the model's feature vector = the transformer's 8 columns **minus** `closed_through_line`; order frozen.
- **`closed_through_line` (audit)** — at `t0` definitionally `=1` (break invariant); an audit column, **outside X**.
- **`risk_if_entered_pct` ⚠** — simultaneously an X feature and a parameter of the Y geometry (it defines R0) → mandatory ablation (guardrail R7).
- **`EPS = 1e-9`** — protection against division by zero in `body_to_range_ratio`.
- **z-score** — a standardized value `(x − mean)/std` from the rolling window `W_VOL=20`.
- **triple barrier / label Y (`TB_v1.1`)** — the trade outcome; iterating `t` from `t0+1` to `t0+H`, first-touch, close-based.
- **`Y_outcome`** — `1` (TP) / `0` (SL or time).
- **TP → Y=1** — the first `t` with `sign·close[t] ≥ sign·(close[t0] + direction·R0)`.
- **SL → Y=0** — the first `t` with `sign·close[t] < sign·L_opp(t)`; **`L_opp(t)` moving** (the line value at `t`, decision v1.2).
- **time → Y=0** — no resolution by `t0+H`.
- **geometric barriers** — TP/SL from `R0` (from `L_opp`), time in candles; ATR is only a normalizer → no ATR↔label coupling.
- **`label_uniqueness_weight`** — sample weight (average uniqueness): overlapping `[t0, tb]` windows do not count as independent; `weight_i = mean_{t∈W_i}(1/c_t)`, `c_t` = the number of windows covering candle `t`.
- **Output B** (training matrix) — the actual ML deliverable: one row per setup (`asset_id · direction · setup_id · entry_timestamp · 7 X · closed_through_line audit · Y_outcome · label_uniqueness_weight`); schema **frozen**.
- **Output A** — an optional per-candle table (inspection); columns + `Y_entry`.
- **partition `{asset_id} × {direction}`** — a separate dataset/artifact for each asset × direction pair.

## L8 · Quality validation: stores + transforms (dashboard)

A quality gate before training: one dashboard summarizes the quality of the whole flow (L2–L7). **FAIL blocks L9.**

- **quality validation** — measures and reports, **fixes nothing** (fixes = the source layers).
- **parities** — agreement of counts between stores: zip → DuckDB (8 841 820 rows / 503 symbols) · DuckDB → parquet (503 files, parity per ticker) · parquet → Output B (setup count per `{asset × direction}`, audit R4).
- **gaps** — in-session = 0 (hard fail) · overnight/weekend = counted (normal for 1h) · **filled gaps = 0** (we fill nothing; the counter proves it).
- **zero-values** — `volume = 0` bars · `high == low` candles (zero-range) · prices ≤ 0 (must be 0, QC-05).
- **NaN/Inf** — 0 in Output B apart from documented cases (`build_contract_eng.md` §Outputs).
- **split integrity** — assertion: no `[t0, t0+24]` window crosses a boundary; embargo ≥ lookback.
- **alarms (OK / WARN / FAIL)** — each counter has a threshold; any FAIL = gate closed.
- **`reports/quality/summary.json`** — counters + statuses + input hash (one truth).
- **`reports/quality/dashboard.html`** — a self-contained dashboard generated from summary.json.

## L9 · Optuna → XGBoost → strategy .py (base64)

The heart of ML: tuning and training on Train, and a self-contained strategy file with the model in base64.

- **Optuna** — a hyperparameter-tuning library; start condition = green L8 dashboard.
- **TPE** — Tree-structured Parzen Estimator (Optuna's Bayesian sampler).
- **MedianPruner** — pruner: cuts a trial below the median of the historical ones (`n_warmup_steps=2`).
- **`N_TRIALS = 200`** — the trial budget.
- **AUC-PR objective** — area under the precision-recall curve; averaged over k=4 CV folds.
- **purged walk-forward CV** — the fold scheme **in Train only** (folds with purge+embargo).
- **OOS guard** — in the tuning/training phase an attempt to read OOS = exception (DoD F5).
- **XGBoost `binary:logistic`** — gradient-boosting model; returns `p(TP)`.
- **meta-labeling** — the model's role: it **filters** the trend-line setup signal (the primary signal comes from the detector), it does not look for trades.
- **champion** — retrain on the full Train with the best trial's parameters; one model per `{asset × direction}`; deterministic seed.
- **`strategy_<TICKER>.py`** — a self-contained artifact (target ×503), imported standalone without the training data.
- **`MODEL_B64`** — the XGBoost model serialized and **base64**-encoded (~180 kB), decoded at import.
- **`LABEL_CONTRACT`** — the label-semantics identifier: `TB_v1.1 · close-based · SL=L_opp(t) moving · R0 · H=24`.
- **`THRESHOLD_ENTRY` (0.60)** — the decision threshold: `p ≥ 0.60 → ENTRY, else FLAT`; tuned in Train, never on OOS.
- **`selfcheck()` / golden vectors** — manually verified pairs (input → expected `p`) checked at import; a divergence → hard error.
- **deterministic build** — the same run → the same file hash.

## L10 · OOS test: 503 assets × metrics

The final verdict: a one-time run of the frozen strategies on the untouched OOS window and a results matrix.

- **OOS test** — one run over the OOS window (`2024-01-02 → 2026-05-29`).
- **hash registry** — the hash of each artifact recorded **before** the test; from that moment the files are immutable.
- **entry rule** — the detector generates setups, the strategy computes the 7 X features at `t0`, `p = model(x)`, `p ≥ 0.60 → ENTRY`.
- **TB exits** — fixed TP from `R0` · SL = moving `L_opp(t)` · time barrier `H=24`.
- **results matrix `503 × metrics`** — aggregation per asset.
- **OOS metrics (canonical order: PF · Sharpe · MDD · TIM · WR):**
  - **PF (profit factor)** — gross profits / gross losses.
  - **Sharpe** — informational; treat with caution at low TIM.
  - **MDD %** — maximum drawdown.
  - **TIM %** — time in market (% of candles with an open position).
  - **WR %** — win-rate (% of winning trades).
  - **trades** — the number of trades (the denominator of significance).
- **distribution report** — distributions of the metrics across the universe, top/bottom assets, the share with PF > 1; we look for a **distribution**, not a single star.
- **one-shot** — the OOS result never goes back into tuning (the next iteration = a new cycle from Train with a later OOS).

---

## Canonical forms (one naming across the whole project)

| Concept | Canonical form | Avoid |
|---|---|---|
| Analytical store (cylinder badge) | `DuckDB` | "duck" |
| USD price view | `VIEW ohlcv_1h` (in prose: the `ohlcv_1h` view), with "(USD)" when needed | "VIEW USD", "USD view" |
| OOS metrics order | **PF · Sharpe · MDD · TIM · WR** (= `METRICS` array) | PF · MDD · TIM · Sharpe · WR |
| Quality gates | `QC-01…QC-11` (11 QC gates) | "QC-01…11", "11 padlocks" |
| Database snapshot | `atomic snapshot` | "snapshot atomic" |
| Roll-in phase (prose) | `warm-up` (code/filenames: `warmup`) | "warm up", "warmup" in prose |
| Layer numbering (Pipeline A) | **L1–L10** (Detector = L6, Features = L7, Validation = L8, Optuna = L9, OOS = L10) — a separate scheme from Pipeline B's `L0–L5` (see "Pipeline B" below) | L1–L9; mixing A's and B's `L#` |
| Presentation language | viz UI + `README.md` = English; source project's `FLOW/`, `ROADMAP.md`, `docs/SPEC.md`, register = Polish; this English glossary + the `ENG/` summaries = English (snapshot) | — |
| Numbers | 503 tickers (universe) · 510 zip (503 + extra) · 8 841 820 rows | discrepancies without explanation |

---

## Pipeline B — OHLCV → L5 feature engineering (separate from L1–L10)

Everything above (L1–L10) is **Pipeline A** — the S&P 500 trading-strategy pipeline. The
`viz/feature_dag.html` visualization documents a **different** pipeline, **Pipeline B**: general
feature engineering over raw OHLCV. It has its own layer scheme **L0–L5** — the `L#` numbers do
**not** correspond to Pipeline A's. **Native bar = 1h** (the `qc_raw_ohlcv_data_sp500_alpaca_transforms`
1h store), so the only resample is **1h → 1d** (5m/15m are finer than the native bar). Shared
vocabulary (candle, ATR, z-score, regime,
resample, momentum, volatility, rolling) keeps the same canonical forms as above
(note: Pipeline A's ATR uses **Wilder** smoothing as a feature normalizer; Pipeline B's `l4_atr` is a
plain rolling **mean of TR** — same term, intentionally different variant).

- **Layers (bottom → top):** `L0` Raw OHLCV (O H L C V) · `L1` Atomic transforms (point-wise on
  one candle / adjacent pair) · `L2` Rolling / temporal (lags, rolling windows of length n) ·
  `L3` MTF / regime (resample 1h → 1d, recompute L1/L2, context aggregates) ·
  `L4` Classical indicators (RSI / MACD / ATR / OBV — compressed functions of L1–L3) ·
  `L5` Research representations (stack → standardize → PCA / wavelets / autoencoder / sequences).
- **Feature families:** `price` · `returns` · `range` (range/vol) · `candle` (candle geometry) ·
  `volume` · `meta` (synthesis / regime / embedding).
- **Feature-id naming convention:** `l{layer}_{metric}[_{params}][_{timeframe}]` — the token after the
  layer is the metric/abbreviation (`r`=close-to-close return, `mom`=momentum, `vol`=volatility),
  optionally followed by params (`n`, `k`) and/or timeframe (`mtf` / `{tf}`). The **family**
  (price / returns / range / candle / volume / meta) is a separate classifying attribute carried on
  each node's `family:` field (shown by the legend colour), **not** an id segment.
  Examples: `l1_r_cc` (family=returns), `l1_tp` (price), `l2_mom_n` (returns), `l3_vol_regime` (meta).
- **Edges = lineage:** every node is a function of its inputs back to `L0`; "regime context"
  edges are drawn dashed.


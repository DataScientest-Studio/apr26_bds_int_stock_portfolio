# Layers Short SOT — Minimal Feature Namespace Pipeline

This is the source of truth for the implemented per-asset pipeline. The scope is
limited to `Plan/` and `Project/`.

## Layer Map

| Layer | Name | Contract |
|---|---|---|
| L1 | Alpaca OHLCV Download | Upstream provenance. Raw 1h OHLCV came from Alpaca Market Data API. |
| L2 | ZIP Archive / Seed Export | Upstream provenance. One archive per ticker was exported to `data/seed/<TICKER>_ohlcv_1h.parquet`. |
| L3 | DuckDB Build | `build_db.py` loads all seed parquets into `liora.duckdb`, table `bars_1h`. |
| L4 | Parquet 1h / 1d / 1w | The notebook reads DuckDB, writes clean 1h OHLCV, then deterministic 1d and 1w roll-ups. |
| L5 | Time Split | Warmup / Train / OOS split with purge and embargo. OOS stays unread until the verdict step. |
| L6 | Features + Triple Barrier Y | Candidate bars use 1h momentum for side, Features come from namespaces, Y is symmetric ATR Triple Barrier. |
| L7 | Optuna HPO + Kelly | Optuna tunes XGB on Train CV AUC-PR; Kelly is calibrated on Train out-of-fold log-growth. |
| L8 | XGB Strategy Artifact | XGB trains on full Train and is embedded as base64 in `strategy_<TICKER>.py`. |
| L9 | OOS Endproduct | OOS verdict, dashboard row, README, and final seven-file asset folder. |

## Feature Namespaces

The model input order is deterministic:

1. `01-99`: `features_1h`
2. `101-199`: `features_1d`
3. `201-299`: `features_1w`
4. `901-999`: `multi_tf`

Each registry uses a single `features` list with `id`, `name`, `implemented`,
`formula`, and `unit`. The active manifest is resolved from
`Project/Structure/config/feature_namespaces.json`.

The current feature families are returns, SMA/MA distances, volume z-score,
ATR percent, realized volatility, RSI, Bollinger Bands, MACD, and simple
multi-timeframe alignment/spread ratios. Daily and weekly features are computed
on completed roll-up bars and projected as-of to the 1h decision timestamp.
Multi-timeframe features are pure functions of already projected 1h/1d/1w
feature values.

## Candidate And Label Contract

Every eligible 1h bar can become a candidate. The candidate side is:

`direction = sign(log_return_5)`

`0`, missing, infinite, or insufficient-history values are skipped.

The label `Y_outcome` is `TripleBarrier.ATR.v1`:

- entry: `open[t0+1]`
- width: `ATR14[t0] * TB_ATR_MULTIPLIER`
- target: `entry + direction * width`
- stop: `entry - direction * width`
- horizon: `H=24`
- trigger clock: close-based
- condition fill: next open
- scheduled fill: close at the time barrier

## Operator Surface

```bash
cd Project/Structure
make build-db
make run-asset TICKER=AAPL
make loop "AAPL TSLA XOM"
make dashboard
make build   # regenerate Plan/*.html from *.tmpl + Markdown markers
make check   # fail-closed gate: drift / stray literals / lego<->SOT crossmatch
make on
```

## Seven-File Asset Contract

Each `Assets/<TICKER>/` folder contains:

1. `<T>__L4_to_L9.ipynb`
2. `<T>_ohlcv_1h.parquet`
3. `<T>_ohlcv_1d.parquet`
4. `<T>_ohlcv_1w.parquet`
5. `OPTUNAs_XGB_HPOs_best_params.json`
6. `strategy_<T>.py`
7. `<T>_README.md`

## Guard Map

Real fail-closed gates in the runtime (no others exist):

| Guard | Home | Verdict |
|---|---|---|
| G.1 | `pipeline.layer4_snapshot_to_parquet` source QC | corrupt source OHLCV ⇒ `RuntimeError`, never cleaned |
| G.2 | `pipeline.purge_train_setups` + `purged_wf_folds` | label window crossing OOS ⇒ `AssertionError`; CV folds purged+embargoed |
| G.3 | `pipeline.accept_strategy` + `run_asset.py` 7-file assert + artifact selfcheck | contract violation ⇒ `SystemExit` / assert |

## Derivation rule

The MODULES registry in `Plan/procedure_lego.html.tmpl` `[J1]` derives 1:1 from the
"Kontrakt replikacji" blocks below; on divergence the SOT wins. Rationale (the *why*)
lives only in the app's `[J1b]` PROMPTS, never here. The fail-closed crossmatch
(module ids + depends vs these blocks) runs in
`Project/Structure/config/data_state_numbers_gate.py` (`make check`).

---

## Kontrakt replikacji — L1 Alpaca OHLCV download (upstream provenance)

- **CEL:** document where the raw bars came from; nothing of L1 executes in this repo.
- **INPUT:** Alpaca Market Data API, 1h equity bars (fetched by the upstream SP500 source
  repo `qc-raw-ohlcv-data-sp500-alpaca`, not by this project).
- **TRANSFORM:** none here — provenance only.
- **OUTPUT:** raw 1h OHLCV per ticker held upstream (Alpaca-fed DuckDB).
- **INWARIANTY:** this repo never touches the network and holds no API secrets;
  no live download path exists anywhere in `Project/Structure/`.
- **KNOBS:** none (upstream concern).
- **TESTY AKCEPTACYJNE:** none — provenance block, not an executed layer.
- **DEPENDS:** upstream: — · downstream: L2 · scope: provenance (not executed).

## Kontrakt replikacji — L2 seed export (one parquet per ticker)

- **CEL:** freeze the pipeline input as committed per-ticker raw 1h OHLCV parquets.
- **INPUT:** upstream SP500 DuckDB (`ohlcv_1h` view) at `SP500_DUCKDB`
  (Makefile default `/opt/to_liora_school/qc-raw-ohlcv-data-sp500-alpaca/endproduct/ohlcv_1h_sp500_alpaca.duckdb`).
- **TRANSFORM:** `ENSURE_SEEDS_PY` (Makefile, run by `make loop`) exports only MISSING tickers:
  `select ts as timestamp, open, high, low, close, volume from ohlcv_1h where symbol=? order by ts`,
  tz-localize `America/New_York` → convert UTC, volume cast float64.
- **OUTPUT:** `data/seed/<TICKER>_ohlcv_1h.parquet` × <!--na:n_assets_seed-->20<!--/na--> seed
  tickers (committed; the universe grows by dropping in another seed).
- **INWARIANTY:** existing seeds are never overwritten; columns are exactly
  timestamp/open/high/low/close/volume with UTC timestamps; no derived columns.
- **KNOBS:** `SP500_DUCKDB` (Makefile variable).
- **TESTY AKCEPTACYJNE:** `make loop` with all seeds present prints "all requested seeds already
  present" and writes nothing; a missing ticker absent upstream ⇒ `SystemExit`.
- **DEPENDS:** upstream: L1 · downstream: L3 · scope: provenance + top-up (executed only by `make loop`).

## Kontrakt replikacji — L3 build_db.py → liora.duckdb

- **CEL:** one analytical input store for the whole run: every seed in a single DuckDB table.
- **INPUT:** all `data/seed/*_ohlcv_1h.parquet`.
- **TRANSFORM:** `build_db.py`: `DROP TABLE IF EXISTS bars_1h` → `CREATE TABLE bars_1h(ticker,
  timestamp TIMESTAMPTZ, open, high, low, close, volume DOUBLE)` → plain INSERT per seed with the
  ticker column added. No cleaning, no calendar, no QC here (G.1 asserts on read).
- **OUTPUT:** `liora.duckdb`, table `bars_1h` (<!--na:duckdb_rows_bars_1h-->364079<!--/na--> rows
  over <!--na:n_assets_seed-->20<!--/na--> tickers); regenerable, gitignored.
- **INWARIANTY:** zero value mutation — a verbatim load; drop+recreate means no partial state
  survives a rebuild.
- **KNOBS:** `seed_dir=data/seed` · `db=liora.duckdb` (module constants in `build_db.py`).
- **TESTY AKCEPTACYJNE:** `make build-db` prints per-ticker bar counts and the final
  "built … from N ticker(s)"; corrupt seed values surface later as a G.1 `RuntimeError`.
- **DEPENDS:** upstream: L2 · downstream: L4 · scope: per-universe (one DB, all tickers).

## Kontrakt replikacji — L4 snapshot → 1h/1d/1w parquets

- **CEL:** materialize the asset's clean raw-truth: one clean 1h parquet plus deterministic
  1d/1w roll-ups, all pure OHLCV.
- **INPUT:** `liora.duckdb` `bars_1h` (read-only connection), one ticker.
- **TRANSFORM:** `layer4_snapshot_to_parquet` (pipeline.py:181): ordered SELECT of the 6 OHLCV
  columns → G.1 source QC (fail-closed) → `atomic_write` parquet (pyarrow, zstd).
  `layer4_materialize_timeframes` (:261) + `aggregate_to_timeframe` (:224): 1d = ET
  (`America/New_York`) calendar-day groups, 1w = ISO-week groups (Monday anchor);
  O=first, H=max, L=min, C=last, V=sum; `close_ts`/`available_at` are derived in memory for L6
  projection and NOT persisted.
- **OUTPUT:** `Assets/<T>/<T>_ohlcv_1h.parquet` + `<T>_ohlcv_1d.parquet` + `<T>_ohlcv_1w.parquet`
  (deliverable files #2–#4; columns exactly timestamp/open/high/low/close/volume).
- **INWARIANTY:** roll-ups derive only from the same clean 1h frame — no external calendar, no
  holiday list, no completeness gate; corrupt source stops the run (G.1), repair never happens here.
- **KNOBS:** `SESSION_TIMEZONE=America/New_York` · `CONTEXT_TIMEFRAMES=(1d, 1w)` · compression=zstd.
- **TESTY AKCEPTACYJNE:** `make run-asset TICKER=<T>` leaves the 3 parquets in `Assets/<T>/`;
  re-running is deterministic (same bytes for the same DB).
- **DEPENDS:** upstream: L3 · downstream: L5, G.1 · scope: per-asset.

## Kontrakt replikacji — G.1 source QC on read (fail-closed)

- **CEL:** refuse to compute on corrupt source data — the only repair is fixing the source.
- **INPUT:** the L4 dataframe immediately after the DuckDB read (before any write).
- **TRANSFORM:** predicates (pipeline.py:193–214): unparseable timestamp(s) · duplicate
  timestamp(s) · non-monotonic order · non-finite or ≤0 OHLC · high<low ·
  high<max(open,close) · low>min(open,close) · non-finite or negative volume.
  Any hit ⇒ `RuntimeError("L4 source QC FAILED …")` listing every violated predicate.
- **OUTPUT:** a verdict only — pass returns the same dataframe untouched.
- **INWARIANTY:** read-only (never mutates a row); zero cleaning / imputation / row synthesis;
  fail-closed — the notebook run dies, no partial deliverable is published.
- **KNOBS:** none — predicates are fixed in code.
- **TESTY AKCEPTACYJNE:** corrupt one seed value (e.g. negative volume) → `make run-asset` raises
  `RuntimeError "L4 source QC FAILED"` before any parquet is written.
- **DEPENDS:** upstream: L4 · downstream: blocks L5+ · scope: per-asset guard (inline in L4's read).

## Kontrakt replikacji — L5 temporal split + purge/embargo

- **CEL:** leakage-safe partitions on one continuous candle index; OOS frozen until L9.
- **INPUT:** the clean 1h frame from L4; frozen split dates from `config/pipeline_parameters.json`.
- **TRANSFORM:** `layer5_split` (pipeline.py:274): boolean masks warmup/train/oos from the frozen
  dates (end dates inclusive via +1 day) + integer bounds
  (`train_start_idx`/`train_end_idx`/`oos_start_idx`/`oos_end_idx`).
  `purge_train_setups` (:290): keep a Train event only if `t0 + H + EMBARGO_BARS <= oos_start_idx`,
  then assert `t0 + H < oos_start_idx` for every kept event.
- **OUTPUT:** masks + bounds (in-memory views); the parquet stays one unsplit file.
- **INWARIANTY:** marks only — zero physical splitting; purge (=H=24) and embargo (=35) are both
  positive; embargo covers the label window with a buffer, while the binding leakage control is
  the asserted label-window purge (rolling feature windows reach up to W_SMA_SLOW=50 bars — the
  walk-forward direction plus the purge assert is what protects the split, not the embargo alone);
  the OOS boundary is read again only at L9.
- **KNOBS:** warmup 2016-01-04→2016-10-14 · train 2016-10-17→2023-12-29 ·
  oos 2024-01-02→2026-05-29 · `PURGE_CANDLES=H=24` · `EMBARGO_BARS=35`.
- **TESTY AKCEPTACYJNE:** `validate_parameters` rejects `PURGE_CANDLES != H` (pipeline.py:117);
  the purge assertion fires if any kept label window crosses the boundary.
- **DEPENDS:** upstream: L4 · downstream: L6, G.2 · scope: per-asset.

## Kontrakt replikacji — G.2 split leakage guard

- **CEL:** make the leakage controls executable, not aspirational.
- **INPUT:** Train events + bounds from L5; fold layout inputs at L7 time.
- **TRANSFORM:** three enforced mechanisms: (1) purge assertion
  `all(t0 + H < oos_start_idx)` in `purge_train_setups` (pipeline.py:293);
  (2) purged walk-forward CV `purged_wf_folds` (:623): k=4 contiguous validation segments over
  Train, a fold's training events must satisfy `t0 + H < val_lo − EMBARGO_BARS`, folds with
  <5 val or <10 train events are dropped; (3) Kelly calibration assert
  `max(val t0) < oos_start_idx` (:716) — calibration never reaches OOS.
- **OUTPUT:** a verdict only — violations raise (`AssertionError`), nothing is repaired.
- **INWARIANTY:** no validation fold ever precedes its training data (walk-forward direction);
  every check counts candle indices, never wall-clock; OOS index range is untouched by any fold.
- **KNOBS:** `H=24` · `EMBARGO_BARS=35` · `cv_folds=4` (from
  `config/xgboost_optuna_search_space.json:objective`) · min fold sizes 5 val / 10 train.
- **TESTY AKCEPTACYJNE:** shrinking the Train window so a label window crosses the boundary makes
  `purge_train_setups` raise; `calibrate_kelly` raises if any fold's validation reaches OOS.
- **DEPENDS:** upstream: L5 · downstream: gates L7 · scope: per-asset guard.

## Kontrakt replikacji — L6 candidates + features + Triple Barrier Y

- **CEL:** turn eligible Train bars into Output B: X at close[t0] + honest net-return label.
- **INPUT:** clean 1h frame, Train mask + bounds (L5), the active feature manifest
  (`resolve_feature_manifest`, pipeline.py:332), the feature context (`build_feature_context`, :459).
- **TRANSFORM:** candidates (`generate_candidate_events`, :491): every scanned bar with finite
  `log_return_5` and ATR width > EPS becomes a candidate; side `direction=sign(log_return_5)`,
  zero/NaN momentum ⇒ skip. Features: <!--na:n_features_total-->56<!--/na--> X =
  <!--na:n_features_1h-->17<!--/na--> `1h` + <!--na:n_features_1d-->17<!--/na--> `1d` +
  <!--na:n_features_1w-->17<!--/na--> `1w` (coarse frames from
  completed roll-up bars, projected as-of via `merge_asof` on `available_at <= decision_timestamp`
  = close[t0]) + <!--na:n_features_multi_tf-->5<!--/na--> `multi_tf` (pure functions of
  already-projected values); missing context ⇒ NaN
  (XGBoost native missing); a non-finite mandatory 1h feature EXCLUDES the row
  (`core_feature_eligibility`, :480) — never imputed. Label (`simulate_trade`, :513),
  `TripleBarrier.ATR.v1`: entry `open[t0+1]·(1+s·slip)`; TP/SL = entry ± `ATR14[t0]·TB_ATR_MULTIPLIER`;
  close-based triggers scanned in `[t_fill, t_sched)`; condition exit fills `open[t+1]·(1−s·slip)`;
  scheduled exit fills `close[t_sched]·(1−s·slip)` (TIME_BARRIER at `t0+H`, or OOS_END_FORCED_EXIT
  at the range end); per-unit net return includes commission on both sides.
  `Y_outcome = 1` iff net return > 0. Label-uniqueness weights = mean of 1/concurrency over the
  holding window (`_uniqueness_weights`, :552).
- **OUTPUT:** Output B (`layer6_output_b`, :569): id/timestamp columns +
  <!--na:n_features_total-->56<!--/na--> X + the audit lane
  (`target_level`, `stop_level`, `barrier_width_pct`, `local_market_exit_reason`,
  `local_per_unit_net_return`, `Y_outcome`, `label_uniqueness_weight`).
- **INWARIANTY:** X uses only data at or before close[t0]; the future is read only inside the
  label lane `[t0, t0+H]`; audit columns never enter `XGBoost.DMatrix` (X selection is
  `effective_feature_names` only); the label geometry is symmetric — no barrier multipliers per side.
- **KNOBS:** `H=24` · `TB_ATR_MULTIPLIER=1.0` · `W_ATR=14` (Wilder) ·
  `SIGNAL_MOMENTUM_FEATURE=log_return_5` · `SIGNAL_ZERO_POLICY=skip` · `BARRIER_MODE=close` ·
  `COMMISSION_BPS=1` · `SLIPPAGE_BPS=2` · `EPS=1e-9`.
- **TESTY AKCEPTACYJNE:** `make feature-search` prints the resolved
  <!--na:n_features_total-->56<!--/na-->-feature manifest
  (namespace order, ascending ids); `validate_parameters` guards every knob's domain.
- **DEPENDS:** upstream: L5 · downstream: L7 · scope: per-asset.

## Kontrakt replikacji — S.1 per-asset feature search (continuous research plane)

- **CEL:** a sensible optional-feature subset for EVERY healthy asset (1d/1w/multi_tf;
  the 1h namespace stays frozen), so a future UI user picking any asset for a portfolio
  finds it already sensibly configured — not a ticker-ranking product; selection is
  Train-only; the loop runs until the operator stops it.
- **INPUT:** universe provider: `make feature-search-loop` ⇒ `SEARCH_UNIVERSE=all` = every
  upstream symbol (symbol asc) filtered by eligibility (`min_train_bars` in the frozen Train
  window; too-thin tickers become `ineligible` with a recorded reason, judged once at insert);
  `make search-on` ⇒ explicit `SEARCH_TICKERS` list (legacy, apply-on-satisfied). Bars come
  seed-first-else-upstream via `seeds.py` (byte-identical transform, parity asserted on every
  seed write); the superset Output B (<!--na:n_features_total-->56<!--/na--> X) per ticker is
  built once per pass via `derive_output_b`; `search_control.json` carries the agent-tunable knobs.
- **TRANSFORM:** `feature_search_worker.py` runs ROUNDS forever over the non-parked,
  non-ineligible tickers. Per ticker: TRIAGE first (stage-1 grid only — 1h-only and
  all-<!--na:n_features_total-->56<!--/na--> baselines + 8 namespace-block combos; never
  applies) until `baseline_ref` exists, then DEEP passes ordered by gain rank
  (gain = best_cv − baseline_ref, tie ticker asc — compute ordering only, never selection):
  first pass greedy forward/backward, later passes pair-swap / restart-from-k-th-best /
  add-remove-2 with k from the ticker's OWN deep-pass count, plus agent-suggested subsets
  (validated fail-closed). Each candidate = a column slice of the shared superset, scored by
  mean purged-WF CV AUC-PR (fixed `fallback_params`, k=4, seed 42); evaluations are keyed in
  `search_state.db` (WAL, single writer) so a resume or later round never re-evaluates a
  subset. An erroring ticker is PARKED (status + error + alert) and the round continues.
- **OUTPUT:** CONVERGED(t) := deep passes ≥ `min_deep_rounds` AND (the last completed pass
  adopted nothing OR ended on a dead streak ≥ `no_improve_N`) — evaluated only after a
  COMPLETED pass, purely from db state. Converged tickers are applied in ONE round-end BATCH:
  export missing seeds (upstream → `data/seed/`, untracked until the user's batch commit) →
  ONE `build_db` rebuild (L3 drop+recreate, once per round) → sequential `run_asset.py`
  (each = the asset's SINGLE OOS read) → status `applied`. Best may equal a baseline — the
  explicit override in the gitignored `config/per_asset_feature_overrides.json` IS the
  product. Later Train-CV improvements only set `pending_better` — re-apply (a deliberate
  second OOS read) is manual: `make search-apply TICKER=…`.
- **INWARIANTY:** selection never reads OOS and an OOS result never reopens selection;
  overrides never touch ids 1–99 (three enforcement layers + `mandatory_core_feature_names`
  backstop); the next candidate is a pure function of (state db, control file, the ticker's
  own pass count); triage never applies; a parked/ineligible ticker never stops the loop;
  the loop has NO completion condition — it stops only via STOP.flag / HALT.flag /
  `make search-off`; a session running in one mode is never killed by launching the other
  (MODE marker guard); results stay framed as research (survivorship, corp-actions deferred).
- **KNOBS:** `search_control.json` (gitignored runtime, NOT in configurations.html):
  epsilon=0.0005 · no_improve_N=8 · min_gain=0.002 (satisfied policy) · round_budget_evals=150 ·
  min_deep_rounds=2 · min_train_bars=3000 (consumed once per new ticker) ·
  apply_policy (env-owned: converged for feature-search-loop, satisfied for search-on;
  the worker mirrors it for the agent to read and ignores file drift) ·
  priorities · paused_tickers · stage3_candidates · halt.
- **TESTY AKCEPTACYJNE:** `feature_search_worker.py --selfcheck` (provider determinism,
  eligibility, seed↔upstream parity, 4 convergence cases, batch success/failure paths);
  kill -9 mid-pass resumes without re-evaluating any stored subset key; an override
  containing a 1h id raises RuntimeError; `applied` survives later rounds with no second
  `run_asset` (pending_better only).
- **DEPENDS:** upstream: L6 · downstream: L7 · scope: offline research plane
  (`make feature-search-loop` / `make search-on`, tmux-supervised, runs until interrupted).

## Kontrakt replikacji — L7 Optuna HPO + Kelly calibration

- **CEL:** tune only the XGB hyperparameters on Train CV, then calibrate one per-asset Kelly λ on
  Train out-of-fold log-growth — OOS untouched.
- **INPUT:** Output B + bounds (Train), seed=42, the manifest, the search space
  `config/xgboost_optuna_search_space.json`.
- **TRANSFORM:** `layer7_optuna` (pipeline.py:647): Optuna `TPESampler(seed=42)` +
  `MedianPruner(n_warmup_steps=2)`, 200 trials, metric = tie-invariant AUC-PR
  (`average_precision`, :606, stable mergesort) averaged over `purged_wf_folds` k=4;
  single-class or fold-less data ⇒ deterministic `fallback_params`. Suggest order and bounds are
  registry-driven from the search-space JSON (7 params: max_depth, eta, subsample,
  colsample_bytree, min_child_weight, reg_lambda, n_estimators).
  `calibrate_kelly` (:689): `GridSampler` over λ grid 0.05–1.0 × 20 points; per fold a fold-model
  (best params) predicts out-of-fold, `run_engine` replays the validation candle range with
  per-trade `f = clip(λ·(2p−1), 0, KELLY_CAP)`; objective = Σ log(end_capital/E0); ties resolve to
  the smallest λ.
- **OUTPUT:** `OPTUNAs_XGB_HPOs_best_params.json` (deliverable file #5): best_params +
  `kelly_fraction` + cv_auc_pr + fold count + the feature manifest + lineage (written by the
  notebook L7 cell).
- **INWARIANTY:** optimization strictly inside Train; the label geometry (Triple Barrier) is
  never tuned; Kelly touches sizing only — the XGB study and model bytes are independent of λ;
  the same seed ⇒ an identical trial sequence.
- **KNOBS:** `N_TRIALS=200` · `cv_folds=4` · `pruner_warmup=2` · `OPTUNA_OBJECTIVE=auc_pr` ·
  `RANDOM_SEED=42` · `XGBOOST_N_JOBS=1` · `KELLY_CALIBRATION={low 0.05, high 1.0, grid_points 20}` ·
  `KELLY_CAP=1.0`.
- **TESTY AKCEPTACYJNE:** re-running the notebook reproduces best_params + cv_auc_pr exactly
  (pinned env, seeded TPE, nthread=1); the G.2 assert in `calibrate_kelly` holds.
- **DEPENDS:** upstream: L6, G.2 · downstream: L8 · scope: per-asset.

## Kontrakt replikacji — L8 frozen XGB strategy artifact

- **CEL:** one self-contained, reloadable strategy file per asset — model + contract + selfcheck.
- **INPUT:** Output B + best_params (+ kelly_fraction) from L7, the manifest, lineage, the
  Train window.
- **TRANSFORM:** `layer8_train` (pipeline.py:737): final fit on the FULL Train
  (uniqueness-weighted). `strategy_meta` (:745): `MODEL_B64` = base64 of `booster.save_raw()`,
  `MODEL_HASH` = sha256 of the raw bytes, the embedded manifest (names/ids/namespaces),
  `THRESHOLD_ENTRY`, `LABEL_CONTRACT=TripleBarrier.ATR.v1`, `EXECUTION_CONTRACT` (fills, costs,
  capital mode, kelly_cap + basis), golden vectors = first 3 X rows with their predictions.
  `asset_writers.write_strategy`: emits `strategy_<T>.py` with `_load()` (hash-checked model
  decode), `predict_proba()`, `selfcheck()` (golden vectors, atol 1e-6).
- **OUTPUT:** `strategy_<TICKER>.py` (deliverable file #6) — imports with no training-data access.
- **INWARIANTY:** the artifact is standalone (base64 model, no filesystem reads at import);
  `MODEL_HASH` binds the payload — a flipped byte fails `_load`; selfcheck divergence raises.
- **KNOBS:** `THRESHOLD_ENTRY=0.6` (embedded, from config) · golden vector count = 3.
- **TESTY AKCEPTACYJNE:** `python3 strategy_<T>.py` prints `selfcheck: True`;
  tampering with `MODEL_B64` breaks the hash assert.
- **DEPENDS:** upstream: L7 · downstream: L9, G.3 · scope: per-asset.

## Kontrakt replikacji — G.3 acceptance + deliverable contract gate

- **CEL:** gate what may be called a deliverable: explicit acceptance semantics + an exact
  7-file contract + a self-verifying artifact.
- **INPUT:** the Train `run_engine` summary (acceptance), the produced `Assets/<T>/` folder
  (contract), the artifact (selfcheck).
- **TRANSFORM:** `accept_strategy` (pipeline.py:779): with `MIN_TRAIN_ACCEPTANCE_TRADES=null` the
  mode is `correctness_check` — the run is accepted as a correctness result and `rankable`
  records whether Train PF is finite; a non-null minimum enables real rejection (below-min trades
  or non-rankable PF ⇒ rejected). `run_asset.py`: asserts the folder holds EXACTLY the 7 contract
  files (missing or extra ⇒ `SystemExit`). The artifact selfcheck re-predicts the golden vectors
  on import/run.
- **OUTPUT:** acceptance dict (recorded in the artifact as `ACCEPTANCE`) + the pass/fail of the
  7-file assert.
- **INWARIANTY:** `THRESHOLD_ENTRY` is a config constant used identically in Train acceptance and
  the OOS verdict — never tuned on OOS; the acceptance verdict is stamped INTO the artifact;
  no extra files may ride along in an asset folder.
- **KNOBS:** `MIN_TRAIN_ACCEPTANCE_TRADES=null` (correctness-check mode) ·
  `PF_ZERO_GROSS_LOSS_POLICY=not_rankable`.
- **TESTY AKCEPTACYJNE:** `make run-asset` ends with "OK <T>: 7 files"; adding any 8th file to
  `Assets/<T>/` makes the next run exit with "7-file contract violated".
- **DEPENDS:** upstream: L8 · downstream: gates L9 · scope: per-asset guard.

## Kontrakt replikacji — L9 one-shot OOS + 7-file endproduct

- **CEL:** the single OOS read: verdict, README, metrics row — then the folder is complete.
- **INPUT:** the frozen OOS mask + bounds (L5), the trained booster (L8), the feature context,
  `kelly_fraction` (L7).
- **TRANSFORM:** `generate_candidate_events` on `masks["oos"]` (the first and only OOS scan) →
  `score_setups` (pipeline.py:924; the same X assembler and the same eligibility gate as Train) →
  `run_engine` (:794) over `[oos_start_idx, oos_end_idx]`: one open position, candidates grouped
  per t0 sorted by p, threshold 0.6, exact-tie skip, per-trade Kelly sizing
  `f=clip(λ·(2p−1),0,1)`, equity marked to close per held bar, capital-depletion halt; summary =
  end capital, PF (None when gross loss is 0 — `not_rankable`), MDD, win rate, TIM, counters.
  `asset_writers.write_readme`: capital path + ROI/365 + the feature table + the Triple Barrier
  ledger (first 50 trades). `asset_writers.write_oos_metrics`: UPSERT of the 16 result columns
  into `oos_metrics.db` (side store OUTSIDE the 7 files).
- **OUTPUT:** `<TICKER>_README.md` (deliverable file #7) + the `oos_metrics` row; with the
  executed notebook (file #1) the 7-file contract is complete.
- **INWARIANTY:** OOS is scanned exactly once, at the end — no parameter, threshold or feature
  choice reads it; the engine is the same code path as Train acceptance; results are framed as a
  correctness/research result, not an edge claim (`MIN_OOS_TRADES_FOR_INTERPRETATION=null`,
  `CORP_ACTIONS_POLICY=deferred` ⇒ raw unadjusted prices,
  `UNIVERSE_MODE=current_constituents_research` ⇒ survivorship caveat).
- **KNOBS:** oos 2024-01-02→2026-05-29 · `INITIAL_CAPITAL_USD=1000` ·
  `CAPITAL_MODE=kelly_fractional_compounding` · `POSITION_POLICY=one_open_position_per_asset` ·
  `SIMULTANEOUS_SETUP_POLICY=highest_probability_then_skip_on_exact_tie`.
- **TESTY AKCEPTACYJNE:** the notebook's final cell verifies the 6 on-disk deliverables before
  `run_asset.py` adds the executed ipynb and asserts all 7; the README ledger equals the engine
  ledger (same run, same object).
- **DEPENDS:** upstream: L8, G.3 · downstream: D.1 · scope: per-asset (one-shot).

## Kontrakt replikacji — D.1 dashboard feed (derived)

- **CEL:** one read-only universe view of the recorded OOS verdicts — never a source of truth.
- **INPUT:** `oos_metrics.db` (the L9 side store).
- **TRANSFORM:** `build_dashboard.py` (stdlib, runs without the venv): SELECT * ordered by ticker
  → `Plan/data/dashboard.json` (`{"assets": [...]}`); absent/empty DB ⇒ `[]` (empty-safe).
- **OUTPUT:** `Plan/data/dashboard.json`, fetched by the static `Plan/dashboard.html`
  (sortable table; PF/return color-coded; empty state instructs `make run-asset` + `make dashboard`).
- **INWARIANTY:** derived + regenerable + gitignored (`Plan/data/`); the page renders read-only
  and never synthesizes a value that is not in the JSON.
- **KNOBS:** none.
- **TESTY AKCEPTACYJNE:** `make dashboard` prints "dashboard: N asset(s)"; with no DB the JSON is
  an empty list and the page shows its empty state.
- **DEPENDS:** upstream: L9 · downstream: — · scope: per-universe (derived view).

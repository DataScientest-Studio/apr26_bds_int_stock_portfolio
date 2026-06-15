# External Audit Report — `Plan/` as a buildable single source of truth

Audit date: 2026-06-15  
Audited object: `/opt/to_liora_school/liora-project-ml-engineering/Plan/`, excluding the generated `audit/` evidence folder  
Method: full read of Markdown and plaintext HTML, decoded `feature_dag.html` bundle, cross-file SOT checks, formula/number re-derivation, buildability dry-run, headless Chromium render check

Evidence generated:

- `audit/inventory.tsv`, `audit/sha256sums.txt`, `audit/line_counts.txt`
- `audit/decoded_feature_dag/`, `audit/feature_dag_assets.json`, `audit/feature_dag_template.html`
- `audit/scan_findings.json`, `audit/link_check.json`, `audit/feature_id_check.json`, `audit/external_refs.json`
- `audit/main_data_flow.png`, `audit/feature_dag.png`, `audit/*_console.txt`, `audit/*_console.json`

## Verdict

**FAIL.** `Plan/` is useful as an English explanatory snapshot, but it cannot be certified as a buildable single source of truth. The package contains direct SOT contradictions, mathematically wrong or incomplete formula statements, a numeric mismatch in the Pipeline-A visualization, non-English UI/code text, and several build-blocking dependencies on source projects, specs, registers, and configuration files that are not present in `Plan/`. The visualizations render, and many canonical names are aligned, but the acceptance criteria require a stricter outcome than "mostly explanatory and internally close."

## Per-Criterion Table

| Criterion | Result | Evidence |
|---|---:|---|
| AC-1 Naming conventions hold | **PASS** | `ENG/L1...L10` filenames match `L{n}_{slug}_eng.md`; Markdown links resolve; decoded Pipeline-B feature ids pass the grammar for all `l1_...l5_...` nodes (`audit/feature_id_check.json`). L0 raw ids `O/H/L/C/V` are raw OHLCV inputs, not feature ids. |
| AC-2 Canonical forms hold verbatim | **FAIL** | Most forms are correct, but `main_data_flow.html` uses non-verbatim variants such as "QC-01 to QC-11" at line 169 and slash metric forms such as `PF/Sharpe/MDD/TIM/WR` at line 251 instead of the canonical `PF · Sharpe · MDD · TIM · WR`. |
| AC-3 Every formula is well-defined and correct | **FAIL** | Pipeline A viz omits `direction` in TP formulas; Pipeline B has missing zero-denominator guards and an incorrect Bollinger/ATR lineage edge. |
| AC-4 Every number is consistent | **FAIL** | Canonical L3 row count is `8 841 820`, but `main_data_flow.html` snapshot panel emits `rows:8838306`; the same panel emits `ts_max:'2026-05-21 15:00'` while OOS is documented through `2026-05-29`. |
| AC-5 SOT 1:1 | **FAIL** | `README.md` says source projects remain the SOT; `main_data_flow.html` disagrees with `glossary_eng.md` and `L7` on TP formulas and with L3/L4 on snapshot counts. |
| AC-6 Two-pipeline integrity | **PASS** | Pipeline A `L1-L10` and Pipeline B `L0-L5` are explicitly separated in `README.md` and `glossary_eng.md`; the ATR Wilder-vs-mean divergence is labelled. |
| AC-7 Buildability | **FAIL** | Buildability depends on missing external artifacts and unspecified algorithms/parameters, including `config/universe.txt`, full `config/params.json`, `docs/SPEC.md`, detector details, QC/dashboard thresholds, and Pipeline-B parameter sets. |
| AC-8 English-only, links, rendering | **FAIL** | Markdown links resolve and both viz render, but `main_data_flow.html` contains visible Polish UI text `czas`, Polish code comments, and `feature_dag.html` causes a `favicon.ico` 404 in console. |

## Findings Register

### AUD-001 · critical · `README.md:27`, `README.md:60-63`

Issue: `README.md` negates the requested `Plan/`-as-SOT status.

Evidence:

- `README.md:27`: "This is a copy; the source projects remain the single source of truth."
- `README.md:60-63`: "The full Polish reference docs (`FLOW/L*.md`) and the live pipeline code stay in the source project..." and "refresh `main_data_flow.html` by re-copying it from the source project's `viz/`."

Why wrong: The audit brief requires `Plan/` to be the buildable SOT in isolation. A document inside `Plan/` states the opposite and points implementers to unavailable upstream material.

Precise repair: Replace line 27 with a statement such as "For this audit package, `Plan/` is the implementation source of truth." Either include the source facts needed from `FLOW/`, `docs/SPEC.md`, registers, and code-derived configs inside `Plan/`, or explicitly state that the package is explanatory and not certifiable as a buildable SOT.

### AUD-002 · critical · `ENG/glossary_eng.md:25,35,121`, `ENG/summary_rules_eng.md:28-31`, `ENG/L5_time_split_eng.md:45`, `ENG/L6_setup_detector_eng.md:4`, `ENG/L7_features_x_label_y_eng.md:13`

Issue: Pipeline A cannot be built from `Plan/` alone.

Evidence:

- `glossary_eng.md:25`: the 503-ticker universe is "pinned in `config/universe.txt`", but that file is not in `Plan/`.
- `glossary_eng.md:35`: configuration is in `config/params.json`, but only "the most important" parameters are listed.
- `glossary_eng.md:121`: `TOUCH_TOL` is "defined in F2"; F2 is not in `Plan/`.
- `summary_rules_eng.md:28-31`: summaries are instructed to reference spec/register files and remain 1:1 with external `FLOW`.
- `L5_time_split_eng.md:45`: split dates are "parameters, spec §5a".
- `L6_setup_detector_eng.md:4`: setup objects are "contract spec §3".
- `L7_features_x_label_y_eng.md:13`: `label_uniqueness_weight` formula is referenced to "spec §6" in the layer summary.

Why wrong: A competent team cannot reproduce the described behavior without the universe list, complete parameter set, detector semantics, and external spec/register facts. `glossary_eng.md` contains some values, but not enough to replace the missing files and algorithmic contracts.

Precise repair: Add a build contract appendix inside `Plan/` containing: the full universe list or deterministic membership source/date; complete `params.json`; detector algorithm and setup schema; QC/dashboard thresholds and schemas; Output A/B schemas; `strategy_<TICKER>.py` public API; and any register/spec facts currently referenced only externally.

### AUD-003 · major · `viz/main_data_flow.html:1716,2027,2041,2071,2085`

Issue: Pipeline A visualization states the TP barrier without the required `direction` factor.

Evidence:

- Canonical `glossary_eng.md:124`: "`take_profit_level` — `close[t0] + direction · R0`".
- Canonical `glossary_eng.md:142`: "TP -> Y=1 — the first `t` with `sign·close[t] >= sign·(close[t0] + direction·R0)`."
- Canonical `L7_features_x_label_y_eng.md:10`: "TP: close reaches `close[t0] + direction·R0` -> Y=1".
- Viz `main_data_flow.html:2027`: "TP=1: close reaches close[t0]+R0".
- Viz `main_data_flow.html:2071`: "TP -> Y=1: first close >= close[t0]+R0".
- Viz `main_data_flow.html:2041` and `2085`: "TP = close[t0] + 1·R0".

Why wrong: `close[t0] + R0` is correct only for long setups. For shorts (`direction = -1`) it places the TP above entry rather than below entry, reversing the intended profit barrier.

Precise repair: Replace every generic TP statement with `close[t0] + direction·R0`; replace first-touch tests with the sign-normalized condition from `glossary_eng.md`. If a diagram is intentionally long-only, label it "long example" and keep all generic tooltips/panels direction-aware.

### AUD-004 · major · `viz/main_data_flow.html:2065`

Issue: The Pipeline-A visualization emits a snapshot manifest with row count and maximum timestamp that contradict the canonical docs.

Evidence:

- Canonical `ENG/L3_duckdb_raw_view_qc_eng.md:8`: "row count: 8 841 820".
- Canonical `ENG/glossary_eng.md:80`: "8 841 820 rows · 503 symbols".
- Canonical `ENG/L5_time_split_eng.md:51`: "OOS window: `2024-01-02 -> 2026-05-29`, frozen."
- Viz `main_data_flow.html:2065`: `JSON.stringify({rows:8838306,symbols:503,ts_min:'2016-01-04 09:00',ts_max:'2026-05-21 15:00',price_view:'raw_usd_view'},null,2)`.

Why wrong: `8,838,306` differs from `8,841,820` by `3,514` rows. `ts_max = 2026-05-21 15:00` cannot support an OOS window documented through `2026-05-29`.

Precise repair: Change the mock snapshot manifest to the canonical row count and a timestamp range consistent with the documented OOS end, or remove exact mock manifest values and say "same as L3 manifest" if the current snapshot is not intended to be factual.

### AUD-005 · major · `audit/decoded_feature_dag/2d397cc2-d521-4e51-aff1-34c56cd9bf02.js:36-37,60-61,78,83-89`

Issue: Pipeline B formulas omit required zero-denominator guards and leave standard indicators under-specified.

Evidence:

- `l1_clv`: `(2C - H - L) / (H - L)`.
- `l1_wick_imb`: `(lw - uw) / (H - L), uw = H - max(O,C), lw = min(O,C) - L`.
- `l2_vol_ratio`: `rv_short / rv_long`; `l2_mom_ratio`: `mom_short / mom_long`.
- `l4_rsi`: `RS = avg_gain / avg_loss`.
- `l4_stoch`: `(C - min_n L) / (max_n H - min_n L)`.
- `l4_adx`: `smoothed |+DI - -DI| / (+DI + -DI)`.
- `l4_mfi`: `MR on TP·V flows`.
- `l4_vwap`: `Σ TP·V / Σ V`.

Why wrong: AC-3 requires guards wherever division can be zero. These denominators can be zero on flat candles/windows, zero volume windows, all-gain/all-loss RSI/MFI windows, or zero directional movement. ADX is also not the textbook definition as written: the usual DX includes a `100 *` scale factor and a defined smoothing step.

Precise repair: Add explicit guards to every zeroable denominator, for example `(H=L -> 0)` for CLV/wick imbalance, `(denominator=0 -> 0)` or a domain-specific neutral value for ratios/stochastic/VWAP, and textbook RSI/MFI zero-flow cases. Rewrite ADX as `DX = 100 * |+DI - -DI| / max(eps, +DI + -DI); ADX = Wilder_smooth(DX, n)` or the exact chosen variant.

### AUD-006 · major · `audit/decoded_feature_dag/2d397cc2-d521-4e51-aff1-34c56cd9bf02.js:153-160`

Issue: Pipeline B lineage edges for Bollinger z-score and ATR are mathematically misleading.

Evidence:

- Formula at line 80: `l4_boll_z` is `(C - SMA_n) / σ_n(C)`.
- Edge at line 159: `["l2_rv_n","l4_boll_z"], // σ_n from L2 realized vol`.
- Formula at line 82: `l4_atr` is `mean_n( TR ), TR = max(H-L, |H-C_{-1}|, |L-C_{-1}|)`.
- Edge at line 160: `["l2_rv_n","l4_atr"], // ATR conceptually tied to rolling vol`.

Why wrong: Bollinger bands use rolling standard deviation of close price, not realized variance of log returns. ATR is a rolling mean of true range from high/low/previous close, not a function of realized variance. These edges violate the visualization's own "lineage" contract.

Precise repair: Remove `l2_rv_n -> l4_boll_z` unless a new node explicitly computes `σ_n(C)` from close. Remove `l2_rv_n -> l4_atr`; keep `H`, `L`, and `C` lineage and optionally add a `TR` intermediate node.

### AUD-007 · minor · `viz/main_data_flow.html:962`, `viz/main_data_flow.html:294,421,534,652,1000,1089,2327`, `ENG/summary_rules_eng.md:1,8`

Issue: English-only is violated.

Evidence:

- Visible UI label at `main_data_flow.html:962`: `txt('czas', ...)`.
- Polish comments include "przy eksporcie", "jedna z 5 sylwetek", "podpis pikselowy", "sam obrys", "poziom", "etykieta celu", and "bez zmian".
- `summary_rules_eng.md` uses `streszczenie` in heading/prose.

Why wrong: AC-8 requires no non-English text anywhere, including visualization code comments and bundle payloads. `czas` is visible UI text.

Precise repair: Replace `czas` with `time`; translate all Polish comments and path/prose labels, or move Polish-only path names to a clearly quoted provenance appendix if they must remain as literal external paths.

### AUD-008 · minor · `viz/feature_dag.html` render console

Issue: `feature_dag.html` renders but produces a console/network error for `favicon.ico`.

Evidence:

- `audit/feature_dag_console.txt`: `log.error: Failed to load resource: the server responded with a status of 404 (File not found)`.
- The CDP JSON identifies the URL as `http://127.0.0.1:8765/favicon.ico`.

Why wrong: AC-8 requires both visualizations to render with no console errors. This one is not a JS runtime failure and the screenshot is nonblank, but it is still a console error.

Precise repair: Add `<link rel="icon" href="data:,">` to `feature_dag.html` as done in `main_data_flow.html`, or include a real favicon at the requested path.

### AUD-009 · minor · `README.md:46-48`

Issue: README open instructions point to a non-existent root-level `main_data_flow.html`.

Evidence:

- `README.md:46-47`: "serve over HTTP from this folder ... then open `main_data_flow.html`."
- `README.md:48`: "Deep-links: `main_data_flow.html#1` ...".
- Inventory shows the file is `viz/main_data_flow.html`.

Why wrong: Served from `Plan/`, `main_data_flow.html` at the root does not exist; the correct URL is `viz/main_data_flow.html`.

Precise repair: Change both lines to `viz/main_data_flow.html` and `viz/main_data_flow.html#1` etc., or instruct users to serve from the `viz/` subdirectory.

### AUD-010 · minor · `viz/main_data_flow.html:169,251`

Issue: Some canonical forms are not verbatim in the visualization.

Evidence:

- `main_data_flow.html:169`: "QC-01 to QC-11".
- `main_data_flow.html:251`: "PF/Sharpe/MDD/TIM/WR".
- Canonical `glossary_eng.md:213-214`: `PF · Sharpe · MDD · TIM · WR`; `QC-01…QC-11`.

Why wrong: The audit brief asks canonical forms to hold verbatim across artifacts, not only approximately.

Precise repair: Replace with `QC-01…QC-11` and `PF · Sharpe · MDD · TIM · WR`.

## Buildability Gap List

1. **Universe membership** — `config/universe.txt` is referenced but absent. Minimal addition: include the 503 tickers or a deterministic membership source, effective date, and normalization rules.
2. **Complete parameters** — `config/params.json` is referenced, but only selected values are listed. Minimal addition: include the full file or a complete table of every parameter, type, default, allowed range, and owner layer.
3. **Detector implementation** — `Plan/` defines a setup output contract but not enough of the geometric algorithm to reproduce the detector. Minimal addition: define swing/topology discovery, line fitting, touch tolerance, dedup, entry search, short/long symmetry, and rejection/audit outputs.
4. **External specs/registers** — `docs/SPEC.md`, `docs/PIPELINE_REVIEW_CONFIGURABLES.md`, `FLOW/L*.md`, `spec §N`, and `register C-xx` are repeatedly referenced. Minimal addition: inline every required fact or add an audited `references/` snapshot inside `Plan/`.
5. **QC/dashboard implementation** — QC-01...QC-11 predicates are mostly present, but dashboard WARN/FAIL thresholds and exact `summary.json` schema are incomplete. Minimal addition: define every counter, type, threshold, and gate aggregation rule.
6. **Artifact schemas** — Output B is described but not fully typed; Output A is optional and under-specified; strategy artifact API lacks exact `decide()` signature and golden vectors. Minimal addition: provide schemas, column order, dtypes, null policy, and selfcheck fixtures.
7. **Pipeline B parameter sets** — rolling windows `n`, lags `k`, timeframe instances, regime buckets, and standardization fit scope are not fixed. Minimal addition: provide exact parameter grids/defaults and training/inference scopes.
8. **Pipeline B L5 methods** — PCA, wavelets, autoencoder, LSTM/Transformer are named, not specified. Minimal addition: either mark them explicitly as non-buildable research placeholders or define architectures, training data, fit/transform APIs, and persistence formats.
9. **Formula guards** — zero-denominator behavior is incomplete in Pipeline B. Minimal addition: add explicit guards and neutral values for every zeroable denominator.
10. **SOT ownership** — `README.md` says upstream projects remain SOT. Minimal addition: rewrite provenance so `Plan/` is authoritative for the audit snapshot, and note upstream propagation only as maintenance metadata.

## Repair Plan

### Must

1. Make `Plan/` authoritative: remove the "source projects remain SOT" contradiction and inline all required external spec/register/config facts.
2. Fix Pipeline-A TP math in `viz/main_data_flow.html` to use `direction·R0` everywhere generic.
3. Fix `main_data_flow.html` snapshot manifest row/timestamp values or remove exact stale mock values.
4. Fix Pipeline-B formulas and zero guards in the decoded source, then repack `feature_dag.html`.
5. Fix Pipeline-B lineage for Bollinger and ATR.
6. Add build contracts for Pipeline A and Pipeline B: schemas, parameters, detector semantics, QC/dashboard thresholds, artifact APIs.

### Should

1. Translate all non-English text and comments.
2. Normalize canonical forms verbatim (`QC-01…QC-11`, `PF · Sharpe · MDD · TIM · WR`).
3. Correct README visualization URLs to include `viz/`.
4. Add a favicon data URL to `feature_dag.html`.

### Optional

1. Add an unbundled `viz/feature_dag.source/` or `viz/feature_dag.decoded/` source snapshot so future audits do not depend on manual bundle decoding.
2. Add a machine-readable SOT manifest listing every canonical number, formula, and artifact contract once, then generate summaries/viz text from it.

## Sign-Off Statement

I cannot sign the requested statement. The following conditions must be met before it can be made:

1. `Plan/` must stop deferring SOT authority to upstream source projects and must include all required implementation facts.
2. Pipeline-A TP formulas in `main_data_flow.html` must be direction-aware.
3. Pipeline-A row counts/timestamp ranges must be reconciled across glossary, summaries, and visualization.
4. Pipeline-B formulas must include correct textbook definitions and zero-denominator guards.
5. Pipeline-B lineage must match the actual mathematical dependencies.
6. English-only and console-error issues must be repaired.

Only after these repairs can the statement be considered: "From `Plan/` alone, a competent team can build Pipelines A and B as described, and every formula/number/claim is internally consistent and mathematically correct."

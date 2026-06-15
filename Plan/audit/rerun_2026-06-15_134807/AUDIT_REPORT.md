# External Audit Rerun Report — `Plan/` as a buildable SOT

Audit date: 2026-06-15  
Audited object: `/opt/to_liora_school/liora-project-ml-engineering/Plan/`, excluding `Plan/audit/`  
Rerun evidence directory: `audit/rerun_2026-06-15_134807/`

## Verdict

**FAIL, improved from the prior audit but not yet certifiable.** The repaired package closes many of
the original defects: `Plan/` now contains `config/universe.txt`, `config/params.json`, an inlined
Pipeline-A build contract, detector and quality-gate specs, corrected TP math, corrected snapshot
manifest rows, clean local Markdown links, a valid decoded Pipeline-B DAG, and renderable
visualizations. However, several remaining contradictions still block certification: one stale
Pipeline-A timestamp remains in the visualization, Pipeline-B ATR and zero-std guards disagree across
the canonical docs/spec/viz, the L8 `summary.json` schema is stated in two incompatible forms, and
the package still claims a single configuration site while important gate/detector values are not in
`config/params.json`.

## Evidence Generated

- `inventory.tsv`, `sha256sums.txt`, `line_counts.txt`
- `decoded_feature_dag/`, `feature_dag_assets.json`, `feature_dag_template.html`
- `feature_id_check.json`, `link_check.json`, `language_scan.json`, `regression_scan.json`,
  `sot_reference_scan.json`
- `main_data_flow_cdp.png`, `feature_dag_cdp.png`
- `main_data_flow_console.txt/json`, `feature_dag_console.txt/json`, `*_chromium_stderr.txt`

## Per-Criterion Table

| Criterion | Result | Evidence |
|---|---:|---|
| AC-1 Naming conventions hold | **PASS** | Markdown filenames match the expected scheme. Markdown local links resolve (`link_check.json`: `[]`). Decoded `feature_dag.html` has 55 nodes, 101 edges, no feature-id grammar failures and no bad edge endpoints (`feature_id_check.json`). |
| AC-2 Canonical forms hold verbatim | **FAIL** | Pipeline-B canonical ATR is still contradictory: glossary/viz define `l4_atr` as plain `mean_n(TR)`, while `pipelineB_spec_eng.md` defines the L4 ATR reference as Wilder. |
| AC-3 Every formula is well-defined and correct | **FAIL** | Pipeline-A TP math is now direction-aware, but Pipeline-B zero-std z-score behavior is inconsistent: the viz says `σ=0 -> 0`, while the build spec says `std=0 -> numerator / ε`. |
| AC-4 Every number is consistent | **FAIL** | Most stale row/timestamp values were fixed, but `viz/main_data_flow.html:2062` still reports `2016-01-04 09:00 -> 2026-05-22 15:00`, while the snapshot manifest and OOS docs use `2026-05-29`. |
| AC-5 SOT 1:1 | **FAIL** | `README.md` declares `Plan/` authoritative, but `ENG/summary_rules_eng.md` still says source `FLOW/L*.md` files are the "complete reference"; Pipeline-B ATR and L8 schema also disagree across docs. |
| AC-6 Two-pipeline integrity | **PASS** | Pipeline A `L1-L10` and Pipeline B `L0-L5` are consistently separated and the different layer schemes are repeatedly called out. |
| AC-7 Buildability | **FAIL** | Buildability is much closer, but the configuration/schema contradictions are build-impacting: L8 thresholds are claimed to live in `config/params.json` but are absent, and `summary.json` has two incompatible schemas. |
| AC-8 English-only, links, rendering | **FAIL** | Links resolve and both viz render with no runtime error or 404. Strict English-only still fails because Polish source filenames/path fragments remain in `ENG/readme_eng.md` and `summary_rules_eng.md`. |

## Findings Register

### AUD-R2-001 · major · `ENG/summary_rules_eng.md:6-8`, `README.md:35-40`

Issue: one document still assigns reference authority to external `FLOW/L*.md`, contradicting the
new `Plan/`-as-SOT claim.

Evidence:

- `README.md:35-40`: "`Plan/` is now the authoritative SOT for building this project" and upstream
  paths are "provenance / maintenance metadata only".
- `summary_rules_eng.md:6-8`: "the full files `FLOW/L*.md` ... are the complete reference for a
  layer".

Why wrong: The audit object must be usable in isolation. A rules document inside `Plan/` still tells
summary authors that unavailable Polish source files are the complete layer reference.

Precise repair: Rewrite `summary_rules_eng.md` so the complete reference is
`build_contract_eng.md` plus the in-Plan companion specs. Keep `FLOW/L*.md` only as optional
provenance, never as a reference source.

### AUD-R2-002 · major · `viz/main_data_flow.html:2062`, `viz/main_data_flow.html:2065`

Issue: Pipeline-A max timestamp is still inconsistent inside the visualization.

Evidence:

- `main_data_flow.html:2062`: DuckDB panel reports `2016-01-04 09:00 -> 2026-05-22 15:00`.
- `main_data_flow.html:2065`: snapshot manifest reports `ts_max:'2026-05-29 15:00'`.
- `ENG/L5_time_split_eng.md:9`, `ENG/L10_oos_test_eng.md:5`, and `ENG/glossary_eng.md:105` all use
  OOS through `2026-05-29`.

Why wrong: A dataset ending on 2026-05-22 cannot support an OOS window through 2026-05-29. The
snapshot manifest was fixed, but the DuckDB detail panel still carries the stale date.

Precise repair: Change the DuckDB detail panel date to `2026-05-29 15:00`, or remove exact max
timestamp text from that panel and point to the snapshot manifest.

### AUD-R2-003 · major · `ENG/glossary_eng.md:235-236`, `viz/feature_dag.html` decoded data, `ENG/pipelineB_spec_eng.md:210`

Issue: Pipeline-B ATR is defined as two different formulas.

Evidence:

- `glossary_eng.md:235-236`: "Pipeline B's `l4_atr` is a plain rolling mean of TR".
- Decoded `feature_dag.html` data line 82: `l4_atr_n` formula is `mean_n( TR )`.
- `pipelineB_spec_eng.md:210`: L4 ATR reference is `ATR_n = Wilder(TR, n)` and says it is
  deliberately the same Wilder variant as Pipeline A.

Why wrong: The audit brief explicitly treats Pipeline A ATR = Wilder and Pipeline B `l4_atr` =
plain rolling mean of TR as an intended divergence. The current build spec reverses that canonical
distinction.

Precise repair: Make `pipelineB_spec_eng.md` L4 ATR match `l4_atr_n = mean_n(TR)` if it is the same
node as the viz/glossary. If a Wilder ATR extension is desired, give it a distinct id and mark it as
a separate v2 feature, not canonical `l4_atr`.

### AUD-R2-004 · major · `ENG/pipelineB_spec_eng.md:154,161`, decoded `feature_dag.html` line 80

Issue: Pipeline-B zero-std z-score behavior is inconsistent.

Evidence:

- `pipelineB_spec_eng.md:154`: `l3_l2_volume_z...` uses `safe_div(..., volume_std_n)` with
  `std=0 -> /ε`.
- `pipelineB_spec_eng.md:161`: for z-scores, "When the std is 0 ... `safe_div` returns
  `numerator / ε`".
- Decoded `feature_dag.html` line 80: Bollinger z-score says `(σ_n=0 -> 0)`.
- The audit brief's formula checklist expects z-scores/Bollinger with `σ=0 -> 0` guard.

Why wrong: Both behaviors are finite, but they are not the same mathematical function. A flat-window
z-score returning a huge `numerator/ε` value is not the same as the neutral `0` guard used by the
viz and audit checklist.

Precise repair: Pick one canonical guard and apply it everywhere. For this audit, use `std=0 -> 0`
for z-scores/Bollinger, or explicitly update the glossary/viz/brief-derived examples and justify the
non-neutral ε-floor behavior.

### AUD-R2-005 · major · `ENG/quality_gate_spec_eng.md:104-167`, `ENG/detector_algorithm_eng.md:395-414`

Issue: `reports/quality/summary.json` has two incompatible schemas.

Evidence:

- `quality_gate_spec_eng.md:106`: `summary.json` schema is frozen.
- `quality_gate_spec_eng.md:110,159`: `schema_version` is `"1.0"` and `checks[]` has exactly one
  object per check id 1..11.
- `detector_algorithm_eng.md:399-414`: reproduces a `summary.json` with `"schema_version": "1"` and
  a `checks` array containing only a `DET-09` item.

Why wrong: A frozen schema cannot simultaneously require 11 gate checks with version `1.0` and a
single detector-local check with version `1`. Implementers would produce incompatible dashboard
inputs.

Precise repair: Keep one canonical `summary.json` schema in `quality_gate_spec_eng.md`. In
`detector_algorithm_eng.md`, describe only the detector's contribution to the canonical counters
(`setups_total`, `det09_rejected`) rather than showing a competing full schema.

### AUD-R2-006 · major · `ENG/quality_gate_spec_eng.md:256`, `config/params.json:1-20`, `ENG/build_contract_eng.md:200-202`, `ENG/detector_algorithm_eng.md:44-51`

Issue: `config/params.json` is declared as the single configuration site, but important fixed values
are not in it.

Evidence:

- `quality_gate_spec_eng.md:256`: "All thresholds live in `config/params.json`".
- `config/params.json` contains 18 keys; it does not contain L8 thresholds such as
  `volume_zero_warn_pct`, `volume_zero_fail_pct`, `zero_range_warn_pct`, `zero_range_fail_pct`, or
  `det09_rejected_warn_pct`.
- `build_contract_eng.md:200-202` says split dates are parameters, but no split-date keys are in
  `params.json`.
- `detector_algorithm_eng.md:44-51` fixes `k`, `COOLDOWN`, and `LOOKBACK`, but these are not in
  `params.json`.

Why wrong: The docs contain many of these values, so a human can infer them, but the "only
configuration site" claim is false. This weakens reproducibility and creates multiple places for
drift.

Precise repair: Either add all fixed thresholds/split dates/detector design parameters to
`config/params.json`, or narrow the claim: `params.json` contains the Pipeline-A core runtime
parameters, while reference design constants live in named spec sections.

### AUD-R2-007 · major · `README.md:24-27`, `ENG/pipelineB_spec_eng.md:198-200`

Issue: the audit scope is Pipeline B `L0-L5`, but the repaired package narrows certification to
Pipeline B `L0-L3`.

Evidence:

- `README.md:24-27`: Pipeline B `L4/L5` are "not part of the v1 certified implementation".
- `pipelineB_spec_eng.md:198-200`: all of Part 2 (`L4 + L5`) is "NOT built in v1".
- `AUDIT_BRIEF.md` defines Pipeline B as OHLCV -> `L5` feature engineering and AC-7 requires both
  pipelines to be buildable from `Plan/` alone.

Why wrong: It is acceptable to label future implementation scope, but the certification statement
requested by the audit is about the described `Plan/` package, which includes Pipeline B through L5.
The package cannot claim full Pipeline-B certification while excluding L4/L5 from the certified
implementation boundary.

Precise repair: Either certify Pipeline B `L0-L5` as a buildable spec, including L4/L5, or explicitly
change the audit target/sign-off statement to "Pipeline A end-to-end + Pipeline B L0-L3 certified;
Pipeline B L4/L5 reference design only."

### AUD-R2-008 · minor · `ENG/readme_eng.md:18-29`, `ENG/summary_rules_eng.md:6,45`

Issue: strict English-only still fails on Polish source path fragments and provenance prose.

Evidence:

- `ENG/readme_eng.md:20-29` contains source paths such as `FLOW/L1_zrodlo_alpaca.md`,
  `FLOW/L6_detektor_setupu.md`, `FLOW/L7_cechy_x_etykieta_y.md`, and
  `FLOW/L8_walidacja_jakosci_danych.md`.
- `summary_rules_eng.md:6` explicitly labels those source files as Polish.

Why wrong: The audit brief says "No non-English text anywhere", including docs and viz payloads. The
remaining Polish is literal provenance rather than UI text, so this is minor, but it still violates
the strict criterion.

Precise repair: Remove the provenance filename table from the certifiable `ENG/` docs, or move it to
an audit-excluded provenance appendix. If retained, use neutral source IDs instead of Polish path
fragments.

### AUD-R2-009 · minor · `ENG/glossary_eng.md:124`, `ENG/L7_features_x_label_y_eng.md:13`

Issue: some old external-style references remain even though the facts now exist in `Plan/`.

Evidence:

- `glossary_eng.md:124`: `TOUCH_TOL` is "defined in F2".
- `L7_features_x_label_y_eng.md:13`: `label_uniqueness_weight` formula is referenced to "spec §6".

Why wrong: The facts are now in `build_contract_eng.md` / `detector_algorithm_eng.md`, so these
references are stale and weaken the self-contained story.

Precise repair: Replace with in-Plan references: `TOUCH_TOL = 0.25` in
`detector_algorithm_eng.md` / `config/params.json`; `label_uniqueness_weight` formula in
`build_contract_eng.md` §7.3.

## Buildability Gap List

1. **Single configuration site is incomplete.** L8 thresholds, split dates, and detector reference
   parameters are fixed in prose but not in `config/params.json`, despite claims that all thresholds
   or all parameters live there.
2. **L8 output schema is ambiguous.** Implementers can choose either the full 11-check
   `summary.json` schema or the detector-local DET-09-only sample unless the competing schema is
   removed.
3. **Pipeline-B ATR cannot be implemented consistently.** `l4_atr` is both plain `mean_n(TR)` and
   Wilder ATR, depending on which document an engineer follows.
4. **Pipeline-B z-score zero guard cannot be implemented consistently.** The spec and viz define
   different outputs when rolling std is zero.
5. **Pipeline-B certification boundary is narrower than the audit object.** `L4/L5` are described
   but excluded from v1 certification; the audit object expects OHLCV -> L5.
6. **Residual external/provenance references need cleanup.** Remaining `FLOW/`, `spec §`, `F2`, and
   `register C-xx` references should either point to in-Plan sections or be fenced as non-build
   provenance.

## Repair Plan

### Must

1. Fix `viz/main_data_flow.html:2062` so the DuckDB panel date agrees with `2026-05-29 15:00`.
2. Resolve Pipeline-B ATR: make glossary, `feature_dag.html`, `pipelineB_spec_eng.md`, and
   `build_contract_eng.md` use one canonical `l4_atr` definition.
3. Resolve Pipeline-B zero-std guards: make z-score/Bollinger formulas agree everywhere.
4. Keep exactly one `reports/quality/summary.json` schema; remove or rewrite the detector-local
   competing sample.
5. Either add all L8 thresholds/split dates/detector constants to `config/params.json`, or revise the
   "single configuration site" claims.
6. Decide the certification scope for Pipeline B: full `L0-L5`, or explicitly amend the audit target
   to `L0-L3` certified + `L4/L5` reference only.

### Should

1. Reword `summary_rules_eng.md` so `FLOW/L*.md` is provenance only.
2. Replace stale `F2` / `spec §` / `register C-xx` references with in-Plan anchors or filenames.
3. Remove Polish source path fragments from certifiable English docs, or move them outside the
   audited deliverable.

### Optional

1. Precompile `feature_dag.html` instead of shipping in-browser Babel if the project wants a fully
   warning-free console, not merely error-free rendering.
2. Add a machine-readable canonical-values manifest and generate the repeated row/date/formula text
   from it to prevent future drift.

## Positive Checks That Now Pass

- `config/universe.txt` exists and contains 503 unique tickers.
- `config/params.json` exists and contains the core Pipeline-A runtime parameters including
  `TOUCH_TOL`.
- Pipeline-A TP statements in `main_data_flow.html` are direction-aware.
- The stale `rows:8838306` snapshot manifest value is fixed to `8841820`.
- Markdown local links resolve.
- Decoded Pipeline-B DAG ids and edges are internally valid.
- `feature_dag.html` no longer produces the prior favicon 404. Render logs show only React DevTools
  info and an in-browser Babel warning, not a runtime exception.

## Sign-Off Statement

I cannot sign the requested statement yet. The following conditions must be met first:

1. Pipeline-B ATR and zero-std guard semantics must be made internally consistent.
2. Pipeline-A date ranges must agree everywhere in docs and visualization panels.
3. L8 must have one canonical `summary.json` schema.
4. The configuration ownership model must be truthful and complete.
5. The package must either certify Pipeline B through `L5` or explicitly narrow the audit scope.
6. Remaining external/provenance and non-English path references must be cleaned up or excluded from
   the certifiable deliverable.

Only after those repairs can the statement be considered true: "From `Plan/` alone, a competent team
can build Pipelines A and B as described, and every formula/number/claim is internally consistent and
mathematically correct."

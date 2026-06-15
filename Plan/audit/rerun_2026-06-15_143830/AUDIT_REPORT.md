# External Audit Rerun Report — `Plan/` as a buildable SOT

Audit date: 2026-06-15  
Audited object: `/opt/to_liora_school/liora-project-ml-engineering/Plan/`, excluding `Plan/audit/`  
Rerun evidence directory: `audit/rerun_2026-06-15_143830/`

## Verdict

**FAIL, close but not certifiable.** The latest repair closes several previous blockers: the stale
`2026-05-22` date is gone, `config/params.json` is now valid and materially expanded, Markdown links
resolve, Polish-language scans are clean, the decoded Pipeline-B DAG has valid ids/edges, and both
visualizations render without runtime/404 errors. However, the current package still has
build-impacting SOT contradictions: Pipeline-B ATR is still called both `mean_n(TR)` and Wilder in
certifying docs, the Pipeline-B z-score guard note still says the additive epsilon floor is used,
`viz/main_data_flow.html` still shows a non-canonical `summary.json` object, and one quality-gate
section still frames Pipeline-B L4/L5/parity checks as `v2`/`NOT in v1`.

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
| AC-1 Naming conventions hold | **PASS** | Markdown files match the expected scheme; local Markdown links resolve (`link_check.json`: `[]`); decoded Pipeline-B DAG has 55 nodes, 101 edges, no bad ids and no bad edge endpoints (`feature_id_check.json`). |
| AC-2 Canonical forms hold verbatim | **FAIL** | Pipeline-B canonical `l4_atr` is still contradicted inside `pipelineB_spec_eng.md` and `quality_gate_spec_eng.md`: the docs say `mean_n(TR)` in one place and Wilder in another. |
| AC-3 Every formula is well-defined and correct | **FAIL** | Pipeline-B z-score tables say `σ=0 -> 0`, but the immediately following guard note still says the additive epsilon floor is used instead of explicit zero. |
| AC-4 Every number is consistent | **PASS** | The stale `2026-05-22` timestamp is gone; current number/date scans did not find `8838306`, `2026-05-21`, or `2026-05-22`. |
| AC-5 SOT 1:1 | **FAIL** | `quality_gate_spec_eng.md` defines one frozen `summary.json` schema, but `main_data_flow.html` still displays a different mock `summary.json` structure; Pipeline-B ATR/scope text also disagrees across specs. |
| AC-6 Two-pipeline integrity | **PASS** | Pipeline A `L1-L10` and Pipeline B `L0-L5` remain clearly separated. |
| AC-7 Buildability | **FAIL** | The expanded config is a strong improvement, but implementers still receive contradictory ATR, z-score, `summary.json`, and Pipeline-B certification-scope instructions. |
| AC-8 English-only, links, rendering | **PASS** | Polish scan returned 0 hits; links resolve; both viz render nonblank. `feature_dag.html` emits React DevTools info and a Babel warning, but no error-level console entry or favicon 404 was observed. |

## Findings Register

### AUD-R3-001 · major · `ENG/pipelineB_spec_eng.md:210`, `ENG/quality_gate_spec_eng.md:236`

Issue: Pipeline-B ATR is still internally contradictory.

Evidence:

- `pipelineB_spec_eng.md:210` starts correctly: canonical `l4_atr = mean_n(TR)`.
- The same line then says: "NB: this is **ATR = Wilder**, deliberately the same Wilder variant as
  Pipeline A's normalizer".
- `quality_gate_spec_eng.md:236` still says: "Pipeline B L4 reference (v2, textbook + guards):
  ... `ATR_n` (Wilder) ...".
- Decoded `feature_dag.html` data uses `l4_atr_n = mean_n(TR)`, and `build_contract_eng.md:411`
  correctly says ADX may use an internal Wilder-smoothed TR that is not canonical `l4_atr`.

Why wrong: The audit brief and glossary treat Pipeline B `l4_atr` as the intentionally different
plain rolling mean of TR, while Pipeline A uses Wilder ATR. Calling canonical Pipeline-B ATR Wilder
again reintroduces the exact divergence that was supposed to be fixed.

Precise repair: In `pipelineB_spec_eng.md:210`, delete the stale NB and replace it with the
`build_contract_eng.md` wording: canonical `l4_atr = mean_n(TR)`; ADX may use an internal
Wilder-smoothed TR, but that internal series is not canonical `l4_atr`. In
`quality_gate_spec_eng.md:236`, replace `ATR_n (Wilder)` with canonical `l4_atr = mean_n(TR)` and,
if needed, mention ADX's internal Wilder smoothing separately.

### AUD-R3-002 · major · `ENG/pipelineB_spec_eng.md:154-161`

Issue: Pipeline-B z-score zero-denominator behavior is still self-contradictory.

Evidence:

- `pipelineB_spec_eng.md:154-159` correctly gives z-score guards as `σ=0 -> 0`.
- `pipelineB_spec_eng.md:161` then says: "the additive ε floor is used instead of an explicit 0."
- Decoded `feature_dag.html` line for `l4_boll_z` states `(σ_n=0 -> 0)`.

Why wrong: `std=0 -> 0` and "use additive ε floor instead of explicit 0" are different mathematical
definitions. A flat-window z-score cannot be both neutral zero and `numerator / ε`.

Precise repair: Replace the line-161 note with a clean statement only: `z = (x - mean) / std if
std > 0 else 0`; this applies to all z-score and Bollinger z-score nodes. Do not mention ε-floor for
z-scores.

### AUD-R3-003 · major · `ENG/quality_gate_spec_eng.md:104-167`, `viz/main_data_flow.html:2081`

Issue: `summary.json` is still represented by two schemas once the visualization is included.

Evidence:

- `quality_gate_spec_eng.md:104-167` defines the frozen canonical schema with
  `schema_version`, `built_at_utc`, `inputs_hash`, `counters`, `parities`, `checks[]`, and
  `overall_status`.
- `main_data_flow.html:2081` displays a `summary.json` mock object with fields
  `parity`, `gaps`, `zero_values`, `features`, `split`, `alarms`, `gate`, and `inputs_hash`.

Why wrong: AC-5 requires the docs and `main_data_flow.html` to state the same facts. A viewer who
clicks the L8 summary panel receives a different schema from the frozen build contract.

Precise repair: Replace the visualization's `summary.json` mock with a minimal canonical object
using the fields from `quality_gate_spec_eng.md`: `schema_version: "1.0"`, `built_at_utc`,
`inputs_hash`, `counters`, `parities`, `checks`, and `overall_status`.

### AUD-R3-004 · major · `ENG/quality_gate_spec_eng.md:236-240`

Issue: Pipeline-B L4/L5/parity text still uses the old `v2` / `NOT in v1` framing.

Evidence:

- `quality_gate_spec_eng.md:236`: "Pipeline B L4 reference (v2, textbook + guards)".
- `quality_gate_spec_eng.md:238`: "Pipeline B L5 reference (v2)".
- `quality_gate_spec_eng.md:240`: "Reference v2 parity checks (would extend the §1.1 chain, NOT in
  v1)".

Why wrong: The current repair intent is to certify Pipeline B `L0-L5`. Calling L4/L5 `v2` and
describing related checks as "NOT in v1" preserves scope-narrowing language inside an audited spec.
It may be meant as "optional add-on to Pipeline-A L8", but the wording still reads as a certification
boundary.

Precise repair: Reword the section as "Optional add-on to the core Pipeline-A L8 gate for certified
Pipeline-B outputs." Remove `v2`, `reference v2`, and `NOT in v1`. If the add-on is optional, state
that it is optional for Pipeline-A's core gate, not that Pipeline-B L4/L5 are outside the certified
package.

### AUD-R3-005 · minor · `viz/main_data_flow.html:1868,2071`, `ENG/summary_rules_eng.md:31`

Issue: stale external-style references remain in certifiable artifacts.

Evidence:

- `main_data_flow.html:1868`: "full description: FLOW/L3".
- `main_data_flow.html:2071`: `label_uniqueness_weight (spec §6)`.
- `summary_rules_eng.md:31`: "`build_contract_eng.md` §Parameters; register C-xx for rationale".

Why wrong: These are not currently the sole source of build-critical facts, so this is not a major
buildability defect. But `Plan/` is supposed to be the certifiable SOT in isolation, and these
references keep pointing readers outward or to non-local section names.

Precise repair: Replace `FLOW/L3` with `ENG/L3_duckdb_raw_view_qc_eng.md` or
`ENG/build_contract_eng.md`; replace `spec §6` with `build_contract_eng.md §7.3`; replace
`register C-xx` with an in-Plan rationale note or remove the rationale pointer from the summary
rules.

## Buildability Gap List

1. **Canonical Pipeline-B ATR is still ambiguous.** A builder could implement either `mean_n(TR)` or
   Wilder ATR from the current specs.
2. **Pipeline-B z-score zero guard is still ambiguous.** The table says neutral zero; the note says
   epsilon floor.
3. **L8 `summary.json` schema is still not 1:1 across docs and visualization.**
4. **Pipeline-B certification boundary text is still muddy in `quality_gate_spec_eng.md`.**
5. **Some outward references remain in certifiable text and visualization labels.**

## Positive Checks That Now Pass

- `config/params.json` is valid JSON and contains `l8`, `splits`, `detector`, `pipeline_b`,
  `pipeline_b_l4`, and `pipeline_b_l5`.
- `config/universe.txt` has 503 lines and 503 unique tickers.
- `main_data_flow.html` no longer contains `2026-05-22`; the DuckDB and snapshot panels both use
  `2026-05-29 15:00`.
- `feature_dag.html` decodes successfully and its feature ids/edges validate.
- Markdown local links resolve.
- English-only scan returned 0 Polish hits.
- Both visualizations render nonblank with no runtime errors or missing favicon.

## Repair Plan

### Must

1. Remove the stale Wilder wording attached to canonical Pipeline-B `l4_atr` in
   `pipelineB_spec_eng.md` and `quality_gate_spec_eng.md`.
2. Fix the z-score guard note in `pipelineB_spec_eng.md:161` so it no longer mentions ε-floor for
   z-scores.
3. Update `viz/main_data_flow.html:2081` to show the canonical `summary.json` schema.
4. Remove `v2` / `NOT in v1` wording from the Pipeline-B L4/L5/parity add-on section of
   `quality_gate_spec_eng.md`.

### Should

1. Replace remaining outward references (`FLOW/L3`, `spec §6`, `register C-xx`) with in-Plan
   filenames/sections.
2. Re-run the same semantic scans before the next audit: ATR, z-score, `summary.json`, scope
   narrowing, stale dates, stale references, links, language, decoded DAG, and render.

## Sign-Off Statement

I cannot sign the requested statement yet. The package is close, but the remaining contradictions
are material: a competent team still cannot know whether Pipeline-B ATR is plain mean or Wilder,
whether zero-std z-scores return 0 or `x/ε`, and which `summary.json` shape the visualization is
committing to. Once those are corrected, the package should be a strong candidate for PASS.

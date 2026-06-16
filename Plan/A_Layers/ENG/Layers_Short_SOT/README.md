# Layers_Short_SOT — the total SOT (short, fact-only, canonical)

This folder is the **single source of truth** for building Pipeline A (the S&P 500 trend-line
meta-labeling strategy, layers L1–L10). Every build-critical fact — parameters, formulas, schemas,
contracts, QC predicates — is defined here, **once**, in short fact-only files.

## Governance (the canonical rule)

1. **This folder is canonical.** The companion docs at [`../`](..) (`build_contract_eng.md`,
   `detector_algorithm_eng.md`, `quality_gate_spec_eng.md`, `glossary_eng.md`, `readme_eng.md`,
   `summary_rules_eng.md`) are **subordinate**: narrative, rationale, worked examples and term
   definitions only. They **must not redefine** any fact owned here — they reference it.
2. **Each fact has exactly one home** (the fact-ownership map below). A fact appears in its home file and
   nowhere else; everything else points to it.
3. **On any divergence, the SOT wins** — fix the companion (or the viz) to match this folder, never the
   reverse.
4. **Style:** facts only — dense bullets/tables, one fact per line, physical/object perspective, no prose
   rationale and no worked examples (those live in the companions). This is what keeps the *total* SOT
   *short*.

## Files

Cross-cutting (own facts that span layers):

- [00_conventions_eng.md](00_conventions_eng.md) — notation · canonical naming forms · global numbers · cross-cutting rules.
- [00_parameters_eng.md](00_parameters_eng.md) — the single parameter registry (mirror of `config/params.json`): 17 keys + EPS + detector reference values + L8 threshold constants.
- [00_input_contract_eng.md](00_input_contract_eng.md) — input OHLCV table schema + invariants + `price_view` + naive-ET→UTC rule.
- [00_definition_of_done_eng.md](00_definition_of_done_eng.md) — the build acceptance checklist.

Per layer (own that layer's contract):

| Lv | File |
|----|------|
| L1 | [L1_source_alpaca_eng.md](L1_source_alpaca_eng.md) |
| L2 | [L2_lean_zip_store_eng.md](L2_lean_zip_store_eng.md) |
| L3 | [L3_duckdb_raw_view_qc_eng.md](L3_duckdb_raw_view_qc_eng.md) |
| L4 | [L4_snapshot_parquet_eng.md](L4_snapshot_parquet_eng.md) |
| L5 | [L5_time_split_eng.md](L5_time_split_eng.md) |
| L6 | [L6_setup_detector_eng.md](L6_setup_detector_eng.md) |
| L7 | [L7_features_x_label_y_eng.md](L7_features_x_label_y_eng.md) |
| L8 | [L8_data_quality_eng.md](L8_data_quality_eng.md) |
| L9 | [L9_optuna_xgboost_eng.md](L9_optuna_xgboost_eng.md) |
| L10 | [L10_oos_test_eng.md](L10_oos_test_eng.md) |

## Fact-ownership map

| Canonical fact | Home |
|---|---|
| Notation; canonical naming forms; global numbers (503 / 510 / 8 841 820); causality / determinism / one-shot / gate / scale-independence | `00_conventions_eng.md` |
| All parameters (17 `params.json` keys + EPS + `TOUCH_TOL` + detector `k`/`LOOKBACK`/`COOLDOWN` + L8 threshold constants) | `00_parameters_eng.md` |
| Input table schema + cross-bar invariants + `price_view` manifest + naive-ET→UTC rule | `00_input_contract_eng.md` |
| Definition of Done checklist | `00_definition_of_done_eng.md` |
| Source contract | `L1` |
| LEAN zip store + CSV row layout + ×10000 + naive ET | `L2` |
| DuckDB schema + `VIEW ohlcv_1h` + **QC-01…QC-11** + `_meta` + key numbers | `L3` |
| Atomic snapshot + parquet schema/path + parity | `L4` |
| Split dates + purge (=H=24) + embargo (=5 sess) + CV scheme | `L5` |
| Detector OUTPUT contract objects + 5 invariants + DET-09 | `L6` |
| 8 feature formulas + 7-X `FEATURE_MANIFEST` + label Y + Output A/B schema + `label_uniqueness_weight` | `L7` |
| L8 counters + parities P1/P2/P3 + `summary.json` schema + aggregation rule | `L8` |
| Optuna/XGBoost + `strategy_<TICKER>.py` artifact contract | `L9` |
| OOS one-shot + entry rule + TB exits + 503×metrics matrix + distribution report | `L10` |

## Companion docs (subordinate)

- [../build_contract_eng.md](../build_contract_eng.md) — build narrative / reader's guide; cites this folder, restates no fact.
- [../detector_algorithm_eng.md](../detector_algorithm_eng.md) — reference detector algorithm (one valid realization): pseudocode, fit math, worked examples.
- [../quality_gate_spec_eng.md](../quality_gate_spec_eng.md) — L8 worked example, dashboard layout, rationale.
- [../glossary_eng.md](../glossary_eng.md) — term dictionary (definitions).
- [../readme_eng.md](../readme_eng.md) — ENG package index.
- [../summary_rules_eng.md](../summary_rules_eng.md) — the writing standard.

Feature explanation ("Plan B", Stages F0–F14) is a separate, subordinate helper in
[`../../../B_Features/`](../../../B_Features/) — not part of this SOT.

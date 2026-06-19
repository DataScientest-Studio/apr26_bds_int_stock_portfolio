# Layers_Short_SOT — the total SOT (short, fact-only, canonical)

This folder is the **single source of truth** for building Pipeline A (the S&P 500 trend-line
meta-labeling strategy, layers L1–L11). Every build-critical fact — parameters, formulas, schemas,
contracts, QC predicates — is defined here, **once**, in short fact-only files.

## Governance (the canonical rule)

1. **This folder is canonical and self-contained** — it is the entire build SOT. There are no companion docs:
   every build-critical fact lives here (and data-state numbers in `../../config/data_state_numbers.json`).
2. **Each fact has exactly one home** (the fact-ownership map below). A fact appears in its home file and
   nowhere else; everything else points to it.
3. **On any divergence, the SOT wins** — fix the viz to match this folder, never the reverse.
4. **Style:** facts only — dense bullets/tables, one fact per line, physical/object perspective, no prose
   rationale and no worked examples. This is what keeps the SOT *short*.
5. **Frozen data-state numbers** (universe size, zip count, row count, store sizes, candles/day, price scale)
   are owned by [`../../config/data_state_numbers.json`](../../config/data_state_numbers.json), **not** typed into prose. They
   are generated into this SOT (and the viz) as `<!--na:…-->…<!--/na-->` marker regions.
   Never hand-edit such a number; edit the registry and run `python3 ../../config/data_state_gate.py build`.
   `python3 ../../config/data_state_gate.py check` enforces it. Tunable design knobs remain in `config/parameters.json`.

## Files

Cross-cutting (own facts that span layers):

- [00_conventions_eng.md](00_conventions_eng.md) — notation · canonical naming forms · global numbers · cross-cutting rules.
- [00_parameters_eng.md](00_parameters_eng.md) — the single parameter registry (mirror of `config/parameters.json`): 17 contract keys (incl. `EPS`) + detector reference values + L8 threshold constants.
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
| L9 | [L9_optuna_tuning_eng.md](L9_optuna_tuning_eng.md) |
| L10 | [L10_xgboost_strategy_eng.md](L10_xgboost_strategy_eng.md) |
| L11 | [L11_oos_test_eng.md](L11_oos_test_eng.md) |

## Fact-ownership map

| Canonical fact | Home |
|---|---|
| Notation; canonical naming forms; causality / determinism / one-shot / gate / scale-independence | `00_conventions_eng.md` |
| Frozen data-state numbers (universe size <!--na:universe_size-->503<!--/na--> / zip count <!--na:lean_zip_count-->510<!--/na--> / row count <!--na:duckdb_row_count_str-->8 841 820<!--/na--> / store sizes / candles per day / price scale) | [`../../config/data_state_numbers.json`](../../config/data_state_numbers.json) — single source; rendered into `00_conventions_eng.md` and elsewhere via `<!--na:…-->` markers; includes the ZIP-inventory to universe-size derivation note |
| All parameters (17 contract-table keys incl. `EPS` + top-level `TOUCH_TOL` + detector `k`/`LOOKBACK`/`COOLDOWN` + L8 threshold constants) | `00_parameters_eng.md` |
| Input table schema + cross-bar invariants + `price_view` manifest + naive-ET→UTC rule | `00_input_contract_eng.md` |
| Definition of Done checklist | `00_definition_of_done_eng.md` |
| Source contract | `L1` |
| LEAN zip store + CSV row layout + ×<!--na:price_scale-->10000<!--/na--> + naive ET | `L2` |
| DuckDB schema + `VIEW ohlcv_1h` + **QC-01…QC-11** + `_meta` + key numbers | `L3` |
| Atomic snapshot + parquet schema/path + parity | `L4` |
| Split dates + purge (=H=24) + embargo (=5 sess) + CV scheme | `L5` |
| Detector OUTPUT contract objects + 5 invariants + DET-09 | `L6` |
| 8 feature formulas + 8-X `FEATURE_MANIFEST` (7 geometric + `direction`) + label Y + Output A/B schema + `label_uniqueness_weight` | `L7` |
| L8 counters + parities P1/P2/P3 + `summary.json` schema + aggregation rule | `L8` |
| Optuna hyperparameter search (TPE/MedianPruner, purged WF CV) → `best_params.json` | `L9` |
| XGBoost final training (champion) + `strategy_<TICKER>.py` b64 artifact contract | `L10` |
| OOS one-shot + entry rule + TB exits + <!--na:universe_size-->503<!--/na-->×metrics matrix + distribution report | `L11` |

Feature explanation ("Plan B", Stages F0–F14) is a separate, subordinate helper in
[`../../../B_Features/`](../../../B_Features/) — not part of this SOT.

# 00 · Definition of Done (SOT)

Canonical home for the build acceptance checklist (spans all layers). Each item references the layer that
owns the underlying fact.

- [ ] The pipeline accepts raw OHLCV of any Asset (any price scale) and any `TF`; zero hardcoded price thresholds.
- [ ] Output B has exactly the schema of [L7](L7_features_x_label_y_eng.md) (column names and types match by sign).
- [ ] **Causality verified:** a test detecting use of any candle `> t` when computing a feature/line for `t` (e.g. shifting the future does not change historical values).
- [ ] `closed_through_line` is `1` from `entry_candle` onward and `0` before (on a clean setup).
- [ ] `Y_outcome` matches the first-touch rule and `BARRIER_MODE`; unit cases TP/SL/time-barrier covered by tests.
- [ ] `volume_z_score` correct for `std = 0` (returns `0`, not NaN/Inf); `body_to_range_ratio` correct for `high == low`.
- [ ] No NaN/Inf in Output B beyond documented cases (an Asset without volume → `volume_z_score = NaN` with an explicit flag).
- [ ] `label_uniqueness_weight` computed for overlapping windows (formula in [L7](L7_features_x_label_y_eng.md)).
- [ ] Partitioning per `asset_id` (one model / one `strategy_<TICKER>.py` with the model embedded as base64 `MODEL_B64` / one `MODEL_HASH` per asset; both directions share it).
- [ ] Determinism: same input → same output (hash-testable).
- [ ] **Splits verified by assertion:** no label window `[t0, t0+H]` crosses a Warm-up/Train/OOS boundary (purge + embargo of [L5](L5_time_split_eng.md) works).
- [ ] Strategy artifact ([L10](L10_xgboost_strategy_eng.md)): imports standalone, `selfcheck()` PASS, deterministic build (hash).
- [ ] OOS one-shot: artifacts frozen before the test; the OOS run writes `l11_asset_metrics.sqlite` (the asset-metrics DB) and never returns to tuning.
- [ ] Strategy accepted per the objective hierarchy (PF↑ → MaxDD↓ → realized TIM↓; WR informational); OOS reported in **PF · MDD · TIM · WR** order ([00_conventions_eng.md](00_conventions_eng.md)).
- [ ] `FEATURE_MANIFEST` contains exactly the **8 X columns** (7 geometric + `direction`); `closed_through_line` present in B as audit and constantly `= 1`.
- [ ] Setups rejected by detector invariant 5 (DET-09: `R0 ≤ 0` / `ATR(t0) ≤ 0` / missing `L_opp`) are counted in the audit report — they do not vanish silently.
- [ ] Endproduct ([L12](L12_endproduct_eng.md)): one `<TICKER>/` ticker folder per asset containing exactly `<TICKER>__L4_to_L12.ipynb` (the L4→L12 runner) + `<TICKER>_ohlcv_1h.parquet` + `OPTUNAs_XGB_HPOs_best_params.json` + `strategy_<TICKER>.py` + `<TICKER>_README.md` (5 files; the README is a derived human-readable report, not an authoritative store).

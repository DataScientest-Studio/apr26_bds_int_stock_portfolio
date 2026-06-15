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
- [ ] Partitioning per `{asset_id} × {direction}`.
- [ ] Determinism: same input → same output (hash-testable).
- [ ] **Splits verified by assertion:** no label window `[t0, t0+H]` crosses a Warm-up/Train/OOS boundary (purge + embargo of [L5](L5_time_split_eng.md) works).
- [ ] Strategy artifact ([L9](L9_optuna_xgboost_eng.md)): imports standalone, `selfcheck()` PASS, deterministic build (hash).
- [ ] OOS one-shot: artifacts frozen before the test; the OOS result never returns to tuning.
- [ ] `FEATURE_MANIFEST` contains exactly the **7 X columns**; `closed_through_line` present in B as audit and constantly `= 1`.
- [ ] Setups rejected by detector invariant 5 (DET-09: `R0 ≤ 0` / `ATR(t0) ≤ 0` / missing `L_opp`) are counted in the audit report — they do not vanish silently.

# C01 · F0 — Load raw OHLCV (feature Stage F0)

Load the chosen asset's raw OHLCV and build the F0 base series the whole DAG sits on.

- Realizes: [F0](../ENG/Stages_Short_SOT/F0_raw_ohlcv_eng.md).
- Role: feature-stage cell (raw input).
- Input: `SYMBOL`, `paths` from [C00](C00_setup_and_asset_select_eng.md).
- Does:
  - read the asset's raw 1h OHLCV (the Lean hour `.zip` for `SYMBOL`) into one DataFrame.
  - sort ascending by time into one continuous series; build `ts` and the integer bar index `t`.
  - expose the five F0 channels (`open`, `high`, `low`, `close`, `volume`) and `prev_close = close[t−1]`.
  - (optional) cross-check the recomputed series against the pre-built transforms parquet for `SYMBOL`; mismatch is a warning, not the source.
- Produces: `ohlcv` — the F0 series (`ts`, `t`, `open`, `high`, `low`, `close`, `volume`, `prev_close`). No feature ids at F0 (the `f{stage}_…` grammar starts at F1).
- Guards: one continuous ascending series per asset; F0 is raw input, no fit, no look-ahead — see [F0](../ENG/Stages_Short_SOT/F0_raw_ohlcv_eng.md).
- Check: monotonic `ts`, contiguous `t`, no duplicate bars; the five channels present and finite; `prev_close` defined for `t ≥ 1`.
- Output: `ohlcv` → [C02](C02_time_split_eng.md) (split) and the feature cells [C03](C03_f1_atomic_transforms_eng.md)+.

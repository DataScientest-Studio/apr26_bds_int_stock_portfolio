# F1 · Time split — Warm-up / Train / OOS (SOT)

A **scaffold / data-handling Stage** (produces no `f{stage}_…` ids): split the one continuous per-asset
series into disjoint windows up front, so every later fit touches **Train only** and OOS stays frozen. This is
the leakage backbone — it precedes every fit-on-Train Stage (F4 regimes, F6 representations, F9 selection,
F10 calibration). Values inlined from the Pipeline-A build SOT
([A_Layers/L5](../../../A_Layers/ENG/Layers_Short_SOT/L5_time_split_eng.md)).

- Input: the raw OHLCV series from [F0](F0_raw_ohlcv_eng.md) (one continuous series per asset, sorted by `t`).
- **Three disjoint windows** (by integer bar position):
  - **Warm-up** `2016-01-04 → 2016-10-14` — rolls in the longest feature window (max ≈ 20 candles); not trained on.
  - **Train** `2016-10-17 → 2023-12-29` — the only window any object is fit on.
  - **OOS** `2024-01-02 → 2026-05-29` — frozen; read once at [F11](F11_oos_evaluation_eng.md).
- **Purge** = `24` candles (`H`): drop rows whose label window `[t0, t0+H]` crosses a window boundary.
- **Embargo** = `5` sessions (~`35` candles) after the Train→OOS boundary (covers rolling-feature autocorrelation).
- **CV** = **purged walk-forward** folds defined **inside Train** (used by F9 selection + F10 tuning).
- Family: none (produces split masks, not features).
- Output: `split` — Warm-up / Train / OOS masks + the CV fold scheme + purge/embargo sizes → consumed by every
  fit-on-Train Stage; see [00_leakage_contract_eng.md](00_leakage_contract_eng.md).

# Build contract — Pipeline A (reader's guide)

> **This document is subordinate to the SOT.** Every parameter, formula, schema, contract and number for
> Pipeline A is owned by the short fact-only files in [`Layers_Short_SOT/`](../../A_Layers/ENG/Layers_Short_SOT/). This guide
> is **narrative only** — it explains *why* the pipeline is shaped the way it is and *where* each fact
> lives. It **restates no fact**; on any divergence, the SOT wins. Start at
> [`Layers_Short_SOT/README.md`](../../A_Layers/ENG/Layers_Short_SOT/README.md).

Pipeline A is the **S&P 500 trend-line meta-labeling strategy pipeline** — layers **L1–L10**: source
candles → LEAN ZIP store → DuckDB (`raw_ohlcv_1h` + `VIEW ohlcv_1h`, QC-gated) → parquet snapshot → time
split → trend-line setup **detector** (L6) → features X + label Y (L7) → quality dashboard (L8) →
Optuna→XGBoost strategy artifact (L9) → one-shot OOS test (L10). `layer` / `L1–L10` belong to Pipeline A
only.

## How to build from this package

A competent engineer can build Pipeline A from `Plan/A_Layers/` alone. The build-critical facts are all in
[`Layers_Short_SOT/`](../../A_Layers/ENG/Layers_Short_SOT/):

- Conventions, naming and global numbers → [`Layers_Short_SOT/00_conventions_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_conventions_eng.md).
- Every parameter (the only configuration site) → [`Layers_Short_SOT/00_parameters_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_parameters_eng.md).
- The input table contract → [`Layers_Short_SOT/00_input_contract_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_input_contract_eng.md).
- Acceptance / Definition of Done → [`Layers_Short_SOT/00_definition_of_done_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/00_definition_of_done_eng.md).
- One file per layer (L1–L10), each owning that layer's contract.

This guide walks the same ground in prose; the companions [detector_algorithm_eng.md](detector_algorithm_eng.md)
(the reference detector geometry) and [quality_gate_spec_eng.md](quality_gate_spec_eng.md) (the L8 worked
example) add depth without owning facts. Terminology is defined in [glossary_eng.md](glossary_eng.md).

## The build, layer by layer

- **L1 — Source (Alpaca).** Hourly OHLCV for the 503-ticker universe is downloaded via QuantConnect LEAN,
  topped up hourly. Prices arrive raw (no corporate-action adjustment — open risk R1). Details:
  [`Layers_Short_SOT/L1_source_alpaca_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L1_source_alpaca_eng.md).
- **L2 — LEAN ZIP store.** The durable archive; one zip per ticker, integer prices, naive-ET timestamps.
  It is the source of truth from which the database is rebuilt.
  [`Layers_Short_SOT/L2_lean_zip_store_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L2_lean_zip_store_eng.md).
- **L3 — DuckDB + QC.** The analytical store: raw integers in `raw_ohlcv_1h`, USD only in `VIEW ohlcv_1h`
  (a view, not a copy). Every load is gated by QC-01…QC-11; a failing load is not published.
  [`Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L3_duckdb_raw_view_qc_eng.md).
- **L4 — Snapshot → parquet.** An atomic snapshot isolates transforms from the live store; it is
  materialized to one clean OHLCV parquet per ticker (zero derived columns — features come only at L7).
  [`Layers_Short_SOT/L4_snapshot_parquet_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L4_snapshot_parquet_eng.md).
- **L5 — Time split.** Three disjoint windows (warm-up / Train / OOS) as indices on one continuous series,
  with a purge and an embargo at the boundaries so a label window never reaches across.
  [`Layers_Short_SOT/L5_time_split_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L5_time_split_eng.md).
- **L6 — Detector.** A causal trend-line setup detector emits, per setup, the geometric objects the features
  and label need. This package fixes the **output contract** (the objects + 5 invariants + DET-09) and
  defers the *geometry* to a reference algorithm. Contract:
  [`Layers_Short_SOT/L6_setup_detector_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L6_setup_detector_eng.md); reference
  geometry: [detector_algorithm_eng.md](detector_algorithm_eng.md).
- **L7 — Features X + label Y.** The transformer computes 8 columns at `t0` (7 of them the model's X), and a
  triple-barrier label. Output B (one row per setup, partitioned by `{asset × direction}`) is the ML
  deliverable. [`Layers_Short_SOT/L7_features_x_label_y_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L7_features_x_label_y_eng.md).
- **L8 — Quality gate.** One dashboard measures the whole flow (parities + counters) and reports; a FAIL
  closes the gate and L9 does not start. [`Layers_Short_SOT/L8_data_quality_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L8_data_quality_eng.md);
  worked example: [quality_gate_spec_eng.md](quality_gate_spec_eng.md).
- **L9 — Optuna → XGBoost → strategy.py.** Tuning and training happen in Train only; the deliverable is one
  self-contained `strategy_<TICKER>.py` per asset (model in base64, frozen feature manifest, self-check).
  [`Layers_Short_SOT/L9_optuna_xgboost_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L9_optuna_xgboost_eng.md).
- **L10 — OOS test.** Artifacts are frozen (hashed), then run exactly once over the OOS window; the result
  is a per-asset metrics matrix read as a distribution, never fed back into tuning.
  [`Layers_Short_SOT/L10_oos_test_eng.md`](../../A_Layers/ENG/Layers_Short_SOT/L10_oos_test_eng.md).

## Why the pipeline is shaped this way (rationale)

- **Causality is the overriding rule.** For candle `t`, only candles `≤ t0` inform the fits, features and
  break detection. The only forward-looking object is the L7 label window `[t0, t0+H]`. A CI test enforces it.
- **The barriers are geometric, so there is no ATR↔label leakage.** Take-profit comes from `R0` (a distance
  to `L_opp`) and the time barrier counts candles; neither depends on ATR. ATR appears only as a *feature
  normalizer* (and as the detector's touch-tolerance scale) — so the classic "ATR in both the feature and
  the label" leakage cannot occur here.
- **The model is a meta-label, not a signal generator.** The primary signal is the detector's trend-line
  break; XGBoost only *filters* it (`binary:logistic`, threshold at entry). This keeps the search space
  small and the artifact auditable.
- **One-shot OOS protects the verdict.** Artifacts are hashed before the single OOS run, and the OOS result
  never returns to tuning — the next iteration is a fresh cycle with a later OOS.
- **Scale- and timeframe-independence.** No hardcoded price thresholds; all TF dependence is confined to `H`
  (and optionally `W_VOL`/`W_ATR`), so a different `TF` is a reconfiguration, not a rewrite.

## Canonical vs. reference design

The build SOT covers **Pipeline A end-to-end**. The L6 detector is a *reference implementation* of the
output contract: the §contract objects, the five invariants, DET-09, the close-based strict-`>` break and
the canonical parameters (`MIN_TOUCHES=2`, `H=24`, `W_ATR=14`, `ATR_VARIANT=wilder`, `PRICE_VIEW=raw_usd_view`,
`EPS=1e-9` — all owned by `00_parameters_eng.md`) are **canonical**. The detector *geometry* in
[detector_algorithm_eng.md](detector_algorithm_eng.md) and the L8 numeric thresholds in
[quality_gate_spec_eng.md](quality_gate_spec_eng.md) are **reference design (one valid realization)** —
replaceable behind the output contract / gate structure without changing what the model sees.

## Feature explanation ("Plan B", separate)

What the features *are* and where they come from (families, derivation) is a **subordinate helper**, not
part of this build SOT: see [`feature_explanation_plan_b_eng.md`](../../B_Features/feature_explanation_plan_b_eng.md)
(an OHLCV → feature DAG, **Stages F0–F14**, ids `f{stage}_…`). It is not a build pipeline; Pipeline A
does not depend on it.

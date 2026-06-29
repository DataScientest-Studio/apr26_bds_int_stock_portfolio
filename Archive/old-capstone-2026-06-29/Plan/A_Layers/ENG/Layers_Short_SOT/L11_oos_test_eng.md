# L11 · SQLite asset-metrics database + OOS verdict (SOT)

The one-shot OOS run materialized as a concrete artifact: a SQLite database holding one row of metrics per asset
(a wide <!--na:universe_size-->503<!--/na-->-asset metric matrix) plus a distribution report.
Input = the frozen `strategy_<TICKER>.py` artifacts from [L10](L10_xgboost_strategy_eng.md).

## Purpose

- Run the frozen strategies **once** on the untouched OOS window and **persist the verdict as a database artifact**.
- `l11_asset_metrics.sqlite` is the OUTPUT of the one-shot OOS run — the object every downstream reader queries.
- We read a **distribution** across the universe, not a single star.

## Input

- The frozen `strategy_<TICKER>.py` artifacts (×<!--na:universe_size-->503<!--/na-->) from [L10](L10_xgboost_strategy_eng.md).
- Before the run, the hash of each strategy file (`MODEL_HASH`) goes into the hash register; from that moment the artifacts are immutable.
- The OOS window `2024-01-02 → 2026-05-29` (frozen at [L5](L5_time_split_eng.md), untouched until now).

## SQLite artifact

- File: `l11_asset_metrics.sqlite` — a single SQLite database, the OUTPUT of the one-shot OOS run.
- Self-contained, queryable, immutable once written; carries the run identity (`run_id` + `created_at` + the strategy hash register).
- Storage role: a **store/artifact** (the OOS analogue of the L3 `DuckDB` analytical store), never a tuning input.

## Schema / logical layout

One home per fact; the wide metric matrix is the centre.

| Table | Role | Key columns |
|---|---|---|
| `run_manifest` | run identity | `run_id`, `oos_window_start`, `oos_window_end`, `created_at`, `strategy_hash_register` (per-asset `MODEL_HASH`), `metric_order` |
| `asset_registry` | the <!--na:universe_size-->503<!--/na--> assets | `asset_id`, `ticker`, `column_order` (frozen position in the wide matrix) |
| `metric_registry` | the metric definitions | `metric_id` ∈ {`PF`, `MDD`, `TIM`, `WR`, `trades`}, `unit`, `objective_role` |
| `asset_metrics_503` | **the wide metric matrix** | one `metric_id` row × <!--na:universe_size-->503<!--/na--> asset columns (one column per `asset_id`) |
| `distribution_report` | per-metric distribution | `metric_id`, `min`/`median`/`max`, `top_assets`, `bottom_assets`, `share_pf_gt_1` |
| `asset_metric_long` | optional helper **VIEW** | long form `(asset_id, metric_id, value)` — a tidy unpivot of `asset_metrics_503` for ad-hoc queries |

- `asset_metrics_503` is the wide matrix: rows = metrics, columns = the <!--na:universe_size-->503<!--/na--> assets (column order pinned by `asset_registry.column_order`).
- `asset_metric_long` is a convenience VIEW only — no second source of truth; it unpivots the wide matrix without disturbing the <!--na:universe_size-->503<!--/na-->-column layout.

## Metric matrix

- One row of metrics per asset; canonical metric order **PF · MDD · TIM · WR** (= `METRICS`; see [00_conventions_eng.md](00_conventions_eng.md)).
- `PF` (profit factor) = gross profits / gross losses — **maximized**.
- `MDD %` — maximum drawdown — **minimized**.
- `TIM %` — time in market (% of candles with an open position) — **minimized** (realized time-in-market).
- `WR %` — win-rate (% of winning trades) — **informational**.
- `trades` — number of trades; **auxiliary** column, the denominator of significance (not part of the PF · MDD · TIM · WR order).
- Each cell is produced by a single OOS replay per asset: the detector generates setups, the strategy assembles the 8 X manifest (7 geometric features at `t0` + `direction`), the model returns `p = model(x)`, entry rule `p ≥ 0.60 → ENTRY`, exits per triple barrier (fixed TP from `R0` · SL = moving `L_opp(t)` · time barrier 24 candles).

## Distribution report

- Stored in `distribution_report`: per-metric distributions, top/bottom assets, the share with `PF > 1`.
- **Verdict read through the objective** ([00_conventions_eng.md](00_conventions_eng.md)): rank/judge by PF (primary) → MaxDD → realized TIM; WR informational; Sharpe unused.
- We look for a **distribution**, not a single star.

## Invariants

- **One-shot:** the OOS window is tested **once**, after freezing the artifacts; the resulting `l11_asset_metrics.sqlite` never goes back into tuning (the next iteration = a new cycle from Train with a later OOS).
- **Determinism:** the same frozen artifacts + the same OOS window → the same `l11_asset_metrics.sqlite` (reproducible run).
- **External report:** the DB does **not** modify any `strategy_<TICKER>.py` or its `MODEL_HASH`, and does **not** filter the <!--na:universe_size-->503<!--/na--> shipped folders ([L12](L12_endproduct_eng.md)).

## Output

- `l11_asset_metrics.sqlite`: the <!--na:universe_size-->503<!--/na-->-asset metric matrix + distribution report + run manifest.
- Consumed read-only by reviewers and by [L12](L12_endproduct_eng.md) (as an external verdict; not packaged inside the per-asset folders).

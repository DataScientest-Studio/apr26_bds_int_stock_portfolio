# 00 · Conventions (SOT)

Canonical home for notation, naming forms, global numbers and the cross-cutting rules of Pipeline A.
Owned here; companion docs reference this file and restate nothing.

## Notation

- `t` = candle index = integer position after ascending sort by time, on one continuous series per asset.
- `t0` = `entry_candle` (the position-opening candle).
- `sign` = `direction` ∈ {`+1`, `−1`} — the setup side (L6); also the 8th `FEATURE_MANIFEST` column (L7), so one model per asset covers both directions.
- `c / o / h / l / v` = close / open / high / low / volume of candle `t`.
- `ε` = `EPS` = `1e-9` (division-by-zero guard).
- All line functions (`L_trend(t)`, `L_opp(t)`), `H`, the purge and the cooldown operate on the **index**, never on the timestamp.

## Canonical naming forms (one naming across the whole project)

| Concept | Canonical form | Avoid |
|---|---|---|
| Analytical store (cylinder badge) | `DuckDB` | "duck", "kaczka" |
| USD price view | `VIEW ohlcv_1h` (in prose: the `ohlcv_1h` view), add "(USD)" when needed | "VIEW USD", "USD view" |
| OOS metrics order | **PF · Sharpe · MDD · TIM · WR** (= `METRICS` array) | PF · MDD · TIM · Sharpe · WR |
| Quality gates | `QC-01…QC-11` (11 QC gates) | "QC-01…11", "11 padlocks" |
| Database snapshot | `atomic snapshot` | "snapshot atomic" |
| Roll-in phase (prose) | `warm-up` (code/filenames: `warmup`) | "warm up", "warmup" in prose |
| Layer numbering | **L1–L11** (Detector = L6, Features = L7, Quality gate = L8, Optuna search = L9, XGB final + artifact = L10, OOS = L11) | L1–L10; out-of-order layers |
| Input price view | `raw_usd_view` | — |
| Presentation language | viz UI + `README.md` + this `ENG/` package = English | — |

**Scheme reservation:** `layer` / `L1–L11` belong to **Pipeline A only**. The feature explanation
("Plan B") uses **Stages `F0–F14`** and ids `f{stage}_…` — never `L#`.

## Global numbers (agree everywhere)

_Canonical values mirror [`../../config/data_state_numbers.json`](../../config/data_state_numbers.json); rendered here via `na:` markers — edit the registry, not these lines._

- **<!--na:universe_size-->503<!--/na-->** — universe size (quality-filtered subset of the <!--na:lean_zip_count-->510<!--/na--> ZIP inventory); derivation in `config/data_state_numbers.json` → `_universe_derivation`; list pinned in `config/universe_tickers.txt`.
- **<!--na:lean_zip_count-->510<!--/na-->** — full LEAN ZIP inventory (one zip per downloaded ticker). The universe is its quality-filtered subset, so a few inventory tickers (non-constituents / failing the history-gap criteria) are not in the universe. Derivation: `config/data_state_numbers.json` → `_universe_derivation`.
- **<!--na:duckdb_row_count_str-->8 841 820<!--/na-->** — rows in `raw_ohlcv_1h` (<!--na:universe_size-->503<!--/na--> symbols).
- **<!--na:lean_zip_size_mb-->139<!--/na--> MB** — LEAN zip store total size.
- **<!--na:duckdb_size_mb-->166<!--/na--> MB** — DuckDB database file size.
- **×<!--na:price_scale-->10000<!--/na-->** — price storage scale in the LEAN archive / `raw_ohlcv_1h` table (deci-cents).
- **~<!--na:candles_per_day_typical-->7<!--/na-->** — 1h candles per RTH session day (09:00–16:00 ET); candles/day ∈ <!--na:candles_per_day_range_str-->[5, 9]<!--/na-->.

## Cross-cutting rules

- **ML pipeline** — the whole flow from raw market data to the strategy file and the OOS test; 11 levels L1–L11.
- **Asset** — any instrument with OHLCV data; the pipeline is independent of price scale and timeframe.
- **Candle / OHLCV** — one bar with the five fields `open, high, low, close, volume` in a given timeframe.
- **TF (timeframe)** — candle resolution; default `1h` (see [00_parameters_eng.md](00_parameters_eng.md)).
- **Scale- and timeframe-independence** — zero hardcoded price thresholds; the only TF dependence lives in `H` (and optionally `W_VOL`/`W_ATR`).
- **Causality / zero look-ahead** — for candle `t` only data from candles `≤ t` is used. No feature, line or decision depends on the future; the only forward-looking object is the label window `[t0, t0+H]` (L7). Verified by a causality test in CI.
- **Determinism** — the same input state → the same result; guaranteed by seeds, artifact hashes and manifests at every stage.
- **One-shot** — the OOS window is tested **once**, after freezing the artifacts; the OOS result never goes back into tuning.
- **Gate** — an automatic pass-on condition (QC on the L3 load; a non-FAIL L8 dashboard before training).
- **Parameters** — the only configuration site is `config/parameters.json`; all values are owned by [00_parameters_eng.md](00_parameters_eng.md).

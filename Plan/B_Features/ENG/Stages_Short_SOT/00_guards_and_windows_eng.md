# 00 · Guards & windows (SOT)

Canonical home for the numeric guards and the (illustrative) window conventions. Plan B is **decoupled from
any store**, so these are **explanatory conventions for understanding the formulas**, not a pinned store
contract — there is no `config/parameters.json` here (that belongs to Pipeline A).

## Guard conventions (`ε = 1e-9`)

| Guard | Definition | Use |
|---|---|---|
| `safe_div(a, b)` | `a / (b + ε)` | every division (returns, ratios, distances) |
| `safe_max(x, ε)` | `max(x, ε)` | denominators that are a magnitude/range (e.g. `high − low`) |
| `safe_log_ratio(a, b)` | `NULL if a ≤ 0 or b ≤ 0 else ln(a / b)` | log-returns, log-price ratios |
| rolling z-score | `σ = 0 → 0` (return an explicit `0`, never `NaN`/`Inf`) | all standardized features |

`NULL` features (e.g. `safe_log_ratio` on a non-positive price) are dropped, never imputed.

## Window / lag conventions (illustrative)

- Rolling length `n`: typical **`n ∈ {5, 10, 20, 50}` on 1h**, **`{20, 200}` on 1d** — illustrative, not store-pinned.
- Lag `k`: small integer lags (`1, 2, …`) for adjacent-bar features.
- F5 indicator periods follow textbook defaults (e.g. RSI `14`, MACD `12/26/9`, ATR `14`, Stoch/ADX/MFI `14`) — owned per-feature in [F5_classical_indicators_eng.md](F5_classical_indicators_eng.md).
- MTF resample: **1h → 1d** only (the native bar is 1h; sub-hour grids are finer than the native bar and out of scope).

## Causality of windows

Every rolling window and lag looks **backward only** (bars `≤ t`); no centered or forward windows. The full
causality / leakage rules are owned by [00_leakage_contract_eng.md](00_leakage_contract_eng.md).

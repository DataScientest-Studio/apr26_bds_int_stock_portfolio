# F5 · Classical indicators (SOT)

Textbook indicators as compressed functions of F2–F4, ε-guarded. Canonical short forms below; the extended
derivations + worked examples live in the companion [../feature_formulas_eng.md](../feature_formulas_eng.md).
Periods follow textbook defaults ([00_guards_and_windows_eng.md](00_guards_and_windows_eng.md)).

| Feature id | Family | Definition (canonical short form) |
|---|---|---|
| `f5_rsi_14` | returns | Wilder RSI, period 14 |
| `f5_macd_hist_12_26_9` | returns | MACD histogram = MACD(12,26) − signal(9) |
| `f5_atr` | range | `mean_n(TR)`, `TR = max(high − low, abs(high − prev_close), abs(low − prev_close))`, `n = 14` |
| `f5_obv` | volume | on-balance volume (signed-volume cumulant) |
| `f5_adl` | volume | accumulation/distribution line (CLV-weighted volume cumulant) |
| `f5_stoch_k_14` | range | stochastic %K, period 14 |
| `f5_adx_14` | range | average directional index, period 14 (internal Wilder-smoothed TR; **not** named `f5_atr`) |
| `f5_mfi_14` | volume | money-flow index, period 14 |
| `f5_vwap_distance` | price | `safe_div(close − VWAP, VWAP)` |

- All indicators are causal (bars `≤ t`) and ε-guarded on every division.
- `f5_atr = mean_n(TR)` is the **plain mean of TR** (Plan B convention); ADX uses its own internal Wilder TR smoothing, which is **not** `f5_atr`.
- Output: F5 features feed [F6](F6_research_representations_eng.md) (stack) and are direct model-candidate features.

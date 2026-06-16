# F3 · Rolling / temporal (SOT)

Lags and rolling windows of length `n` over F2 features. Window sets are illustrative (`n ∈ {5,10,20,50}` on
1h) — see [00_guards_and_windows_eng.md](00_guards_and_windows_eng.md). All windows are **backward-only**.

| Feature id | Family | Formula |
|---|---|---|
| `f3_mom_n` | returns | rolling sum of `f2_r_cc` over the last `n` bars (momentum) |
| `f3_vol_return_std_n` | range | rolling std of `f2_r_cc` over `n` (realized volatility) |
| `f3_volume_z_n` | volume | `(f2_volume_log − mean_n) / std_n`; **`std = 0 → 0`** |
| `f3_path_drawdown_n` | range | `safe_div(close, rolling_high_n) − 1` |

- `mean_n` / `std_n` / `rolling_high_n` are computed over the trailing window ending at `t` inclusive.
- A rolling feature is `NULL` until its window has rolled in (`t < n−1`); NULLs are dropped, never imputed.
- Output: F3 features feed [F4](F4_mtf_regime_eng.md) (regimes), [F5](F5_classical_indicators_eng.md) and [F6](F6_research_representations_eng.md).

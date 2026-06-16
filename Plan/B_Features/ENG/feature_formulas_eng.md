# Feature formulas — derivations & worked examples (companion)

> **Subordinate to the SOT.** The canonical short forms of every feature are owned by
> [`Stages_Short_SOT/`](Stages_Short_SOT/) (per-Stage F-files); guards by
> [`Stages_Short_SOT/00_guards_and_windows_eng.md`](Stages_Short_SOT/00_guards_and_windows_eng.md). This
> document is the **reference derivation** companion (the analogue of Pipeline A's `detector_algorithm_eng.md`):
> it gives the *how and why* — extended derivations and worked examples for the F4 indicators and the F5
> methods. It restates no canonical short form; on any divergence, the SOT wins.

All formulas are **causal** (bars `≤ t`) and ε-guarded; `prev_close = close[t−1]`.

## F1 — atomic transforms (notes)

- **CLV / close position** `f2_close_position = safe_div(close − low, safe_max(high − low, ε))` ∈ [0,1]: where
  the close sits within the bar's range (0 = at the low, 1 = at the high).
- **Wick imbalance** uses `f2_upper_wick = high − max(open, close)` and `f2_lower_wick = min(open, close) − low`
  (both ≥ 0); a long lower wick vs short upper wick signals intrabar rejection of lows.
- **Log return** `f2_r_cc = safe_log_ratio(close, prev_close)`: additive across bars, symmetric, `NULL` on a
  non-positive price (dropped, not imputed).

## F4 — classical indicators (derivations)

- **True range & ATR.** `TR_t = max(high − low, |high − prev_close|, |low − prev_close|)`. The canonical
  `f5_atr` short form is owned by the F4 SOT; note the Plan-B convention is the **plain mean** of TR over
  `n = 14` (**not** Wilder smoothing — ADX's internal TR smoothing is separate).
- **RSI (Wilder, 14).** Split each bar's price change into gain `U_t = max(Δclose, 0)` and loss
  `D_t = max(−Δclose, 0)`. Wilder-smooth both: `avgU_t = (avgU_{t−1}·13 + U_t)/14`, likewise `avgD`. Then
  `RS = safe_div(avgU, avgD)`, `f5_rsi_14 = 100 − 100/(1 + RS)`.
- **MACD histogram.** `MACD = EMA_12(close) − EMA_26(close)`; `signal = EMA_9(MACD)`;
  `f5_macd_hist_12_26_9 = MACD − signal`.
- **Stochastic %K (14).** `f5_stoch_k_14 = 100 · safe_div(close − min_low_14, safe_max(max_high_14 − min_low_14, ε))`.
- **OBV.** running cumulant: add `volume` when `close > prev_close`, subtract when `close < prev_close`, else 0.
- **ADL.** money-flow multiplier `M = safe_div((close − low) − (high − close), safe_max(high − low, ε))`;
  `f5_adl` is the running cumulant of `M · volume`.
- **MFI (14).** typical price `TP = (high + low + close)/3`; raw money flow `TP · volume`; positive/negative by
  the sign of `ΔTP`; `MFI = 100 − 100/(1 + safe_div(Σpos_14, Σneg_14))`.
- **ADX (14).** directional movement `+DM/−DM` smoothed (Wilder) over an internally-smoothed TR; `DX` from the
  `+DI/−DI` spread; `f5_adx_14` = smoothed `DX`. The ADX-internal Wilder-TR is **not** `f5_atr` (which is the
  plain mean of TR — see the F4 SOT).
- **VWAP distance.** `f5_vwap_distance = safe_div(close − VWAP, VWAP)`, `VWAP` = volume-weighted average price
  over the chosen window.

### Worked example — RSI step

Bars with Δclose = `+0.4, −0.2, +0.1, …`. Seeds (simple mean of the first 14 `U`/`D`) give `avgU₀, avgD₀`;
the next bar updates `avgU = (avgU₀·13 + 0.4)/14`. With `avgU = 0.18, avgD = 0.12`: `RS = 0.18/0.12 = 1.5`,
`RSI = 100 − 100/2.5 = 60`. (Illustrative numbers, not data.)

## F5 — research representations (methods)

- **PCA (`f6_pca_8`).** Standardize the F2–F5 stack on Train; take the top 8 principal directions of the Train
  covariance; project new bars onto that fixed basis.
- **Wavelet (`f6_dwt_db4_l3`).** Daubechies-4 DWT of a trailing window; keep the per-level energies for 3
  levels (multi-resolution volatility signature).
- **Autoencoder (`f6_ae_8`).** Train a bottleneck network on the standardized stack; the 8-dim code is the
  feature; encoder weights frozen after Train.
- **Sequence embedding (`f6_seq_lstm32`).** An LSTM (hidden = 32) over the recent feature sequence; the final
  hidden state (or a pooled summary) is the embedding; backward-only, frozen after Train.

Every F5 object (basis / weights / standardizer) is fit on **Train only** and applied forward unchanged
(see [`Stages_Short_SOT/00_leakage_contract_eng.md`](Stages_Short_SOT/00_leakage_contract_eng.md)).

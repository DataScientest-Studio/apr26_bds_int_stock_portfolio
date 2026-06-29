# 00 · Feature families (SOT)

Canonical home for the **6 feature families**. `family` is a separate attribute of every feature node (not an
id token, see [00_conventions_eng.md](00_conventions_eng.md)); it is the legend colour in the feature DAG.
Both viz (`viz/feature_dag.html` and `viz/main_feature_flow.html`) use these colours verbatim.

| Family | Meaning | Hex colour | Example features |
|---|---|---|---|
| `price` | absolute price levels / averages | `#3a6fa3` | `f2_tp`, `f2_ohlc4` |
| `returns` | log returns, gaps, momentum (changes between bars) | `#3f8556` | `f2_r_cc`, `f2_gap_open`, `f3_mom_n` |
| `range` | range / volatility proxies (dispersion within or across bars) | `#b87333` | `f2_candle_range`, `f3_vol_return_std_n`, `f5_atr` |
| `candle` | candle geometry (body, wicks, position within range) | `#7a4e9e` | `f2_candle_body_abs`, `f2_lower_wick`, `f2_close_position` |
| `volume` | volume and dollar-volume transforms | `#b54a45` | `f2_volume_log`, `f2_volume_dollar`, `f3_volume_z_n` |
| `meta` | synthesis / regime / embedding (functions of other features) | `#3a3a3a` | `f3_vol_regime`, `f5_pca_8`, `f5_ae_8` |

Rules:
- Every feature node (F0 raw + F2–F6) carries **exactly one** family.
- The family is **orthogonal to the stage**: e.g. `returns` appears across F2 (`f2_r_cc`) and F3 (`f3_mom_n`).
- The scaffold Stages (F1 split, F7 label, F8 assemble, F11 OOS), the model Stages (F9 selection, F10
  calibration), the artifact Stage (F12), and the cross-asset Stages (F13 entry table, F14 correlation) carry
  **no family** (they chunk the data / consume the feature space / consume models — they do not produce features).

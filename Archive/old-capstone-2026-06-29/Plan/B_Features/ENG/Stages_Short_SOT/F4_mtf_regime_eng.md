# F4 · MTF / regime / context (SOT)

Multi-timeframe and regime context: resample 1h → 1d, recompute F2/F3 on the coarser grid, bucket into
regimes, and tag the session phase. Regimes condition other features (drawn as **dashed** context edges in
the viz).

| Feature id | Family | Definition |
|---|---|---|
| `f4_vol_regime` | meta | volatility bucket {low, mid, high} from a rolling-vol metric (quantile cutoffs, e.g. `[0.33, 0.66]`) |
| `f4_volume_regime` | meta | volume bucket from `f3_volume_z` (thresholds, e.g. `[−1, 1]`) |
| `f4_session_open_phase` | meta | from minute-of-session (session start) |
| `f4_session_midday_phase` | meta | from minute-of-session (midday) |
| `f4_session_close_phase` | meta | from minute-of-session (session end) |

- Resample is **1h → 1d only** (the native bar is 1h; sub-hour grids are out of scope).
- Quantile / threshold cutoffs are computed on the **Train window only** (see [00_leakage_contract_eng.md](00_leakage_contract_eng.md)) and applied forward.
- Regimes are causal (bars `≤ t`); they condition F5/F6 features but do not look ahead.
- Output: F4 context feeds [F5](F5_classical_indicators_eng.md) and [F6](F6_research_representations_eng.md).

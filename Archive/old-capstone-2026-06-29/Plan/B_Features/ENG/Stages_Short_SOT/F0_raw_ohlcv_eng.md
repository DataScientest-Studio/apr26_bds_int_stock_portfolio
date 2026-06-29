# F0 · Raw OHLCV (SOT)

The base of the DAG: the five channels plus the timestamp. Everything above is a causal function of these.

- Channels: `open`, `high`, `low`, `close`, `volume`.
- Index: `ts` (timestamp); bar index `t` is the ascending position (one continuous series per asset).
- Family: not assigned (F0 is the raw input, not a derived feature).
- No feature ids at F0 (the `f{stage}_…` grammar starts at F2; F1 is the time split).
- `prev_close = close[t−1]` is the only adjacent-bar reference F2 (atomic transforms) needs.
- Output: the raw OHLCV series → consumed by [F1](F1_time_split_eng.md) (the time split), then the feature Stages F2–F6.

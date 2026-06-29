# C00 · Setup & asset selection (scaffold)

The notebook header cell: choose the one asset, pin determinism, resolve paths, import the stack.

- Realizes: scaffold — no SOT Stage (the run harness for the whole go-through).
- Role: scaffold cell.
- Input: none (notebook entry point).
- Does:
  - set `SYMBOL` — one ticker from the 503-name universe (`A_Layers/config/universe_tickers.txt`); a single variable drives the whole notebook.
  - assert `SYMBOL` ∈ universe; fail fast otherwise.
  - set one global `SEED`; seed every RNG (numpy, xgboost, optuna sampler, torch if used).
  - resolve paths: raw OHLCV input, optional cross-check parquet, artifact output dir (see [README.md](README.md) → Notebook contract).
  - import the stack (pandas/numpy, xgboost, optuna, sklearn, pywt/torch as needed) and record versions for the C13 manifest.
- Produces: `SYMBOL`, `SEED`, resolved `paths`, `versions`.
- Guards: determinism is fixed here for the whole run (one seed → identical artifact), per [`00_leakage_contract_eng.md`](../ENG/Stages_Short_SOT/00_leakage_contract_eng.md) (Determinism).
- Check: `SYMBOL` is a valid universe member; `SEED` set before any stochastic call; all import versions captured.
- Output: `SYMBOL`, `SEED`, `paths`, `versions` → [C01](C01_f0_load_raw_ohlcv_eng.md).

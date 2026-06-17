# config/ — the configuration & build folder for Pipeline A

**Every input that parameterizes or feeds the Pipeline A build lives here, once.** Each file has a
single role; the role is also marked in the table below (a *mental model*, not a filename prefix).

| File | Category | Purpose | Edit policy |
|------|----------|---------|-------------|
| `params.json` | knobs (tunable) | Tunable design knobs for Pipeline A (timeframe, barrier mode, thresholds, train/OOS split dates, Optuna/XGBoost knobs, L8 quality gates). | Edit freely when tuning. Mirrored by `ENG/Layers_Short_SOT/00_parameters_eng.md`. |
| `numerical-amounts.json` | data (frozen) | Single source of truth for **frozen, observed** data-state numbers (counts and sizes derived from the source-data snapshot: universe size, ZIP inventory, row count, store sizes, candles per day, price scale). | Edit **only** when the underlying snapshot changes, then run the gate (below). Never hand-type these numbers anywhere else. |
| `universe.txt` | data (frozen) | The S&P 500 universe ticker list (one ticker per line); its line count *is* the universe size. | Regenerate from the snapshot; do not hand-edit ticker by ticker. |
| `numbers.py` | build (gate) | Generator + audit gate for the frozen numbers: renders them into the SOT / `README_A_Layer.md` / the viz, and fails on any drift or stray hand-typed literal. Pure standard library, no dependencies. | Edit only to change the generation / gate logic. |
| `na_allowlist.txt` | build (support) | Allowlist for `numbers.py check` — whitelists genuine non-data-state literal coincidences. Normally empty. | Add an entry only to whitelist a real false positive reported by `check`. |
| `main_data_flow.html.tmpl` | template | Source template for the 3D data-flow visualization; each frozen number is a `{{KEY}}` token. Rendered to `../viz/main_data_flow.html` by `numbers.py build`. | Edit the template; **never** the generated `viz/main_data_flow.html`. |

## Enforcement (single-source guarantee)

The frozen data-state numbers live **once** in `numerical-amounts.json`. Every other appearance is a
*generated region* — invisible HTML-comment `na:` markers in Markdown, and `{{KEY}}` tokens in the viz
template. Two commands keep that guarantee:

- `python3 config/numbers.py build` — re-render every marker and the viz from the registry (idempotent).
- `python3 config/numbers.py check` — audit gate: fails on drift or any stray hand-typed data-state
  literal. This is the only thing an audit needs to verify.

> Note: `check` scans **every** Markdown file under `A_Layers/` (including this one), so do not write
> raw data-state values in prose here — describe them by name (e.g. "universe size"), not by number.

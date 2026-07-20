# S&P 500 ML Indicator Study

One dedicated, sealed machine-learning ENTRY indicator per S&P 500 asset per model family —
XGBoost on 1-hour bars and an LSTM on daily bars, scored out-of-sample against buy-and-hold
with every read of that window counted — presented through a read-only Streamlit console.

## Architecture

```text
OHLCV (1h / 1d)
  -> features / sequences
  -> Train-only calibration (theta, trade floor, OOF operating point)
  -> XGB | LSTM  (sealed per-asset models)
  -> per-asset artifact  (strategy + manifest + parameters + metrics + interpretation)
  -> data/results.db  (SQLite, read-only)
  -> Streamlit console  (four pages)
```

## Quickstart

```bash
git clone --depth 1 --branch presentable_beta_version_of_liora_project \
  https://github.com/DataScientest-Studio/apr26_bds_int_stock_portfolio.git

cd apr26_bds_int_stock_portfolio

make verify     # optional, stdlib only: hashes, notebook parity, map figures
make setup
make on
```

The app serves on `http://localhost:8503`; `make off` stops it again (it kills only the
process listening on that port), and both accept `PORT=…` if 8503 is taken. The shallow clone is
~310 MB on disk — about 55 MB downloaded, the rest written at checkout, because every sealed
artifact travels with the repo (993 in this release: 498 XGB plus 495 LSTM over 498 tickers).
`make setup` installs the presentation dependencies (`streamlit`, `pandas`, `plotly`) plus
`anthropic`, used only by the optional Formular questionnaire on the Basket Simulator. No key is
needed to install, to run any page, to open the questionnaire or to run `make verify` — without
one the questionnaire opens and explains that its single API call is disabled (see
`.env.example`); nothing is trained, recomputed or written at runtime.

Do not take the numbers on trust: `make verify` needs no dependencies and no network, and runs
three stdlib-only gates. `verify_artifacts.py` recomputes the byte size and SHA-256 of the four
sealed files in each of the 993 artifact folders — the folder's own `manifest.json` is excluded
by construction, since it is what carries the digests — rebuilds each `folder_sha256` from those
digests, checks the manifest's count arithmetic, and confirms every sealed row resolves to a
folder the manifest knows. `verify_notebooks.py` re-checks that the two executed notebooks under
`examples/` still reproduce their sealed store rows to 1e-6. `verify_figures.py` recomputes every
store-derived figure the two pipeline maps assert, and fails if one has drifted.

## The two models

- **XGBoost (1h)** — per asset: engineered 1h features (with 1d/1w roll-ups), an ATR
  triple-barrier label, Train-only HPO and threshold calibration. The interpretation
  layer projects the sealed model into per-feature ENTRY value ranges (raw and in
  Train sigmas), each carrying the share of its ENTRY rows that ended net-profitable —
  the label is the sign of the realized net return after costs and the gapped fill,
  stricter than "TP before SL", which the store column `tp_before_sl_rate` misnames.
- **LSTM (1d)** — per asset: 60-session sequences of normalized daily state channels,
  deterministic CPU training warm-started from a universal backbone. The
  interpretation layer measures channel occlusion (ENTRY-conditioned vs global) and
  state-sequence trajectories.

Both models only decide ENTRY; take-profit and stop-loss are a mechanical ATR
triple-barrier contract. An asset with no robust Train operating point stays idle by
design. See `docs/METHODOLOGY.md`.

## The four pages

A flat sidebar, in reading order: how it was built, what came out, something to try, then
the procedure in full. Overview is the landing page.

1. **Data Flow 3D Visualization** — the build path drawn twice: the whole study as eight
   boxes, then the same path as a 2.5D canvas map — sixteen levels, both pipelines in one
   ladder, every contract a click away.
2. **Overview** — the whole result in one page. **Median outcomes**: median return against
   each model's own buy-and-hold, how many assets beat it, median profit factor and its
   coverage. **Feature Logic**: which features one asset's sealed XGB model leans on, as a
   share of its split total-gain (Train-derived interpretation). **Model Comparison**: four
   charts — return, profit factor, trades, beats-HODL share.
3. **Basket Simulator** — pick assets, by a random draw, the questionnaire adviser or by
   hand, and read what the sealed models did with them against the same basket simply
   held. Three numbers, never one: the executed path, the model result, and the
   price-only benchmark.
4. **Data Pipeline Lego Plan** — the procedure as an 18-brick ladder: contract, reasoning
   and lesson per brick, with the layer id the code uses (XGB L4-L9, LSTM D1-D9).

## Repository structure

```text
app.py            Streamlit entry point (four pages under app/pages/, flat sidebar)
app/              console code; app/data.py is the only console module opening the database
                  (the three scripts/ verifiers open it read-only too)
app/formular/     optional questionnaire add-on; own README.md, removable with one git rm -r
src/xgb/          XGB research code (pipeline L4-L9, feature search, artifact writers)
src/lstm/         LSTM research code (pipeline D1-D6, model D7-D8, feature search)
src/shared/       contracts shared by both pipelines (op_select, golden_calibration,
                  interpretation)
config/           frozen configuration the code reads
artifacts/        sealed per-asset artifacts (xgb/<T>/, lstm/<T>/) + manifest.json
data/results.db   sealed SQLite results store (read-only)
examples/         two executed notebooks for one asset (NVDA), one per model:
                  Example_XGB.ipynb (L4→L9) and Example_LSTM.ipynb (D2→D9)
scripts/          the offline verifiers behind `make verify`: artifact hashes, the
                  notebooks' parity with the store, and the maps' asserted figures
docs/             METHODOLOGY.md, ARCHITECTURE.md
docs-facts-infos/ written audits: OHLCV data, methodological integrity,
                  and the research-consistency report
.env.example      how to supply ANTHROPIC_API_KEY for the optional Formular; nothing else
                  in the console reads a key
data_pipeline_lego_plan.html   standalone 18-brick pipeline map (embedded by the Lego Plan page)
data_flow_3d_visualization.html  standalone 2.5D build-path map (embedded by the 3D Visualization page)
```

The code under `src/` is the real research code that produced and describes the sealed
artifacts: both pipelines, the feature searches, the artifact writers and the shared
contracts, unmodified and readable. The acquisition and orchestration layer around it —
bar loading with the corporate-action correction, the per-asset runner, the compute-run
harness — stays on the research branch, together with the raw bar stores and the training
stack (`torch`, `xgboost`, `optuna`, `duckdb`). So `src/` is here to be read and audited,
not to re-run the universe; what you can re-verify on this branch is the artifact tree
(`make verify`) and the two executed notebooks under `examples/`, one per model on the
same ticker.

## Limitation

All results are historical out-of-sample reads of sealed models over fixed windows — every OOS
read is counted in an append-only ledger. They are research output — not live trading and not
investment advice. The interpretation layer is Train-derived and must not be read as an OOS
result.

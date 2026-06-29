# liora-project-ml-engineering — minimalny pipeline ML (S&P 500, per-asset)

Minimalistyczny, samodzielny i reprodukowalny pipeline tradingowy ML: dla wybranego tickera
liczy warstwy **1.6 → 4.2** w jednym notebooku i zostawia w `Assets/<TICKER>/` dokładnie
**7 plików** deliverable. Bez SHA / sum kontrolnych / nadmiernych bramek QC / kontraktów /
testów — wszystko ma być czytelne i łatwe do wytłumaczenia.

## 3 filary

- **`Plan/`** — **wizualizacja**: statyczna historia pipeline'u (`index.html` → `main_data_flow.html`,
  `configurations.html`, `glossary.html`). Pokazuje wyłącznie warstwy, które kod naprawdę liczy
  (1.6 → 4.2).
- **`Project/`** — projekt roboczy:
  - `Structure/` — operacyjny root: `pipeline.py` (warstwy 1.6–4.2), `notebook_template.ipynb`
    (per-asset runner), `build_db.py`, `run_asset.py`, `config/`, `Features/`, `data/seed/`,
    `Assets/` (na starcie pusty), `Makefile`, `requirements.txt`.
  - `endproduct/` — mirror SOT (`Layers_Short_SOT/` dla zaimplementowanych warstw) + symlink do `Assets/`.
- **`Archive/`** — zamrożony materiał: `old-capstone-2026-06-29/` (poprzedni projekt DuckDB/Streamlit
  „Stocks Recommender” + jego Plan SOT), plus wcześniejsze `runs/` i `experiments/`.
- **`Formalities/`** — sprawy kursowe (Timeline, audyt danych, rendery) — bez zmian.

## 7 plików per asset (`Project/Structure/Assets/<TICKER>/`)

1. `<TICKER>__Layer1_6_to_Layer4_2.ipynb` — wykonana kopia notebooka-runnera
2. `<TICKER>_ohlcv_1h.parquet` — czyste 1h OHLCV (Layer 1.6)
3. `<TICKER>_ohlcv_1d.parquet` — zmaterializowane 1d
4. `<TICKER>_ohlcv_1w.parquet` — zmaterializowane 1w
5. `OPTUNAs_XGB_HPOs_best_params.json` — najlepsze hiperparametry (Layer 3.1)
6. `strategy_<TICKER>.py` — samodzielny artefakt strategii (model base64 + selfcheck)
7. `<TICKER>_README.md` — podsumowanie OOS + ścieżka kapitału + ledger transakcji

## Quickstart

```bash
cd Project/Structure
make deps          # instalacja requirements.txt do ../.venv
make build-db      # data/seed/*.parquet -> liora.duckdb
make run-asset TICKER=AAPL   # uruchamia notebook -> Assets/AAPL/ (7 plików)
make serve         # statyczna wizualizacja: http://localhost:8000/index.html
```

Uniwersum rozszerzasz przez dorzucenie kolejnego `data/seed/<TICKER>_ohlcv_1h.parquet`
i `make build-db`. `Assets/` startuje pusty — to użytkownik decyduje, ile assetów utworzy.
Pipeline jest deterministyczny (`seed_everything`, `XGBOOST_N_JOBS=1`), więc wyniki OOS są
reprodukowalne.

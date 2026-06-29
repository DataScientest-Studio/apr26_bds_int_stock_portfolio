# endproduct — SOT + finalne deliverable

Ten folder to **prezentacja i źródło prawdy (SOT)** projektu: zwięzła dokumentacja warstw +
dowiązanie do realnych deliverable. Bez raportów PDF, bez screenshotów.

- [`Layers_Short_SOT.md`](Layers_Short_SOT.md) — zwięzły opis akwizycji danych (1.3–1.5) + 9 zaimplementowanych
  warstw (1.6 → 4.2) i kontrakt 7 plików per asset.
- `Assets/` — symlink do `../Structure/Assets/` (deliverable każdego assetu, tworzone przez `make run-asset`).
- `main_data_flow.html` — symlink do wizualizacji w [`Plan/`](../../Plan/main_data_flow.html).

## Kontrakt 7 plików (`Assets/<TICKER>/`)

| # | Plik | Warstwa | Treść |
|---|------|---------|-------|
| 1 | `<T>__Layer1_6_to_Layer4_2.ipynb` | 4.2 | wykonana kopia notebooka-runnera |
| 2 | `<T>_ohlcv_1h.parquet` | 1.6 | czyste 1h OHLCV |
| 3 | `<T>_ohlcv_1d.parquet` | 1.6 | zmaterializowane 1d |
| 4 | `<T>_ohlcv_1w.parquet` | 1.6 | zmaterializowane 1w |
| 5 | `OPTUNAs_XGB_HPOs_best_params.json` | 3.1 | najlepsze hiperparametry + manifest cech |
| 6 | `strategy_<T>.py` | 3.2 | samodzielny artefakt strategii (model base64 + selfcheck) |
| 7 | `<T>_README.md` | 4.2 | raport OOS: ścieżka kapitału + tabela cech + ledger transakcji |

Akwizycja danych (proweniencja, **upstream — nie kod tego repo**): surowe 1h OHLCV pobrano z **Alpaca**
(`feed=sip`, 1.3), trzymano w formacie **QuantConnect / LEAN** zip i wyeksportowano do
`data/seed/*_ohlcv_1h.parquet` (1.4). Wejście repo (**1.5**): `build_db.py` ładuje te parquety →
`liora.duckdb` (tabela `bars_1h`) — wspólny input; bez live-fetcha. 1.5 nie tworzy plików-deliverable;
powyższe 7 plików produkują warstwy 1.6–4.2.

Wynik jest deterministyczny (`RANDOM_SEED=42`, `XGBOOST_N_JOBS=1`) i reprodukowalny przy
przypiętych wersjach z `Project/Structure/requirements.txt`.

# Layers Short SOT — akwizycja danych (1.3–1.5) + 9 warstw (1.6 → 4.2)

Źródło prawdy dla zaimplementowanego pipeline'u. Runner-notebook (`notebook_template.ipynb`,
uruchamiany przez `run_asset.py`) wykonuje warstwy 1.6 → 4.2 po kolei dla jednego tickera; krok
wejściowy 1.5 (`build_db.py`) buduje wspólny input wcześniej, jednorazowo (`make build-db`).
Warstwy **1.3–1.4 to proweniencja danych (upstream) — NIE kod tego repo**: pokazują, skąd wzięły się
parquety w `data/seed/` (wizualizacja zaczyna się od pobrania danych, nie z pustego miejsca).
Cała matematyka jest w `Project/Structure/pipeline.py`; zapis 3 plików-deliverable w `asset_writers.py`.

## Sekcja Data

### 1.3 — Akwizycja: Alpaca (proweniencja, upstream)
Surowe 1h OHLCV pobrano z **Alpaca Market Data API** (`feed=sip`) **upstream / offline — nie przez to
repo**. To repo jest samowystarczalne: nie woła API na żywo, nie ma klucza ani kodu pobierania —
wozi gotowe parquety. Warstwa pokazana w wizualizacji jako pochodzenie danych.

### 1.4 — Archiwum: QuantConnect / LEAN → eksport do data/seed (proweniencja, upstream)
Surowe OHLCV trzymano w formacie **QuantConnect / LEAN** (1 zip = 1 ticker), po czym **wyeksportowano
jednorazowo** do `data/seed/<TICKER>_ohlcv_1h.parquet` — czyli dokładnie do plików, które wozi to repo.
Również proweniencja (upstream), nie kod tego repo.

### 1.5 — Źródło danych w repo (build_db.py)
`build_db.py` (krok operacyjny `make build-db`, **poza** `pipeline.py`) ładuje surowe 1h OHLCV
z `data/seed/*_ohlcv_1h.parquet` do `liora.duckdb` — jednej tabeli `bars_1h(ticker, timestamp,
open, high, low, close, volume)`. To wspólny input pipeline'u; **nie** produkuje plików-deliverable
(7 plików powstaje w warstwach 1.6 → 4.2). Uniwersum rozszerzasz, dorzucając kolejny
`data/seed/<TICKER>_ohlcv_1h.parquet` i uruchamiając `make build-db`.

### 1.6 — Snapshot → czyste OHLCV (+ roll-up 1d/1w)
`layer1_6_snapshot_to_parquet(db, ticker, out)` czyta `bars_1h` z `liora.duckdb`, **fail-closed**
weryfikuje kontrakt czystego OHLCV (brak NaN/duplikatów/niemonotoniczności, inwarianty świecy:
`high≥low`, `high≥max(o,c)`, `low≤min(o,c)`, wolumen ≥ 0) i zapisuje `<T>_ohlcv_1h.parquet` (#2).
`layer1_6_materialize_timeframes(...)` rolluje 1h → 1d (dzień ET) i 1w (tydzień ISO),
zapisując `<T>_ohlcv_1d.parquet` (#3) i `<T>_ohlcv_1w.parquet` (#4). To jedyna „bramka”, jaka została.

### 1.7 — Podział czasu
`layer1_7_split(df)` → maski warmup / Train / OOS po datach (`config splits`) + purge (`H`=24 barów)
i embargo (`EMBARGO_BARS`=35), żeby okno wyniku etykiety nie nachodziło na szew Train→OOS.

## Sekcja Signal

### 2.1 — Detektor setupów
`layer2_1_detect(df, mask)` — przyczynowe dopasowanie linii trendu na pivotach → kandydaci
long/short. DET-09 odrzuca zdegenerowane / zero-ATR setupy.

### 2.2 — Cechy X + etykieta Y (Output-B)
8 standardowych cech trendline (FT1–FT8) + etykieta triple-barrier `TB_v1.2` (cel / linia
bezpieczeństwa / brak w horyzoncie `H`) → macierz **Output-B**. Etykiety rozwiązują się wewnątrz
Train przez purge.

### 2.3 — Per-asset selekcja cech
`resolve_feature_manifest(ticker)` ustala efektywny manifest cech: domyślnie zestaw 1h
(FT1–FT8 + `log_return_5` = 9 kolumn), opcjonalnie + przyczynowy kontekst 1d/1w per asset
(np. AAPL dokłada blok 1d → 18 kolumn X). Rejestry cech w `Features/features_{1h,1d,1w,between_timeframes}/`.

## Sekcja Training

### 3.1 — Optuna HPO
`layer3_1_optuna(...)` — TPE + MedianPruner na purged walk-forward CV (4 foldy), `N_TRIALS`=200,
maksymalizacja AUC-PR **tylko na Train**. Zapis `OPTUNAs_XGB_HPOs_best_params.json` (#5).

### 3.2 — Strategia XGBoost
`layer3_2_train(...)` trenuje finalny model XGBoost (meta-label) na pełnym Train; akceptacja Train
liczona tym samym silnikiem co OOS. `strategy_meta(...)` + `asset_writers.write_strategy(...)`
zapisują samodzielny `strategy_<T>.py` (#6) z modelem base64 + `selfcheck()`.

## Sekcja OOS + endproduct

### 4.1 — Werdykt OOS
`layer2_1_detect` na masce OOS → `score_setups` modelem z RAM → `run_engine(...)`: jednorazowy
przebieg out-of-sample przez silnik Risk-Box (all-in compounding, jedna pozycja na asset,
symetryczny target/safety, zaplanowane wyjścia). Ten sam `run_engine` liczy akceptację Train i OOS.
Wynik OOS (PF · MDD · WR · trades · …) jest zapisywany do **`oos_metrics.db`**
(`asset_writers.write_oos_metrics`, stdlib `sqlite3`, UPSERT po tickerze) — minimalny magazyn wyników
(TYLKO kolumny OOS, bez contract/lineage/source-QC), który zasila **Dashboard** (`Plan/dashboard.html`;
`make dashboard` eksportuje `oos_metrics.db` → `Plan/data/dashboard.json`). `oos_metrics.db` żyje
w `Structure/` (NIE w `Assets/`) — kontrakt 7 plików nietknięty.

### 4.2 — Endproduct
`asset_writers.write_readme(...)` zapisuje `<T>_README.md` (#7): ścieżka kapitału + tabela cech +
ledger Risk-Box. Następnie `run_asset.py` zapisuje wykonaną kopię notebooka (#1) i sprawdza
kontrakt 7 plików.

## Czego tu NIE ma (świadomie usunięte)
Brak SHA/lineage, planu kontraktów (Layer 0.1), `source_ingest`/DAT, feature-catalog lock,
deployment-authorization, frozen-numbers i contract-crossmatch. Jedyne kontrole to fail-closed
higiena OHLCV w 1.6, walidacja parametrów w 00, `selfcheck()` strategii i sprawdzenie 7 plików.

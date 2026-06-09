# flak92 — TASKS / notatki (prywatne, poza git)

## Decyzja (zmiana 2026-05-21): dane przez yfinance, Alpaca do porównania

Główna akwizycja: **yfinance / Yahoo Finance** (`fetch_data.py`, już w repo).
Powód zmiany — uniwersum projektu to **S&P 500 + DAX 40**, a:
- **yfinance pokrywa OBA** (US + DE), Alpaca to broker US → **DAX 40 niedostępny**.
- yfinance: głębsza historia, Adj Close od ręki, bez klucza, jeden tool na całość.
- Alpaca/LEAN **zostaje** jako drugie źródło — robimy **porównanie jakości** (oba raw daily).

Ścieżka QuantConnect/Alpaca miała sens pod „dane + silnik w jednym" (backtest/live
w LEAN), ale ten recommender liczy metryki ryzyka i potrzebuje DAX → yfinance wygrywa.

## Zasady

- **KISS.** Prosto i optymalnie, ale docelowo (do dalszego użytku), nie „na zaliczenie".
- **Nie wynajdujemy już rozwiązanych problemów.**
- Mamy **dwa store'y obok siebie** (yfinance + Alpaca) celowo — do porównania.

## Stan — ZROBIONE (2026-05-21)

**Store yfinance** (główny) — `data/ohlcv_daily_sp500_dax40_yfinance.duckdb` (~70 MB, gitignore):
- [x] `fetch_data.py --years 10` → 543 tickery (503 SP500 + 40 DAX40), 0 nieudanych.
- [x] `build_yfinance_duckdb.py` → tabele:
      `ohlcv_daily(ticker, date, open, high, low, close, adj_close, volume, "index")`
      (1 329 357 wierszy, 2016-05 → 2026-05, raw close + adj_close; NaN→NULL, wierszy nie usuwamy),
      `tickers(...,"index",...)`, `_meta(source, source_note, built_at)`.

**Store Alpaca** (do porównania) — `data/ohlcv_daily_sp500.duckdb` (~35 MB, gitignore):
- [x] Daily S&P 500 przez Alpaca/LEAN (0 QCC, feed IEX, 2016-01 →). `build_sp500_duckdb.py`
      (dodane `_meta`). 1 268 575 wierszy, 503 symbole. Tabele `ohlcv_daily(symbol,...)`, `constituents`.

**Dashboard porównawczy** — `dashboard.py` → `dashboard.html` (retro HTML, stdlib+duckdb,
**po angielsku**). ATTACH obu duckdb, **side-by-side yfinance vs Alpaca**, **podział per indeks**:
- [x] **S&P 500**: OVERVIEW (oba źródła obok siebie) + **SOURCE DIVERGENCE** (overlap symboli,
      rozjazd raw close: median/p99/max |rel diff|, przykłady AAPL/MSFT/NVDA dzień w dzień) +
      UNIVERSE (sektory) + EXAMPLE (yfinance, z adj_close) + TICKERS side-by-side (rows/range per źródło).
- [x] **DAX 40**: tylko yfinance, jawnie **Alpaca = N/A**.
- [x] Kalendarz handlowy liczony **per (indeks, źródło)** (NYSE vs XETRA → różne dni).
- [x] Graceful: brak jednego duckdb → render drugiego bez crasha.

**Pierwsze wnioski z porównania:** overlap 503/503; **median |diff| = 0%** (źródła zgadzają się
w typowy dzień), ale **p99 ~95% / max ~400%** → splity/edge-case'y liczone inaczej (do zbadania).

### Jak odtworzyć / odświeżyć

```bash
cd /opt/to_liora_school/liora-project-ml-engineering

# (raz) srodowisko
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt

# 1) yfinance: pobranie + build (glowne zrodlo, SP500+DAX40)
./.venv/bin/python fetch_data.py --years 10        # ~10-15 min, Yahoo throttluje; smoke: --limit 20
./.venv/bin/python build_yfinance_duckdb.py

# 2) Alpaca: do porownania (S&P 500, w workspace LEAN /opt/qc) — patrz flak92_README.md
./.venv/bin/python build_sp500_duckdb.py

# 3) dashboard porownawczy
./.venv/bin/python dashboard.py                    # -> dashboard.html
./.venv/bin/python dashboard.py --serve            # live :8000 (auto-refresh 30s)
#   flagi: --yf-db / --alpaca-db (dziala tez z jednym zrodlem)
```

> yfinance free = feed Yahoo (skonsolidowane), raw close + adj_close, historia dekady.
> Alpaca free = feed IEX (jedna gielda), raw, ~2016+.

## TODO (dalej)

- [ ] Zbadać rozjazd p99/max yfinance vs Alpaca (splity? daty korekt?).
- [ ] Feature engineering / model ML (recommender) na `ohlcv_daily` (SP500 + DAX40).
- [ ] (opcjonalnie) korekty split/dividend, jeśli model tego wymaga (yfinance ma `adj_close`).

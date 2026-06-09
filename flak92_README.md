# flak92_README — jak tego używać (prywatne, poza git)

Konkretne komendy do kopiowania. Decyzje/uzasadnienia → `flak92_TASKS.md`.

Dwa store'y daily (do porównania):
- **yfinance** (główny, S&P 500 **+ DAX 40**, raw close + adj_close, ~2016→dziś)
  → `data/ohlcv_daily_sp500_dax40_yfinance.duckdb`
- **Alpaca** (porównanie, tylko S&P 500, feed IEX, raw, ~2016→dziś)
  → `data/ohlcv_daily_sp500.duckdb`

---

## TL;DR — wszystko od zera

```bash
cd /opt/to_liora_school/liora-project-ml-engineering

# (raz) srodowisko
python3 -m venv .venv && ./.venv/bin/pip install -r requirements.txt

# 1) yfinance (glowne zrodlo: SP500 + DAX40)
./.venv/bin/python fetch_data.py --years 10        # ~10-15 min; smoke: --limit 20
./.venv/bin/python build_yfinance_duckdb.py

# 2) Alpaca (do porownania: S&P 500) — pobranie w workspace LEAN /opt/qc, 0 QCC
cd /opt/qc && rm -f data/equity/usa/daily/*.zip
TICKERS=$(tail -n +2 /opt/to_liora_school/liora-project-ml-engineering/sp500_constituents.csv | cut -d, -f1 | paste -sd,)
lean data download --data-provider-historical Alpaca --alpaca-environment paper \
  --security-type Equity --data-type Trade --resolution Daily \
  --market usa --ticker "$TICKERS" --start 20160101 --end 20260520
cd /opt/to_liora_school/liora-project-ml-engineering && ./.venv/bin/python build_sp500_duckdb.py

# 3) dashboard porownawczy
./.venv/bin/python dashboard.py
```

---

## Dashboard (porównawczy yfinance vs Alpaca)

Statyczny plik `dashboard.html`:

```bash
cd /opt/to_liora_school/liora-project-ml-engineering
./.venv/bin/python dashboard.py
xdg-open dashboard.html        # lub otworz recznie
```

Live (serwer http, auto-odświeżanie 30 s, czyta DB na żywo):

```bash
./.venv/bin/python dashboard.py --serve            # http://localhost:8000
./.venv/bin/python dashboard.py --serve --port 9000
```

Flagi źródeł (działa też z jednym store'em):

```bash
./.venv/bin/python dashboard.py --yf-db data/ohlcv_daily_sp500_dax40_yfinance.duckdb \
                                --alpaca-db data/ohlcv_daily_sp500.duckdb
```

Układ (HTML po angielsku), **wyraźny podział per indeks**:
- **S&P 500** — OVERVIEW oba źródła obok siebie · **SOURCE DIVERGENCE** (overlap symboli,
  rozjazd raw close: median/p99/max, przykłady AAPL/MSFT/NVDA dzień w dzień) · UNIVERSE
  (sektory GICS) · EXAMPLE (yfinance, z `adj_close`) · TICKERS side-by-side (rows/range per źródło).
- **DAX 40** — tylko yfinance (Alpaca = N/A).
- Kalendarz handlowy liczony osobno per (indeks, źródło) → NYSE ≠ XETRA.

---

## Odświeżenie danych (forward-fill)

```bash
cd /opt/to_liora_school/liora-project-ml-engineering
# yfinance:
./.venv/bin/python fetch_data.py --years 10 && ./.venv/bin/python build_yfinance_duckdb.py
# Alpaca (zmien --end na dzis):
cd /opt/qc && rm -f data/equity/usa/daily/*.zip
TICKERS=$(tail -n +2 /opt/to_liora_school/liora-project-ml-engineering/sp500_constituents.csv | cut -d, -f1 | paste -sd,)
lean data download --data-provider-historical Alpaca --alpaca-environment paper \
  --security-type Equity --data-type Trade --resolution Daily \
  --market usa --ticker "$TICKERS" --start 20160101 --end $(date +%Y%m%d)
cd /opt/to_liora_school/liora-project-ml-engineering && ./.venv/bin/python build_sp500_duckdb.py
```

---

## Zapytania do DuckDB (store yfinance)

REPL:

```bash
./.venv/bin/python -c "import duckdb; duckdb.connect('data/ohlcv_daily_sp500_dax40_yfinance.duckdb', read_only=True).sql(\"SELECT * FROM ohlcv_daily WHERE ticker='AAPL' ORDER BY date DESC LIMIT 5\").show()"
```

Przykłady SQL:

```sql
-- tylko DAX 40
SELECT * FROM ohlcv_daily WHERE "index"='DAX40' AND ticker='SAP.DE' ORDER BY date DESC LIMIT 10;

-- dzienne zwroty + 20d SMA (na adj_close, feature ML)
SELECT date,
       adj_close/LAG(adj_close) OVER(PARTITION BY ticker ORDER BY date)-1 AS ret,
       AVG(adj_close) OVER(PARTITION BY ticker ORDER BY date ROWS 19 PRECEDING) AS sma20
FROM ohlcv_daily WHERE ticker='AAPL' ORDER BY date;

-- join z sektorem + filtr indeksu
SELECT o.ticker, t.sector, o.date, o.close
FROM ohlcv_daily o JOIN tickers t USING(ticker)
WHERE o."index"='SP500' AND o.date='2026-05-20';

-- porownanie zrodel: ATTACH obu i diff raw close (jak w dashboardzie)
ATTACH 'data/ohlcv_daily_sp500.duckdb' AS alp (READ_ONLY);
SELECT y.ticker, y.date, y.close yf, a.close alpaca
FROM ohlcv_daily y JOIN alp.ohlcv_daily a
  ON replace(replace(upper(y.ticker),'.',''),'-','')=replace(replace(upper(a.symbol),'.',''),'-','')
 AND y.date=a.date
WHERE y.ticker='AAPL' ORDER BY y.date DESC LIMIT 5;
```

Tabele yfinance: `ohlcv_daily(ticker, date, open, high, low, close, adj_close, volume, "index")` ·
`tickers(ticker, name, sector, industry, "index", country)` · `_meta`.
Tabele Alpaca: `ohlcv_daily(symbol, date, open, high, low, close, volume)` · `constituents` · `_meta`.

---

## Uwagi

- Oba store'y = **raw/unadjusted** close → skoki>50% w dashboardzie to realne splity.
  yfinance ma dodatkowo `adj_close` (split/div) — używaj go do zwrotów/metryk.
- **Match tickerów** yfinance↔Alpaca: `BRK-B`↔`BRK.B` (kanon: upper bez `.`/`-`). DAX (`.DE`) jest tylko w yfinance.
- yfinance = feed Yahoo (skonsolidowany), bez klucza. Alpaca = feed IEX, klucz w `/opt/qc/lean.json`, 0 QCC.
- Pierwsze porównanie: median |diff| 0% (zgoda), ale p99/max duże (splity/edge — do zbadania).

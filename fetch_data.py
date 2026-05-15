"""Fetch historical OHLCV (Open/High/Low/Close/Volume) data for S&P 500
and DAX 40 constituents from Yahoo Finance via the yfinance library.

This script powers the data-acquisition step of the Liora Stock portfolio
recommender. The downloaded prices feed the clustering / return-ranking /
recommendation pipeline described in README.md.

Outputs (written under ./data/):
    - tickers.csv                    : metadata for every ticker
                                       (ticker, name, sector, industry, index, country)
    - prices_long.csv                : one row per (date, ticker) — best format for
                                       feature engineering (groupby ticker, rolling
                                       windows, etc.)
    - prices_close_wide.csv          : wide-format adjusted close, one column per ticker
                                       — best format for correlation matrices, returns,
                                       Sharpe ratio calculations
    - by_ticker/SP500/{TKR}.csv      : individual OHLCV file per S&P 500 ticker
    - by_ticker/DAX40/{TKR}.csv      : individual OHLCV file per DAX 40 ticker
    - failed_tickers.csv             : list of tickers that could not be downloaded
                                       (only written if at least one failed)

Usage:
    python fetch_data.py                  # full run with default 5-year window
    python fetch_data.py --years 10       # download 10 years of history
    python fetch_data.py --years 3        # change history window
    python fetch_data.py --limit 20       # smoke test using only the first 20 tickers
    python fetch_data.py --batch-size 25  # smaller batches if network is flaky
"""

# `from __future__ import annotations` lets us use modern type-hint syntax
# (e.g. `list[str]`, `X | None`) even on older Python versions.
from __future__ import annotations

import argparse  # parses --years / --limit / --batch-size from the command line
import io        # wraps the HTML string returned by `requests` so pandas can read it
import time      # short sleeps between batches so we don't hammer Yahoo's endpoint
from pathlib import Path

import pandas as pd   # data wrangling
import requests       # used only to fetch Wikipedia HTML with a real browser User-Agent
import yfinance as yf # actual Yahoo Finance client


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# All outputs land in ./data/ next to this script (works regardless of CWD).
DATA_DIR = Path(__file__).parent / "data"

# Wikipedia pages we scrape for the constituent lists. The S&P 500 page has
# a single canonical table at index 0; the DAX page has several tables, so
# we have to find the right one programmatically (see get_dax40_tickers).
SP500_WIKI = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
DAX40_WIKI = "https://en.wikipedia.org/wiki/DAX"

# Wikipedia blocks Python's default urllib User-Agent with HTTP 403, so we
# pretend to be a regular Chrome browser when requesting the pages.
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"


# ---------------------------------------------------------------------------
# Wikipedia scraping helpers
# ---------------------------------------------------------------------------

def _read_wiki_tables(url: str) -> list[pd.DataFrame]:
    """Fetch a Wikipedia page and return every HTML <table> found on it as a
    list of pandas DataFrames. We use `requests` (with a browser UA) instead of
    passing the URL directly to `pd.read_html`, because pandas uses urllib
    under the hood and Wikipedia 403s the default urllib UA."""
    resp = requests.get(url, headers={"User-Agent": UA}, timeout=30)
    resp.raise_for_status()  # raise if Wikipedia returned 4xx/5xx
    return pd.read_html(io.StringIO(resp.text))


def get_sp500_tickers() -> pd.DataFrame:
    """Return a DataFrame of S&P 500 constituents with columns:
    ticker, name, sector, industry, index, country."""
    tables = _read_wiki_tables(SP500_WIKI)

    # The first table on the page is the constituent list.
    df = tables[0][["Symbol", "Security", "GICS Sector", "GICS Sub-Industry"]].copy()
    df.columns = ["ticker", "name", "sector", "industry"]

    # Yahoo Finance uses '-' instead of '.' for class-share tickers
    # (e.g. Wikipedia says "BRK.B", but Yahoo expects "BRK-B").
    df["ticker"] = df["ticker"].str.replace(".", "-", regex=False)

    # Tag rows so we can later split outputs per index.
    df["index"] = "SP500"
    df["country"] = "US"
    return df


def get_dax40_tickers() -> pd.DataFrame:
    """Return a DataFrame of DAX 40 constituents with columns:
    ticker, name, sector, industry, index, country."""
    tables = _read_wiki_tables(DAX40_WIKI)

    # The DAX page has multiple tables (historical composition, sub-indices, ...).
    # Pick the first one whose columns include both "ticker" and a name/company column.
    for t in tables:
        cols = {c.lower() for c in t.columns.astype(str)}
        if "ticker" in cols and any("company" in c.lower() or "name" in c.lower() for c in t.columns):
            df = t.copy()
            break
    else:
        raise RuntimeError("Could not locate DAX 40 constituents table on Wikipedia.")

    # Lowercase columns so the rest of the function doesn't care about exact casing.
    df.columns = [str(c).strip().lower() for c in df.columns]
    name_col = next(c for c in df.columns if "company" in c or c == "name")
    sector_col = next((c for c in df.columns if "sector" in c or "industry" in c.lower()), None)

    def _normalize(t: str) -> str:
        """Append the Frankfurt exchange suffix `.DE` only if no suffix is already
        present. Wikipedia now lists DAX tickers with their suffix included
        (e.g. `SAP.DE`), and Airbus appears as `AIR.PA` (Paris). Blindly appending
        `.DE` would produce `SAP.DE.DE` and `AIR.PA.DE`, both of which Yahoo rejects."""
        t = t.strip()
        return t if "." in t else f"{t}.DE"

    out = pd.DataFrame({
        "ticker": df["ticker"].astype(str).map(_normalize),
        "name": df[name_col].astype(str).str.strip(),
        # DAX Wikipedia table often only has a single sector/industry column;
        # we duplicate it into both fields for schema consistency with S&P 500.
        "sector": df[sector_col] if sector_col else "Unknown",
        "industry": df[sector_col] if sector_col else "Unknown",
    })
    out["index"] = "DAX40"
    out["country"] = "DE"
    return out


# ---------------------------------------------------------------------------
# Price download (the heavy bit)
# ---------------------------------------------------------------------------

def _download_one(tkr: str, period: str) -> pd.DataFrame | None:
    """Download history for a single ticker. Used as a fallback when a batch
    fetch returns no data for a given ticker. Returns None on failure so the
    caller can record the ticker as failed without an exception."""
    try:
        df = yf.download(
            tkr,
            period=period,
            interval="1d",
            auto_adjust=False,   # keep raw OHLC + a separate Adj Close column
            threads=False,       # avoid yfinance's internal SQLite cache race
            progress=False,      # no progress bars in script output
        )
    except Exception:
        return None
    if df is None or df.empty:
        return None
    # Single-ticker downloads sometimes still return MultiIndex columns
    # (e.g. ('Close', 'AAPL')). Flatten to a simple Index for consistency.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df.dropna(how="all")  # drop rows where every column is NaN


def download_prices(tickers: list[str], years: int, batch_size: int = 50) -> tuple[pd.DataFrame, list[str]]:
    """Download `years` of daily OHLCV history for every ticker, in batches.

    Strategy:
    1. Send `batch_size` tickers per yfinance call. This is much faster than
       hitting Yahoo once per ticker, but a single bad ticker won't poison
       the whole batch.
    2. For any ticker whose batch slot came back empty, retry it individually
       (slower but more reliable).
    3. Return both the assembled price DataFrame and the list of tickers
       that still failed after retry — those go into failed_tickers.csv.
    """
    period = f"{years}y"                             # yfinance accepts strings like "5y", "10y"
    frames: list[pd.DataFrame] = []                  # collected per-ticker DataFrames
    failed: list[str] = []                           # tickers that failed even after retry
    n_batches = -(-len(tickers) // batch_size)       # ceiling division for progress display

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        print(f"  batch {i // batch_size + 1}/{n_batches} ({len(batch)} tickers)…")

        # ---- Step 1: try fetching the whole batch in one yfinance call ----
        try:
            data = yf.download(
                batch,
                period=period,
                interval="1d",
                auto_adjust=False,
                group_by="ticker",   # result is keyed by ticker symbol
                threads=False,       # see _download_one — avoids the SQLite cache race
                progress=False,
            )
        except Exception as e:
            # Network glitch, throttling, etc. — fall through to per-ticker retry.
            print(f"    batch failed wholesale: {e!s}; will retry tickers one by one")
            data = None

        # ---- Step 2: pull each ticker out of the batch result; queue empties for retry ----
        retry_list: list[str] = []
        if data is None:
            # Whole batch failed → retry every ticker individually below.
            retry_list = list(batch)
        else:
            for tkr in batch:
                try:
                    # When the batch has >1 ticker, `data` is a MultiIndex-columned DataFrame
                    # keyed by ticker. When the batch has exactly 1 ticker, `data` is already
                    # flat — handle both shapes.
                    df = data[tkr].dropna(how="all") if len(batch) > 1 else data.dropna(how="all")
                except KeyError:
                    retry_list.append(tkr)
                    continue
                if df.empty:
                    retry_list.append(tkr)
                    continue
                df = df.reset_index().rename(columns=str.lower)
                df["ticker"] = tkr
                frames.append(df)

        # ---- Step 3: per-ticker retry pass for anything the batch didn't return ----
        for tkr in retry_list:
            time.sleep(0.5)   # tiny pause so we don't hammer Yahoo when retrying
            df = _download_one(tkr, period)
            if df is None:
                failed.append(tkr)
                continue
            df = df.reset_index().rename(columns=str.lower)
            df["ticker"] = tkr
            frames.append(df)

        time.sleep(1)   # be polite between batches

    # If nothing came back at all, return empty — caller decides whether to bail.
    if not frames:
        return pd.DataFrame(), failed

    # ---- Step 4: assemble the master long-format DataFrame ----
    prices = pd.concat(frames, ignore_index=True)
    keep = ["date", "ticker", "open", "high", "low", "close", "adj close", "volume"]
    prices = prices[[c for c in keep if c in prices.columns]]
    # Rename "adj close" → "adj_close" so it's a valid Python identifier
    # (easier to use in `df.adj_close` notation, less error-prone in code).
    prices = prices.rename(columns={"adj close": "adj_close"})
    return prices, failed


# ---------------------------------------------------------------------------
# Main entry point: parse args, run the pipeline, write CSVs.
# ---------------------------------------------------------------------------

def main() -> None:
    # CLI flags — `--years 10` for a 10-year history, `--limit 20` for a smoke test, etc.
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--years", type=int, default=5, help="history window in years (default: 5)")
    parser.add_argument("--limit", type=int, default=None, help="cap number of tickers (smoke test)")
    parser.add_argument("--batch-size", type=int, default=50, help="tickers per yfinance batch")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)

    # ---- 1) Build the universe of tickers from Wikipedia ----
    print("Fetching ticker lists from Wikipedia…")
    sp500 = get_sp500_tickers()
    dax40 = get_dax40_tickers()
    # `drop_duplicates` guards against the rare case of a ticker appearing in
    # both indices (shouldn't happen for SP500/DAX40 today, but cheap insurance).
    tickers_df = pd.concat([sp500, dax40], ignore_index=True).drop_duplicates(subset=["ticker"])
    print(f"  S&P 500: {len(sp500)} | DAX 40: {len(dax40)} | total unique: {len(tickers_df)}")

    # Optional smoke-test path: use only the first N tickers.
    if args.limit:
        tickers_df = tickers_df.head(args.limit)
        print(f"  --limit set: using first {len(tickers_df)} tickers")

    tickers_df.to_csv(DATA_DIR / "tickers.csv", index=False)
    print(f"  wrote {DATA_DIR / 'tickers.csv'}")

    # ---- 2) Download price history for every ticker ----
    print(f"\nDownloading {args.years}y of daily history for {len(tickers_df)} tickers…")
    prices, failed = download_prices(tickers_df["ticker"].tolist(), args.years, args.batch_size)

    if prices.empty:
        # No frames at all → exit early rather than producing empty CSVs.
        print("No prices downloaded — check network / yfinance.")
        return

    # ---- 3) Write the long-format master file (one row per date+ticker) ----
    prices.to_csv(DATA_DIR / "prices_long.csv", index=False)
    print(f"  wrote {DATA_DIR / 'prices_long.csv'} ({len(prices):,} rows)")

    # ---- 4) Write one CSV per ticker, split into SP500/ and DAX40/ subfolders ----
    by_ticker_dir = DATA_DIR / "by_ticker"
    # `ticker_to_index` maps "AAPL" → "SP500", "SAP.DE" → "DAX40", etc.
    ticker_to_index = dict(zip(tickers_df["ticker"], tickers_df["index"]))
    counts: dict[str, int] = {}
    for tkr, df in prices.groupby("ticker"):
        idx = ticker_to_index.get(tkr, "OTHER")   # safety net for unknown tickers
        sub = by_ticker_dir / idx
        sub.mkdir(parents=True, exist_ok=True)
        # Drop the ticker column inside the per-ticker file since the filename
        # already carries that information.
        df.drop(columns="ticker").to_csv(sub / f"{tkr}.csv", index=False)
        counts[idx] = counts.get(idx, 0) + 1
    summary = ", ".join(f"{idx}: {n}" for idx, n in sorted(counts.items()))
    print(f"  wrote per-ticker files → {by_ticker_dir}/ ({summary})")

    # ---- 5) Write the wide-format adjusted-close matrix (handy for returns/correlation) ----
    # Rows = dates, columns = tickers, values = adjusted close price.
    wide = prices.pivot(index="date", columns="ticker", values="adj_close").sort_index()
    wide.to_csv(DATA_DIR / "prices_close_wide.csv")
    print(f"  wrote {DATA_DIR / 'prices_close_wide.csv'} ({wide.shape[0]} dates x {wide.shape[1]} tickers)")

    # ---- 6) Persist the list of failed tickers so they can be retried later ----
    if failed:
        pd.DataFrame({"ticker": failed}).to_csv(DATA_DIR / "failed_tickers.csv", index=False)
        print(f"  {len(failed)} tickers failed → {DATA_DIR / 'failed_tickers.csv'}")

    print("\nDone.")


# Standard Python "only run main() when executed as a script, not when imported".
if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""make preoos: per-ticker risk inputs for the preset-package rule, computed STRICTLY PRE-OOS.

For every symbol in the committed daily store (lstm/data/sp500_1d.duckdb) take the last session
<= 2023-12-29 (the sealed pipelines' Train end; OOS starts 2024-01-02) and emit:
  volatility_60d  rolling 60-session std of daily close-to-close returns * sqrt(252)  (annualized;
                  the parent project's exact formula, train_random_forest_no_history_model.py)
  ret_60d         close[t] / close[t-60] - 1  over the same pre-OOS window

FAIL-CLOSED: aborts if any as-of date lands past the cutoff — no OOS information can enter the
package rule. Output ships committed (app/data/preoos_inputs.csv); the app only reads it.

Honest note: raw prices (corporate actions deferred) — volatility near a split date is distorted;
the relax-if-underfilled path of the package rule stays enabled for that reason.
"""
import math
from pathlib import Path

import duckdb
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
BARS = ROOT / "lstm" / "data" / "sp500_1d.duckdb"
OUT = ROOT / "app" / "data" / "preoos_inputs.csv"
CUTOFF = "2023-12-29"          # last Train session of the sealed pipelines; OOS starts 2024-01-02
WINDOW = 60


def main():
    con = duckdb.connect(str(BARS), read_only=True)
    try:
        df = con.execute(
            "select symbol, date, close from bars_1d where date <= ? order by symbol, date",
            [CUTOFF]).fetchdf()
    finally:
        con.close()

    rows = []
    for sym, g in df.groupby("symbol", sort=True):
        g = g.reset_index(drop=True)
        if len(g) < WINDOW + 1:
            continue                                       # not enough pre-OOS history (late IPOs)
        ret = g["close"].pct_change()
        vol = float(ret.rolling(WINDOW).std().iloc[-1]) * math.sqrt(252)
        r60 = float(g["close"].iloc[-1] / g["close"].iloc[-1 - WINDOW] - 1)
        rows.append({"ticker": sym, "asof_date": str(g["date"].iloc[-1].date()),
                     "volatility_60d": round(vol, 6), "ret_60d": round(r60, 6)})

    out = pd.DataFrame(rows).sort_values("ticker").reset_index(drop=True)
    assert not out.empty, "no pre-OOS inputs computed"
    late = out[out["asof_date"] > CUTOFF]
    assert late.empty, f"FAIL-CLOSED: as-of dates past {CUTOFF}: {late['ticker'].tolist()}"

    OUT.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUT, index=False)
    skipped = df["symbol"].nunique() - len(out)
    print(f"preoos: {len(out)} tickers -> {OUT} (as-of max {out['asof_date'].max()}, cutoff {CUTOFF}, "
          f"{skipped} skipped for <{WINDOW + 1} pre-OOS sessions)")


if __name__ == "__main__":
    main()

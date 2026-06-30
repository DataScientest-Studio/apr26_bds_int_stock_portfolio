#!/usr/bin/env python3
"""Execute notebook_template.ipynb for one ticker -> Assets/<TICKER>/ with the 7-file deliverable.

Usage:  python3 run_asset.py TICKER=AAPL      (or:  python3 run_asset.py AAPL)

It injects the ticker into the setup cell, runs the notebook end-to-end (kernel cwd = this Structure/ dir), saves
the executed copy as file #1, and asserts the seven-file contract. The ticker's 1h OHLCV must already be in
liora.duckdb (run `make build-db` first).
"""
import re
import sys
from pathlib import Path

import nbformat
from nbconvert.preprocessors import ExecutePreprocessor

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "notebook_template.ipynb"


def parse_ticker(argv):
    for a in argv[1:]:
        if a.startswith("TICKER="):
            return a.split("=", 1)[1].strip()
        if a and not a.startswith("-"):
            return a.strip()
    raise SystemExit("usage: python3 run_asset.py TICKER=AAPL")


def main():
    ticker = parse_ticker(sys.argv)
    if not (ROOT / "liora.duckdb").exists():
        raise SystemExit("liora.duckdb not found — run `make build-db` first")
    nb = nbformat.read(TEMPLATE, as_version=4)
    for cell in nb.cells:                                  # inject the ticker into the setup cell
        if cell.cell_type == "code" and re.search(r'^TICKER\s*=', cell.source, flags=re.M):
            cell.source = re.sub(r'^TICKER\s*=.*$', f'TICKER = "{ticker}"', cell.source, count=1, flags=re.M)
            break
    ep = ExecutePreprocessor(timeout=3600, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": str(ROOT)}})   # run with cwd = Structure/
    out = ROOT / "Assets" / ticker / f"{ticker}__L4_to_L9.ipynb"
    out.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(nb, out)                                 # file #1 = the executed notebook
    for legacy in out.parent.glob(f"{ticker}__Layer*_to_Layer*.ipynb"):
        legacy.unlink()
    expected = {f"{ticker}__L4_to_L9.ipynb", f"{ticker}_ohlcv_1h.parquet",
                f"{ticker}_ohlcv_1d.parquet", f"{ticker}_ohlcv_1w.parquet",
                "OPTUNAs_XGB_HPOs_best_params.json", f"strategy_{ticker}.py", f"{ticker}_README.md"}
    present = {p.name for p in out.parent.iterdir() if p.is_file()}
    missing, extra = sorted(expected - present), sorted(present - expected)
    if missing or extra:
        raise SystemExit(f"7-file contract violated for {ticker}: missing={missing} extra={extra}")
    print(f"OK {ticker}: 7 files in {out.parent}")


if __name__ == "__main__":
    main()

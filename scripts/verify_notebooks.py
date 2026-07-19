#!/usr/bin/env python3
"""Verify the executed example notebooks — structure, provenance and sealed-row parity.

The notebooks are a record of runs that produced the sealed rows, so the thing that can
rot is the relationship between the two: an epoch turns over, the store moves, and the
committed notebook keeps printing "REPRODUCED the sealed row" about numbers that no
longer exist. That happened once in this project. This gate makes it loud.

Checks per notebook:
  1. parses, nbformat 4, has a kernelspec
  2. no cell recorded an error
  3. at least four "## " headings, so the console's table of contents is never empty
  4. no absolute path and no epoch literal anywhere in sources, outputs or metadata
  5. metadata.liora names a (ticker, model) that exists in data/results.db, and its
     sealed_row matches that row within 1e-6
  6. the rounded figures written into the notebook's own prose match the store,
     rounded the same way

    python3 scripts/verify_notebooks.py      # or: make verify
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
DB_PATH = ROOT / "data" / "results.db"
FORBIDDEN = ("/opt/", "/home/", "golden-v")
MIN_HEADINGS = 4
TOL = 1e-6


def sealed_rows():
    if not DB_PATH.is_file():
        return None
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    try:
        return {(r["ticker"], r["model"]): dict(r)
                for r in con.execute("select * from asset_results")}
    finally:
        con.close()


def close(a, b):
    return abs(float(a) - float(b)) <= TOL + TOL * abs(float(b))


def check(path, rows, problems):
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        problems.append(f"{path.name}: does not parse ({exc})")
        return
    blob = json.dumps(doc, ensure_ascii=False)

    if doc.get("nbformat") != 4:
        problems.append(f"{path.name}: nbformat is {doc.get('nbformat')!r}, expected 4")
    if "kernelspec" not in doc.get("metadata", {}):
        problems.append(f"{path.name}: metadata.kernelspec missing")

    cells = doc.get("cells", [])
    for i, cell in enumerate(cells):
        for out in cell.get("outputs", []):
            if out.get("output_type") == "error":
                problems.append(f"{path.name}: cell {i} recorded an error output")

    headings = [c for c in cells if c.get("cell_type") == "markdown"
                and "".join(c.get("source", "")).startswith("## ")]
    if len(headings) < MIN_HEADINGS:
        problems.append(f"{path.name}: {len(headings)} '## ' heading(s), "
                        f"the console's table of contents needs at least {MIN_HEADINGS}")

    for bad in FORBIDDEN:
        if bad in blob:
            problems.append(f"{path.name}: forbidden literal {bad!r} present")

    prov = doc.get("metadata", {}).get("liora")
    if not prov:
        problems.append(f"{path.name}: metadata.liora missing — nothing to check the store against")
        return
    key = (prov.get("ticker"), prov.get("model"))
    if rows is None:
        problems.append(f"{path.name}: data/results.db missing — cannot check sealed-row parity")
        return
    row = rows.get(key)
    if row is None:
        problems.append(f"{path.name}: metadata.liora names {key}, which is not in the store")
        return

    for field, claimed in (prov.get("sealed_row") or {}).items():
        actual = row.get(field)
        if isinstance(claimed, (int, float)) and isinstance(actual, (int, float)):
            if not close(claimed, actual):
                problems.append(f"{path.name}: metadata.liora.{field} is {claimed}, "
                                f"the store says {actual}")
        elif claimed != actual:
            problems.append(f"{path.name}: metadata.liora.{field} is {claimed!r}, "
                            f"the store says {actual!r}")

    # The prose in the tail note carries rounded figures. They must round to the same thing.
    prose = "\n".join("".join(c.get("source", "")) for c in cells
                      if c.get("cell_type") == "markdown")
    expected = {
        f"{row['end_capital']:.4f}": "end capital",
        f"{row['model_trades']}": "model trades",
    }
    tail = prose.split("Reproducibility note")[-1] if "Reproducibility note" in prose else ""
    if tail:
        for literal, what in expected.items():
            if literal not in tail:
                problems.append(f"{path.name}: the reproducibility note does not carry the "
                                f"store's {what} ({literal})")
        for number in re.findall(r"\*\*([0-9]+\.[0-9]{4})\*\*", tail):
            if not close(float(number), row["end_capital"]):
                problems.append(f"{path.name}: the note states {number}, "
                                f"the store's end capital is {row['end_capital']}")


def main():
    paths = sorted(EXAMPLES.glob("Example_*.ipynb"))
    if not paths:
        print("FAIL: no Example_*.ipynb under examples/")
        return 1
    rows = sealed_rows()
    problems = []
    for path in paths:
        check(path, rows, problems)
    if problems:
        print(f"FAIL: {len(problems)} problem(s) found\n")
        for p in problems:
            print(f"  - {p}")
        return 1
    print(f"OK: {len(paths)} example notebook(s) verified "
          f"(structure, provenance literals, sealed-row parity).")
    return 0


if __name__ == "__main__":
    sys.exit(main())

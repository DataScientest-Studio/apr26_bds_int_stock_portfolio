"""Run a .sql file against the active run's liora.duckdb.

A thin helper so Makefile targets (audit, portfolios) can execute SQL without a
duckdb CLI. Executes every statement in the file; with --print, shows the final
statement's result (transposed when it is a single KPI row).

    python run_sql.py build_portfolios.sql
    python run_sql.py audit.sql --print --read-only
"""

from __future__ import annotations

import argparse
from pathlib import Path

from src import db


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("sql_file")
    p.add_argument("--print", dest="show", action="store_true", help="print the final result")
    p.add_argument("--read-only", action="store_true")
    args = p.parse_args()

    con = db.connect(read_only=args.read_only)
    try:
        result = con.execute(Path(args.sql_file).read_text())
        if args.show:
            frame = result.df()
            print(frame.T.to_string(header=False) if len(frame) == 1 else frame.to_string(index=False))
    finally:
        con.close()


if __name__ == "__main__":
    main()

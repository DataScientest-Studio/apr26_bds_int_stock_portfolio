"""Single entry point to the active run's DuckDB database.

Every reader (Streamlit app, portfolios SQL, parity checks) and writer
(ingest, training) reaches the one ``liora.duckdb`` through here, so the path
lives in exactly one place. The database sits in the active run's data dir and
is exposed via the ``Project/endproduct/data`` symlink (see src/paths.py).

Pure DuckDB + pandas — imports no Streamlit, so it is safe to use from CLI
scripts as well as the cached app loaders.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd

from .paths import DATA_DIR

DB_PATH: Path = DATA_DIR / "liora.duckdb"


def connect(read_only: bool = True) -> duckdb.DuckDBPyConnection:
    """Open a connection to ``liora.duckdb``.

    Multiple ``read_only=True`` connections may coexist (the app); use
    ``read_only=False`` only for the offline writers (ingest / training).
    """
    if read_only and not DB_PATH.exists():
        raise FileNotFoundError(
            f"{DB_PATH} not found — run `make build-db` (ingest_to_duckdb.py) first."
        )
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def query(sql: str, params: list | tuple | None = None) -> pd.DataFrame:
    """Run a read-only query and return a DataFrame (connection auto-closed)."""
    con = connect(read_only=True)
    try:
        return con.execute(sql, params or []).df()
    finally:
        con.close()

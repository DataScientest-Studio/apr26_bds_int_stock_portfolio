"""One-time / idempotent build of the active run's single DuckDB database.

Reads the frozen CSV-era artifacts of the active run (exposed via the
``Project/endproduct/{data,models}`` symlinks) and materialises them into one
``liora.duckdb`` so that every downstream reader (Streamlit app, training,
portfolios) speaks SQL instead of scattered CSVs.

    ohlcv, tickers                  <- data/prices_long.csv, data/tickers.csv
    model_metrics                   <- *_metrics.csv  (5 models, normalised)
    model_predictions               <- *_predictions.csv (per model_key)
    model_rankings                  <- *_latest_rankings.csv (per model_key)
    feature_importance              <- *_feature_importance.csv (per model_key)
    walk_forward_summary/folds/feature_importance
    portfolio_recommendations/summary/sector_weights
    rocm_training_history           <- rocm_training_history.json

Re-runnable: every table is rebuilt from the CSVs. The OHLCV/tickers schema is
defined in schema.sql; artifact tables are materialised from pandas frames.

Run from Project/Structure:  python ingest_to_duckdb.py
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pandas as pd

from src.paths import DATA_DIR, MODEL_DIR
from src.model_loader import MODELS, WALK_FORWARD

SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"
DB_PATH = DATA_DIR / "liora.duckdb"

# Columns kept in the unified (heterogeneous) metrics table. Mirrors
# model_loader._METRIC_COLS plus the train/split fields some models carry.
METRIC_COLS = [
    "model_key", "label", "model",
    "train_start", "train_end", "test_start", "test_end", "split_date",
    "train_rows", "test_rows", "test_tickers",
    "mae", "rmse", "spearman_rank_corr",
    "test_universe_avg_actual_return", "top5_avg_actual_return",
    "device", "final_train_mse",
]


def _materialise(con: duckdb.DuckDBPyConnection, name: str, df: pd.DataFrame) -> None:
    """Replace table `name` with the contents of `df`."""
    con.register("_df", df)
    con.execute(f"CREATE OR REPLACE TABLE {name} AS SELECT * FROM _df")
    con.unregister("_df")
    print(f"  {name:32s} {len(df):>8,} rows")


def _build_metrics() -> pd.DataFrame:
    rows = []
    for key, cfg in MODELS.items():
        path = MODEL_DIR / cfg["metrics"]
        if not path.exists():
            continue
        row = pd.read_csv(path).iloc[0].to_dict()
        if not str(row.get("model", "")).strip():
            row["model"] = key
        row["model_key"] = key
        row["label"] = cfg["label"]
        rows.append(row)
    out = pd.DataFrame(rows)
    return out.reindex(columns=METRIC_COLS)


def _build_per_model(file_key: str, add_cols: dict | None = None) -> pd.DataFrame:
    frames = []
    for key, cfg in MODELS.items():
        name = cfg.get(file_key)
        if not name:
            continue
        path = MODEL_DIR / name
        if not path.exists():
            continue
        df = pd.read_csv(path)
        df.insert(0, "model_key", key)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _build_rocm_history() -> pd.DataFrame:
    path = MODEL_DIR / MODELS["pytorch_mlp_rocm"]["training_history"]
    if not path.exists():
        return pd.DataFrame(columns=["model_key", "epoch", "train_mse"])
    data = json.loads(path.read_text())
    mse = data.get("train_mse", [])
    return pd.DataFrame(
        {"model_key": "pytorch_mlp_rocm", "epoch": range(1, len(mse) + 1), "train_mse": mse}
    )


def main() -> None:
    if not (DATA_DIR / "prices_long.csv").exists():
        raise SystemExit(f"prices_long.csv not found under {DATA_DIR} — check the endproduct/data symlink.")

    con = duckdb.connect(str(DB_PATH))
    print(f"Building {DB_PATH}")

    # --- OHLCV + tickers (canonical schema) ---------------------------------
    con.execute("DROP TABLE IF EXISTS ohlcv")
    con.execute("DROP TABLE IF EXISTS tickers")
    con.execute(SCHEMA_FILE.read_text())

    prices_csv = str(DATA_DIR / "prices_long.csv")
    con.execute(
        "INSERT INTO ohlcv "
        "SELECT CAST(date AS DATE), ticker, open, high, low, close, adj_close, "
        "CAST(volume AS BIGINT) "
        f"FROM read_csv_auto('{prices_csv}', header=true)"
    )
    tickers_csv = str(DATA_DIR / "tickers.csv")
    con.execute(
        'INSERT INTO tickers SELECT ticker, name, sector, industry, "index", country '
        f"FROM read_csv_auto('{tickers_csv}', header=true)"
    )
    n_ohlcv = con.execute("SELECT count(*) FROM ohlcv").fetchone()[0]
    n_tick = con.execute("SELECT count(*) FROM tickers").fetchone()[0]
    print(f"  {'ohlcv':32s} {n_ohlcv:>8,} rows")
    print(f"  {'tickers':32s} {n_tick:>8,} rows")

    # --- model / walk-forward / portfolio artifacts -------------------------
    _materialise(con, "model_metrics", _build_metrics())
    _materialise(con, "model_predictions", _build_per_model("predictions"))
    _materialise(con, "model_rankings", _build_per_model("rankings"))
    _materialise(con, "feature_importance", _build_per_model("feature_importance"))
    _materialise(con, "rocm_training_history", _build_rocm_history())

    for tbl, fname in (
        ("walk_forward_summary", WALK_FORWARD["summary"]),
        ("walk_forward_folds", WALK_FORWARD["folds"]),
        ("walk_forward_feature_importance", WALK_FORWARD["feature_importance"]),
    ):
        p = MODEL_DIR / fname
        _materialise(con, tbl, pd.read_csv(p) if p.exists() else pd.DataFrame())

    for tbl, fname in (
        ("portfolio_recommendations", "portfolio_recommendations.csv"),
        ("portfolio_summary", "portfolio_summary.csv"),
        ("portfolio_sector_weights", "portfolio_sector_weights.csv"),
    ):
        p = MODEL_DIR / fname
        _materialise(con, tbl, pd.read_csv(p) if p.exists() else pd.DataFrame())

    con.close()
    print(f"Done: {DB_PATH}")


if __name__ == "__main__":
    main()

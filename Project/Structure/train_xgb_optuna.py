"""The single production model: XGBoost + Optuna on the SQL feature view.

Replaces the old zoo of train_*.py scripts. Feature engineering lives in
src/features.sql (verified parity with the legacy pandas pipeline); this script
only tunes, trains, evaluates and persists.

Two modes:

  default (production)
      Optuna-tune hyperparameters on a time-based validation slice, retrain the
      final model on the full pre-2025 train split, evaluate on the 2025+ test
      split, and write everything to liora.duckdb (model_metrics row for
      `xgboost_no_history`, plus its predictions / rankings / feature_importance)
      and to endproduct/models/{xgb_model.json, best_params.json}.

  --mode fold (walk-forward)
      Train on date <= --train-end with FIXED --params (no tuning), score the
      (train-end, test-end] window, append one fold-metrics row to --out CSV.
      Used by walk_forward.sh; never touches the production DuckDB tables.

Run from Project/Structure:
    ../.venv/bin/python train_xgb_optuna.py                 # production
    ../.venv/bin/python train_xgb_optuna.py --trials 30
"""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import optuna
import pandas as pd
import xgboost as xgb

from src import db
from src.paths import MODEL_DIR

MODEL_KEY = "xgboost_no_history"
MODEL_LABEL = "XGBoost + Optuna — production"
TARGET_HORIZON_DAYS = 63
TEST_START_DATE = pd.Timestamp("2025-01-01")
VAL_START_DATE = pd.Timestamp("2024-07-01")  # last ~6mo of train = Optuna val
RANDOM_SEED = 42

NUMERIC_FEATURES = [
    "ret_5d", "ret_20d", "ret_60d",
    "mean_return_20d", "mean_return_60d",
    "volatility_20d", "volatility_60d",
    "log_avg_volume_20d", "drawdown_252d",
]
CAT_FEATURE = "sector"
FEATURE_COLS = NUMERIC_FEATURES + [CAT_FEATURE]

STRUCTURE = Path(__file__).resolve().parent
FEATURES_SQL = (STRUCTURE / "src" / "features.sql").read_text()

# Native xgboost API (xgb.train / DMatrix) — avoids the XGBRegressor sklearn
# wrapper so scikit-learn is NOT a dependency. sector is fed as a pandas
# category via enable_categorical (no one-hot get_dummies).
FIXED_PARAMS = {
    "objective": "reg:squarederror",
    "tree_method": "hist",
    "eval_metric": "rmse",
    "seed": RANDOM_SEED,
    "nthread": -1,
}


# --------------------------------------------------------------------------- #
# Data
# --------------------------------------------------------------------------- #
def load_supervised(con) -> pd.DataFrame:
    """All feature rows from the SQL view, sector as a stable category dtype."""
    con.execute(FEATURES_SQL)  # ensure the `features` view exists
    df = con.execute(
        "SELECT date, ticker, sector, industry, "
        + ", ".join(NUMERIC_FEATURES)
        + ", target_63d_return FROM features"
    ).df()
    df["date"] = pd.to_datetime(df["date"])
    df["sector"] = df["sector"].fillna("Unknown").astype("category")
    return df


def _matrix(df: pd.DataFrame) -> pd.DataFrame:
    return df[FEATURE_COLS]


def _split_params(params: dict) -> tuple[dict, int]:
    """Split a flat hyperparameter dict into (booster params, num_boost_round)."""
    p = dict(FIXED_PARAMS)
    p.update(
        max_depth=int(params["max_depth"]),
        eta=float(params["learning_rate"]),
        min_child_weight=float(params["min_child_weight"]),
        subsample=float(params["subsample"]),
        colsample_bytree=float(params["colsample_bytree"]),
        reg_lambda=float(params["reg_lambda"]),
        reg_alpha=float(params["reg_alpha"]),
    )
    return p, int(params["n_estimators"])


def fit(params: dict, train_df: pd.DataFrame) -> xgb.Booster:
    booster_params, rounds = _split_params(params)
    dtrain = xgb.DMatrix(
        _matrix(train_df), label=train_df["target_63d_return"], enable_categorical=True
    )
    return xgb.train(booster_params, dtrain, num_boost_round=rounds)


def predict(booster: xgb.Booster, df: pd.DataFrame) -> np.ndarray:
    return booster.predict(xgb.DMatrix(_matrix(df), enable_categorical=True))


def spearman(pred, actual) -> float:
    return float(pd.Series(pred).corr(pd.Series(actual), method="spearman"))


# --------------------------------------------------------------------------- #
# Optuna
# --------------------------------------------------------------------------- #
def tune(train_df: pd.DataFrame, n_trials: int) -> dict:
    need = NUMERIC_FEATURES + ["target_63d_return"]
    fit_df = train_df[train_df["date"] < VAL_START_DATE].dropna(subset=need)
    val_df = train_df[train_df["date"] >= VAL_START_DATE].dropna(subset=need)
    yv = val_df["target_63d_return"].to_numpy()

    def objective(trial: optuna.Trial) -> float:
        params = dict(
            n_estimators=trial.suggest_int("n_estimators", 200, 700, step=50),
            max_depth=trial.suggest_int("max_depth", 3, 8),
            learning_rate=trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            min_child_weight=trial.suggest_int("min_child_weight", 5, 50),
            subsample=trial.suggest_float("subsample", 0.6, 1.0),
            colsample_bytree=trial.suggest_float("colsample_bytree", 0.6, 1.0),
            reg_lambda=trial.suggest_float("reg_lambda", 0.0, 10.0),
            reg_alpha=trial.suggest_float("reg_alpha", 0.0, 1.0),
        )
        booster = fit(params, fit_df)
        return spearman(predict(booster, val_df), yv)

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(
        direction="maximize", sampler=optuna.samplers.TPESampler(seed=RANDOM_SEED)
    )
    study.optimize(objective, n_trials=n_trials, show_progress_bar=False)
    print(f"Optuna best val Spearman = {study.best_value:.4f}")
    return study.best_params


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #
def topk_avg(rows: pd.DataFrame, k: int) -> float:
    top = (
        rows.sort_values(["date", "predicted_63d_return"], ascending=[True, False])
        .groupby("date")
        .head(k)
    )
    return float(top["target_63d_return"].mean())


def evaluate(test: pd.DataFrame) -> dict:
    err = test["predicted_63d_return"] - test["target_63d_return"]
    return {
        "mae": float(err.abs().mean()),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "spearman_rank_corr": spearman(test["predicted_63d_return"], test["target_63d_return"]),
        "test_universe_avg_actual_return": float(test["target_63d_return"].mean()),
        "top5_avg_actual_return": topk_avg(test, 5),
        "test_rows": int(len(test)),
        "test_tickers": int(test["ticker"].nunique()),
    }


# --------------------------------------------------------------------------- #
# DuckDB writes
# --------------------------------------------------------------------------- #
def _replace_rows(con, table: str, df: pd.DataFrame) -> None:
    con.execute(f"DELETE FROM {table} WHERE model_key = ?", [MODEL_KEY])
    con.register("_df", df)
    con.execute(f"INSERT INTO {table} BY NAME SELECT * FROM _df")
    con.unregister("_df")


def write_production(con, metrics_row, preds, rankings, importance) -> None:
    _replace_rows(con, "model_metrics", pd.DataFrame([metrics_row]))
    _replace_rows(con, "model_predictions", preds)
    _replace_rows(con, "model_rankings", rankings)
    _replace_rows(con, "feature_importance", importance)


# --------------------------------------------------------------------------- #
# Modes
# --------------------------------------------------------------------------- #
def run_production(n_trials: int) -> None:
    con = db.connect(read_only=False)
    df = load_supervised(con)

    train = df[df["date"] < TEST_START_DATE]
    best = tune(train, n_trials)
    print(f"Best params: {best}")

    train_sup = train.dropna(subset=NUMERIC_FEATURES + ["target_63d_return"])
    booster = fit(best, train_sup)

    test = df[(df["date"] >= TEST_START_DATE)].dropna(subset=NUMERIC_FEATURES + ["target_63d_return"]).copy()
    test["predicted_63d_return"] = predict(booster, test)
    m = evaluate(test)

    metrics_row = {
        "model_key": MODEL_KEY, "label": MODEL_LABEL, "model": MODEL_KEY,
        "train_start": train_sup["date"].min().date().isoformat(),
        "train_end": train_sup["date"].max().date().isoformat(),
        "test_start": test["date"].min().date().isoformat(),
        "test_end": test["date"].max().date().isoformat(),
        "split_date": TEST_START_DATE.date().isoformat(),
        "train_rows": int(len(train_sup)),
        "device": None, "final_train_mse": None,
        **m,
    }

    preds = test[["date", "ticker", "sector", "target_63d_return", "predicted_63d_return"]].copy()
    preds.insert(0, "model_key", MODEL_KEY)
    preds["date"] = preds["date"].dt.strftime("%Y-%m-%d")
    preds["sector"] = preds["sector"].astype(str)

    # latest rankings: predict the most recent date (target is naturally NaN there)
    latest_date = df["date"].max()
    latest = df[(df["date"] == latest_date)].dropna(subset=NUMERIC_FEATURES).copy()
    latest["predicted_63d_return"] = predict(booster, latest)
    rankings = latest[["date", "ticker", "sector", "industry", "predicted_63d_return",
                       "volatility_60d", "ret_60d"]].sort_values("predicted_63d_return", ascending=False)
    rankings.insert(0, "model_key", MODEL_KEY)
    rankings["date"] = rankings["date"].dt.strftime("%Y-%m-%d")
    rankings["sector"] = rankings["sector"].astype(str)

    gain = booster.get_score(importance_type="gain")
    importance = pd.DataFrame(
        {"model_key": MODEL_KEY, "feature": FEATURE_COLS,
         "importance": [float(gain.get(f, 0.0)) for f in FEATURE_COLS]}
    ).sort_values("importance", ascending=False)

    write_production(con, metrics_row, preds, rankings, importance)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    booster.save_model(str(MODEL_DIR / "xgb_model.json"))
    (MODEL_DIR / "best_params.json").write_text(json.dumps(best, indent=2))
    con.close()

    # quality gate vs frozen RF-no-history baseline
    print("\n=== Production XGBoost + Optuna ===")
    print(f"  test Spearman           : {m['spearman_rank_corr']:.4f}")
    print(f"  test top-5 avg return   : {m['top5_avg_actual_return']:.4%}")
    print(f"  test universe avg return: {m['test_universe_avg_actual_return']:.4%}")
    rf = db.query(
        "SELECT top5_avg_actual_return FROM model_metrics WHERE model_key='random_forest_no_history'"
    )
    if rf is not None and not rf.empty:
        delta = m["top5_avg_actual_return"] - float(rf.iloc[0, 0])
        verdict = "≥ RF baseline ✅" if delta >= 0 else "< RF baseline (documented in leaderboard)"
        print(f"  vs RF-no-history top-5  : {float(rf.iloc[0,0]):.4%}  (Δ {delta:+.4%}) — {verdict}")
    print(f"\nSaved model → {MODEL_DIR/'xgb_model.json'}")


def run_fold(train_end: str, test_end: str, params_file: str, fold: int, out: str) -> None:
    con = db.connect(read_only=False)
    df = load_supervised(con)
    con.close()
    params = json.loads(Path(params_file).read_text())

    te = pd.Timestamp(train_end)
    tend = pd.Timestamp(test_end)
    train = df[(df["date"] <= te)].dropna(subset=NUMERIC_FEATURES + ["target_63d_return"])
    test = df[(df["date"] > te) & (df["date"] <= tend)].dropna(
        subset=NUMERIC_FEATURES + ["target_63d_return"]
    ).copy()
    if train.empty or test.empty:
        print(f"fold {fold}: empty train/test — skipped")
        return

    booster = fit(params, train)
    test["predicted_63d_return"] = predict(booster, test)
    err = test["predicted_63d_return"] - test["target_63d_return"]

    row = {
        "fold": fold,
        "train_start": train["date"].min().date().isoformat(),
        "train_end": train["date"].max().date().isoformat(),
        "test_start": test["date"].min().date().isoformat(),
        "test_end": test["date"].max().date().isoformat(),
        "train_rows": int(len(train)),
        "test_rows": int(len(test)),
        "test_tickers": int(test["ticker"].nunique()),
        "mae": float(err.abs().mean()),
        "rmse": float(np.sqrt(np.mean(err**2))),
        "spearman_rank_corr": spearman(test["predicted_63d_return"], test["target_63d_return"]),
        "universe_avg_actual_return": float(test["target_63d_return"].mean()),
        "top5_avg_actual_return": topk_avg(test, 5),
        "top10_avg_actual_return": topk_avg(test, 10),
    }
    out_path = Path(out)
    header = not out_path.exists() or out_path.stat().st_size == 0
    pd.DataFrame([row]).to_csv(out_path, mode="a", header=header, index=False)
    print(f"fold {fold}: test {row['test_start']}→{row['test_end']} "
          f"spearman={row['spearman_rank_corr']:.3f} top5={row['top5_avg_actual_return']:.3%}")


def main() -> None:
    logging.getLogger("xgboost").setLevel(logging.ERROR)
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["production", "fold"], default="production")
    p.add_argument("--trials", type=int, default=30, help="Optuna trials (production mode)")
    p.add_argument("--train-end", help="fold mode: last training date (YYYY-MM-DD)")
    p.add_argument("--test-end", help="fold mode: last test date (YYYY-MM-DD)")
    p.add_argument("--params", help="fold mode: best_params.json with fixed hyperparameters")
    p.add_argument("--fold", type=int, default=0, help="fold mode: fold index")
    p.add_argument("--out", help="fold mode: CSV to append the fold-metrics row to")
    args = p.parse_args()

    if args.mode == "production":
        run_production(args.trials)
    else:
        run_fold(args.train_end, args.test_end, args.params, args.fold, args.out)


if __name__ == "__main__":
    main()

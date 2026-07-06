"""Results store: fs/artifacts/<universe>/fs_results.duckdb. Single writer (stages run
sequentially); every write is idempotent per (run_id, model) — stages can be re-run.
The `feature_importance_shap` schema is exactly WO-FS-XGB §5."""
import duckdb

from . import art_dir

SCHEMAS = {
    "feature_importance_shap": (
        "run_id TEXT, model TEXT, method TEXT, ticker TEXT, feature TEXT, "
        "mean_abs_shap DOUBLE, shap_share DOUBLE, rank_in_ticker INTEGER"),
    "shap_universality": (
        "run_id TEXT, model TEXT, feature TEXT, median_rank DOUBLE, iqr_rank DOUBLE, "
        "coverage DOUBLE, asset_specific INTEGER"),
    "loop_rounds": (
        "run_id TEXT, model TEXT, round INTEGER, n_features INTEGER, cv_mean DOUBLE, "
        "cv_se DOUBLE, removed TEXT, features TEXT, mda TEXT, control TEXT"),
    "stability": "run_id TEXT, model TEXT, feature TEXT, pi DOUBLE",
    "cv_scores": (
        "run_id TEXT, model TEXT, stage TEXT, unit TEXT, unit_id TEXT, score DOUBLE, extra TEXT"),
    "trial_slices": "run_id TEXT, model TEXT, trial INTEGER, slice INTEGER, score DOUBLE",
    "verdict": "run_id TEXT, model TEXT, payload TEXT",
}


def db_path(universe):
    return str(art_dir(universe) / "fs_results.duckdb")


def replace_rows(universe, table, rows, run_id, model, stage=None):
    """Delete this (run_id, model[, stage])'s rows in `table`, insert the new ones. `stage` scopes
    the delete for cv_scores, which several stages (study2_best, cpcv) share under one (run_id,
    model) — without it, re-running one stage would wipe the others' rows."""
    if table not in SCHEMAS:
        raise KeyError(table)
    con = duckdb.connect(db_path(universe))
    try:
        con.execute(f"create table if not exists {table} ({SCHEMAS[table]})")
        if stage is None:
            con.execute(f"delete from {table} where run_id=? and model=?", [run_id, model])
        else:
            con.execute(f"delete from {table} where run_id=? and model=? and stage=?",
                        [run_id, model, stage])
        if rows:
            cols = [c.split()[0] for c in SCHEMAS[table].split(", ")]
            ph = ",".join("?" for _ in cols)
            con.executemany(f"insert into {table} values ({ph})",
                            [[r.get(c) for c in cols] for r in rows])
        con.commit()
    finally:
        con.close()


def read_table(universe, table, model=None, run_id=None):
    import pandas as pd
    con = duckdb.connect(db_path(universe), read_only=True)
    try:
        tables = {t[0] for t in con.execute("show tables").fetchall()}
        if table not in tables:
            return pd.DataFrame()
        conds = []
        if model:
            conds.append(f"model='{model}'")
        if run_id:
            conds.append(f"run_id='{run_id}'")
        q = f"select * from {table}" + (" where " + " and ".join(conds) if conds else "")
        return con.execute(q).fetchdf()
    finally:
        con.close()

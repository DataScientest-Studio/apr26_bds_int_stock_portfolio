#!/usr/bin/env python3
"""Continuous per-asset best-features search worker (S.1 research plane).

Runs FOREVER (until STOP.flag / HALT.flag / control.halt) in rounds over the
non-problematic tickers of the universe. Per asset it searches subsets of the
39 OPTIONAL coarse features (1d 101-117, 1w 201-217, multi_tf 901-905) — the
1h namespace is frozen — scoring each subset by mean purged walk-forward CV
AUC-PR on Train only (fixed fallback_params, the exact evaluator the old
FEATURE_SEARCH_PY used). A ticker that raises is PARKED (status+error+alert)
and skipped; the loop keeps going over the healthy rest.

"Sensible value" bar: satisfied when best_cv >= baseline_ref + min_gain where
baseline_ref = max(cv(1h-only), cv(all-56)). On the FIRST satisfied, the
winner is applied atomically to config/per_asset_feature_overrides.json and
run_asset.py fires ONCE (the single OOS read for that asset). Later rounds
keep polishing on Train only; a Train-CV candidate beating the applied one
sets pending_better=1 — re-apply (a second OOS read) happens ONLY via the
manual `make search-apply TICKER=...` path, never automatically.

State: search_state.db (sqlite WAL; this process is the ONLY writer; readers
use mode=ro) + search_control.json (agent-tunable; malformed JSON => alert +
last good copy) + logs/search/{worker.log,heartbeat.json,ALERTS.txt,...}.
Deterministic: seed 42, nthread 1, fixed candidate enumeration; the next
candidate is a pure function of (state db, control file, round).

CLI:  (no args) run the continuous loop
      --plan-next        print the next (ticker, subset_key) without evaluating
      --status           read-only status table (used by `make search-status`)
      --apply TICKER     manual re-apply of the current best (operator decision)
"""
import argparse
import itertools
import json
import os
import sqlite3
import subprocess
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pipeline as P  # noqa: E402

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "search_state.db"
CONTROL_PATH = ROOT / "search_control.json"
OVERRIDES_PATH = ROOT / "config" / "per_asset_feature_overrides.json"
LOG_DIR = ROOT / "logs" / "search"
HEARTBEAT = LOG_DIR / "heartbeat.json"
ALERTS = LOG_DIR / "ALERTS.txt"
STOP_FLAG = LOG_DIR / "STOP.flag"
HALT_FLAG = LOG_DIR / "HALT.flag"

DEFAULT_UNIVERSE = ("AAPL MSFT NVDA AMZN GOOGL META TSLA AVGO LLY JPM "
                    "V UNH XOM MA COST PG HD JNJ WMT NFLX")

CONTROL_DEFAULTS = {
    "schema_version": "search_control.v1",
    "epsilon": 0.0005,
    "no_improve_N": 8,
    "stage2_max_evals": 200,
    "min_gain": 0.002,
    "round_budget_evals": 150,
    "priorities": [],
    "paused_tickers": [],
    "stage3_candidates": {},
    "halt": False,
    "notes": "",
}

OPTIONAL_IDS = sorted(
    int(f["id"])
    for reg in P.FEATURE_REGISTRIES.values()
    for f in reg["features"]
    if bool(f.get("implemented", True)) and not (1 <= int(f["id"]) <= 99)
)
BLOCKS = {"1d": [i for i in OPTIONAL_IDS if 101 <= i <= 199],
          "1w": [i for i in OPTIONAL_IDS if 201 <= i <= 299],
          "multi_tf": [i for i in OPTIONAL_IDS if 901 <= i <= 999]}


def utcnow():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(msg):
    line = f"[{utcnow()}] {msg}"
    print(line, flush=True)


def alert(msg):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    with open(ALERTS, "a", encoding="utf-8") as f:
        f.write(f"[{utcnow()}] {msg}\n")
    log("ALERT: " + msg)


def heartbeat(**kw):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tmp = HEARTBEAT.with_suffix(".tmp")
    tmp.write_text(json.dumps({"ts": utcnow(), **kw}), encoding="utf-8")
    os.replace(tmp, HEARTBEAT)


def stop_requested(ctl):
    return bool(ctl.get("halt")) or STOP_FLAG.exists() or HALT_FLAG.exists()


# ---------------------------------------------------------------- control ---

_control_cache = {"mtime": None, "data": dict(CONTROL_DEFAULTS)}


def read_control():
    if not CONTROL_PATH.exists():
        tmp = CONTROL_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(CONTROL_DEFAULTS, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, CONTROL_PATH)
    mtime = CONTROL_PATH.stat().st_mtime
    if mtime == _control_cache["mtime"]:
        return _control_cache["data"]
    try:
        raw = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
        data = dict(CONTROL_DEFAULTS)
        data.update({k: raw[k] for k in CONTROL_DEFAULTS if k in raw})
        _control_cache.update(mtime=mtime, data=data)
    except Exception as e:
        alert(f"search_control.json malformed ({e!r}) — keeping last good copy")
        _control_cache["mtime"] = mtime
    return _control_cache["data"]


# ------------------------------------------------------------------- state ---

def db_connect(readonly=False):
    if readonly:
        con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        con = sqlite3.connect(DB_PATH)
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA busy_timeout=5000")
    con.row_factory = sqlite3.Row
    return con


def db_init(con, universe):
    con.executescript("""
    CREATE TABLE IF NOT EXISTS evaluations(
      ticker TEXT, subset_key TEXT, subset_ids_json TEXT,
      cv_auc_pr REAL, n_features INTEGER, n_folds INTEGER,
      stage TEXT, source TEXT, round INTEGER,
      evaluated_at TEXT, eval_seconds REAL,
      PRIMARY KEY(ticker, subset_key));
    CREATE TABLE IF NOT EXISTS assets(
      ticker TEXT PRIMARY KEY, status TEXT,
      baseline_ref REAL, best_subset_key TEXT, best_cv REAL, best_n_features INTEGER,
      applied_subset_key TEXT, applied_cv REAL, pending_better INTEGER DEFAULT 0,
      evals_count INTEGER DEFAULT 0, no_improve_streak INTEGER DEFAULT 0,
      round INTEGER DEFAULT 0, run_asset_attempts INTEGER DEFAULT 0,
      error TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY, value TEXT);
    """)
    for t in universe:
        con.execute("INSERT OR IGNORE INTO assets(ticker, status, updated_at) VALUES(?, 'pending', ?)",
                    (t, utcnow()))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('universe', ?)", (" ".join(universe),))
    con.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('started_at', ?)", (utcnow(),))
    con.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('rounds_completed', '0')")
    con.commit()


def asset_row(con, t):
    return con.execute("SELECT * FROM assets WHERE ticker=?", (t,)).fetchone()


def set_asset(con, t, **kw):
    kw["updated_at"] = utcnow()
    cols = ", ".join(f"{k}=?" for k in kw)
    con.execute(f"UPDATE assets SET {cols} WHERE ticker=?", (*kw.values(), t))
    con.commit()


def recompute_best(con, t):
    """The db is the truth: best = max cv, ties -> fewer features -> smallest key."""
    row = con.execute(
        "SELECT subset_key, cv_auc_pr, n_features FROM evaluations WHERE ticker=? "
        "ORDER BY cv_auc_pr DESC, n_features ASC, subset_key ASC LIMIT 1", (t,)).fetchone()
    if row:
        set_asset(con, t, best_subset_key=row["subset_key"], best_cv=row["cv_auc_pr"],
                  best_n_features=row["n_features"])
    return row


def subset_key(ids):
    return ",".join(str(i) for i in sorted(ids))


def key_ids(key):
    return [] if key in (None, "") else [int(x) for x in key.split(",")]


# --------------------------------------------------------------- evaluator ---

FB = dict(P.XGBOOST_OPTUNA_SEARCH_SPACE["fallback_params"])


def cv_aucpr(df_b, bounds, names, seed):
    import numpy as np
    import xgboost as xgb
    X = df_b[names].to_numpy(float)
    y = df_b["Y_outcome"].to_numpy(int)
    w = df_b["label_uniqueness_weight"].to_numpy(float)
    t0s = [int(s.split(":")[1]) for s in df_b["setup_id"]]
    ap = []
    for tr, va in P.purged_wf_folds(t0s, bounds["train_start_idx"], bounds["train_end_idx"]):
        if len(set(y[tr])) < 2:
            continue
        bst = P._xgb_train(X[tr], y[tr], w[tr], FB, seed, feature_names=names)
        ap.append(P.average_precision(y[va], bst.predict(xgb.DMatrix(X[va], feature_names=names))))
    if not ap:
        raise RuntimeError("no scoreable folds (degenerate Train data)")
    return float(sum(ap) / len(ap)), len(ap)


class TickerContext:
    """Superset Output-B for one ticker, built once and cached for the round."""

    def __init__(self, ticker):
        import pandas as pd
        seed_path = ROOT / "data" / "seed" / f"{ticker}_ohlcv_1h.parquet"
        if not seed_path.exists():
            raise RuntimeError(f"missing seed {seed_path.name} (run `make ensure-seeds`)")
        df = pd.read_parquet(seed_path)
        manifest = P.resolve_feature_manifest(ticker, overrides={})   # superset: all 56
        rec = P.derive_output_b(df, ticker, manifest)
        got = set(rec["manifest"]["effective_feature_ids"])
        want = set(range(1, 18)) | set(OPTIONAL_IDS)
        if got != want:
            raise RuntimeError(f"superset manifest mismatch: {sorted(got ^ want)}")
        self.ticker = ticker
        self.df_b = rec["df_b"]
        self.bounds = rec["bounds"]
        if not len(self.df_b):
            raise RuntimeError("empty Output B (no eligible Train candidates)")


def evaluate(con, ctx, subset, stage, source, rnd, ctl, seed, counters):
    """Score one optional-id subset; keyed — an existing key is returned, never re-run."""
    key = subset_key(subset)
    row = con.execute("SELECT cv_auc_pr FROM evaluations WHERE ticker=? AND subset_key=?",
                      (ctx.ticker, key)).fetchone()
    if row:
        return row["cv_auc_pr"], False
    bad = [i for i in subset if i not in OPTIONAL_IDS]
    if bad:
        raise RuntimeError(f"candidate contains non-optional ids {bad}")
    m = P.resolve_feature_manifest(ctx.ticker, overrides={ctx.ticker: {"selected_optional_ids": sorted(subset)}})
    names = m["effective_feature_names"]
    t0 = time.time()
    cv, n_folds = cv_aucpr(ctx.df_b, ctx.bounds, names, seed)
    a = asset_row(con, ctx.ticker)
    improved = a["best_cv"] is None or cv > a["best_cv"] + ctl["epsilon"]
    con.execute("INSERT INTO evaluations VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                (ctx.ticker, key, json.dumps(sorted(subset)), cv, len(names), n_folds,
                 stage, source, rnd, utcnow(), round(time.time() - t0, 3)))
    con.execute("UPDATE assets SET evals_count=evals_count+1, no_improve_streak=? WHERE ticker=?",
                (0 if improved else (a["no_improve_streak"] or 0) + 1, ctx.ticker))
    con.commit()
    recompute_best(con, ctx.ticker)
    counters["new"] += 1
    counters["ticker_new"] += 1
    heartbeat(ticker=ctx.ticker, phase=stage, round=rnd,
              evals_ticker=counters["ticker_new"], last_cv=round(cv, 6))
    return cv, True


# ----------------------------------------------------------- search stages ---

def candidate_stream(con, ctx, rnd, ctl):
    """Deterministic candidate generator for (ticker, round). Yields (subset, stage, source).
    The stream inspects the db lazily so adopted improvements reshape later candidates."""
    t = ctx.ticker

    def best_ids():
        r = asset_row(con, t)
        return set(key_ids(r["best_subset_key"] or ""))

    if rnd <= 1:
        # stage-1: baselines + the 8 block combos
        yield [], "grid", "worker"                                     # 1h-only baseline
        yield list(OPTIONAL_IDS), "grid", "worker"                     # all-56 baseline
        for combo in itertools.chain.from_iterable(
                itertools.combinations(("1d", "1w", "multi_tf"), k) for k in (1, 2, 3)):
            yield sorted(i for b in combo for i in BLOCKS[b]), "grid", "worker"
        # stage-2: greedy passes around the live best
        for _ in range(64):                                            # pass budget; streak/budget break earlier
            base = best_ids()
            for i in sorted(base):
                yield sorted(base - {i}), "greedy", "worker"
            for i in OPTIONAL_IDS:
                if i not in base:
                    yield sorted(base | {i}), "greedy", "worker"
    else:
        # deeper rounds: pair-swap -> restart greedy from k-th best -> add/remove-2
        base = best_ids()
        for i in sorted(base):
            for j in OPTIONAL_IDS:
                if j not in base:
                    yield sorted((base - {i}) | {j}), "swap", "worker"
        k = min(rnd, 10)
        kth = con.execute(
            "SELECT subset_key FROM evaluations WHERE ticker=? "
            "ORDER BY cv_auc_pr DESC, n_features ASC, subset_key ASC LIMIT 1 OFFSET ?",
            (t, k - 1)).fetchone()
        if kth:
            seed_set = set(key_ids(kth["subset_key"]))
            for i in sorted(seed_set):
                yield sorted(seed_set - {i}), "restart", "worker"
            for i in OPTIONAL_IDS:
                if i not in seed_set:
                    yield sorted(seed_set | {i}), "restart", "worker"
        base = best_ids()
        for i, j in itertools.combinations(sorted(base), 2):
            yield sorted(base - {i, j}), "swap", "worker"
        top = [set(key_ids(r["subset_key"])) for r in con.execute(
            "SELECT subset_key FROM evaluations WHERE ticker=? "
            "ORDER BY cv_auc_pr DESC, n_features ASC, subset_key ASC LIMIT 5", (t,))]
        pool = sorted(set().union(*top) - base) if top else []
        for i, j in itertools.combinations(pool, 2):
            yield sorted(base | {i, j}), "swap", "worker"

    # stage-3: agent candidates (drained every round)
    for cand in ctl["stage3_candidates"].get(t, []):
        try:
            ids = sorted(int(x) for x in cand)
        except Exception:
            alert(f"{t}: malformed agent candidate {cand!r} — rejected")
            continue
        if any(i not in OPTIONAL_IDS for i in ids):
            alert(f"{t}: agent candidate {ids} contains non-optional ids — rejected")
            continue
        yield ids, "agent", "agent"


def search_ticker(con, t, rnd, ctl, seed, counters):
    ctx = TickerContext(t)
    a = asset_row(con, t)
    # Only the very first pass flips pending->searching. A ticker that is already
    # satisfied/applied must NEVER have its lifecycle status touched here — resetting
    # it every round would make maybe_apply() re-fire apply_override()+run_asset(),
    # i.e. a second OOS read, on every round. Continued polishing stays Train-only.
    if a["status"] == "pending":
        set_asset(con, t, status="searching", round=rnd)
    else:
        set_asset(con, t, round=rnd)
    con.execute("UPDATE assets SET no_improve_streak=0 WHERE ticker=?", (t,))
    con.commit()
    for subset, stage, source in candidate_stream(con, ctx, rnd, ctl):
        ctl = read_control()
        if stop_requested(ctl) or t in ctl["paused_tickers"]:
            return
        if counters["ticker_new"] >= (ctl["round_budget_evals"] if rnd > 1 else ctl["stage2_max_evals"]):
            break
        evaluate(con, ctx, subset, stage, source, rnd, ctl, seed, counters)
        a = asset_row(con, t)
        if stage == "greedy" and a["no_improve_streak"] >= ctl["no_improve_N"]:
            break
    # stage-1 finished at least once: record baseline_ref
    a = asset_row(con, t)
    if a["baseline_ref"] is None:
        rows = {r["subset_key"]: r["cv_auc_pr"] for r in con.execute(
            "SELECT subset_key, cv_auc_pr FROM evaluations WHERE ticker=? AND subset_key IN (?, ?)",
            (t, "", subset_key(OPTIONAL_IDS)))}
        if len(rows) == 2:
            set_asset(con, t, baseline_ref=max(rows.values()))


# ------------------------------------------------------------- apply plane ---

def apply_override(t, ids, cv, stage):
    ids = sorted(int(i) for i in ids)
    assert not any(1 <= i <= 99 for i in ids), "override may not touch the frozen 1h namespace"
    assert all(i in OPTIONAL_IDS for i in ids), f"override contains non-optional ids: {ids}"
    doc = {"schema_version": "per_asset_feature_overrides.v1",
           "_meta": {"written_by": "feature_search_worker.py — atomic tmp+os.replace; "
                                   "the 1h namespace may never appear here"},
           "asset_overrides": {}}
    if OVERRIDES_PATH.exists():
        doc = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    doc.setdefault("asset_overrides", {})[t] = {
        "selected_optional_ids": ids,
        "provenance": {"cv_auc_pr": cv, "stage": stage, "evaluated_at": utcnow()}}
    tmp = OVERRIDES_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, OVERRIDES_PATH)


def run_asset(t):
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    heartbeat(ticker=t, phase="run_asset", grace_s=10800)
    logf = LOG_DIR / f"run_asset_{t}.log"
    env = dict(os.environ, OMP_NUM_THREADS="1")
    with open(logf, "a", encoding="utf-8") as f:
        f.write(f"\n=== run_asset {t} @ {utcnow()} ===\n")
        f.flush()
        rc = subprocess.run([sys.executable, "run_asset.py", f"TICKER={t}"],
                            cwd=str(ROOT), env=env, stdout=f, stderr=subprocess.STDOUT,
                            timeout=10800).returncode
    heartbeat(ticker=t, phase="run_asset_done", rc=rc)
    return rc


def _apply_and_run(con, t, subset_key_val, cv, attempts_before):
    """Apply the winning subset and fire the SINGLE OOS read via run_asset.py. On
    failure, retry up to 3 attempts (across rounds) before parking the ticker —
    a repeatedly-broken run_asset must not spin forever."""
    apply_override(t, key_ids(subset_key_val), cv, "auto_first_satisfied")
    rc = run_asset(t)
    if rc == 0:
        set_asset(con, t, status="applied", applied_subset_key=subset_key_val,
                  applied_cv=cv, pending_better=0)
        log(f"{t}: applied + one-shot OOS done (subset {subset_key_val})")
        return True
    attempts = attempts_before + 1
    if attempts < 3:
        set_asset(con, t, status="satisfied", run_asset_attempts=attempts)
        alert(f"{t}: run_asset rc={rc} (attempt {attempts}/3) — will retry next round")
    else:
        set_asset(con, t, status="parked", run_asset_attempts=attempts,
                  error=f"run_asset failed rc={rc} x{attempts}")
        alert(f"{t}: PARKED after {attempts} run_asset failures (see logs/search/run_asset_{t}.log)")
    return False


def maybe_apply(con, t, ctl):
    """Own the ENTIRE apply/OOS lifecycle transition. status in (pending, searching)
    means "never yet satisfied" (search_ticker only ever sets searching from
    pending, never from satisfied/applied — see search_ticker's comment)."""
    a = asset_row(con, t)
    if a["best_cv"] is None or a["baseline_ref"] is None:
        return
    sensible = a["best_cv"] >= a["baseline_ref"] + ctl["min_gain"]
    if a["status"] in ("pending", "searching") and sensible:
        set_asset(con, t, status="satisfied")
        log(f"{t}: satisfied (best_cv={a['best_cv']:.4f} >= baseline {a['baseline_ref']:.4f} + {ctl['min_gain']})")
        _apply_and_run(con, t, a["best_subset_key"], a["best_cv"], a["run_asset_attempts"] or 0)
    elif a["status"] == "satisfied" and sensible:
        # retry path after a previously failed run_asset (still capped at 3 attempts)
        _apply_and_run(con, t, a["best_subset_key"], a["best_cv"], a["run_asset_attempts"] or 0)
    elif a["status"] == "applied" and a["applied_cv"] is not None \
            and a["best_cv"] > a["applied_cv"] + ctl["epsilon"] and not a["pending_better"]:
        set_asset(con, t, pending_better=1)
        alert(f"{t}: Train-CV best ({a['best_cv']:.4f}) now beats the applied subset "
              f"({a['applied_cv']:.4f}) — pending_better; re-apply is a MANUAL decision "
              f"(make search-apply TICKER={t})")


# ------------------------------------------------------------------ orders ---

def round_order(con, universe, ctl):
    rows = {r["ticker"]: r for r in con.execute("SELECT * FROM assets")}
    healthy = [t for t in universe if rows.get(t) and rows[t]["status"] != "parked"
               and t not in ctl["paused_tickers"]]
    prio = [t for t in ctl["priorities"] if t in healthy]
    rest = [t for t in healthy if t not in prio]
    unsat = [t for t in rest if rows[t]["status"] in ("pending", "searching", "satisfied")]
    sat = [t for t in rest if rows[t]["status"] == "applied"]
    return prio + unsat + sat


def ensure_db_inputs(universe):
    """All seeds present (launcher exports them); rebuild liora.duckdb once if any ticker missing."""
    missing_seed = [t for t in universe if not (ROOT / "data" / "seed" / f"{t}_ohlcv_1h.parquet").exists()]
    if missing_seed:
        raise SystemExit(f"missing seeds {missing_seed} — run `make ensure-seeds` first")
    need_build = not (ROOT / "liora.duckdb").exists()
    if not need_build:
        import duckdb
        con = duckdb.connect(str(ROOT / "liora.duckdb"), read_only=True)
        have = {r[0] for r in con.execute("select distinct ticker from bars_1h").fetchall()}
        con.close()
        need_build = any(t not in have for t in universe)
    if need_build:
        log("rebuilding liora.duckdb (new seeds present)")
        import build_db
        build_db.build_db()


# -------------------------------------------------------------------- main ---

def run_loop():
    seed = P.seed_everything()
    P.validate_parameters()
    universe = (os.environ.get("SEARCH_TICKERS") or DEFAULT_UNIVERSE).upper().split()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ensure_db_inputs(universe)
    con = db_connect()
    db_init(con, universe)
    log(f"worker up: universe={len(universe)} tickers, optional ids={len(OPTIONAL_IDS)}")
    while True:
        ctl = read_control()
        if stop_requested(ctl):
            heartbeat(phase="halted")
            log("halt/stop requested — exiting 3")
            return 3
        order = round_order(con, universe, ctl)
        if not order:
            alert("all tickers parked/paused — sleeping 300s")
            heartbeat(phase="all_parked")
            time.sleep(300)
            continue
        rnd_done = int(con.execute("SELECT value FROM meta WHERE key='rounds_completed'").fetchone()[0])
        rnd = rnd_done + 1
        counters = {"new": 0, "ticker_new": 0}
        log(f"=== round {rnd}: {len(order)} tickers ===")
        for t in order:
            ctl = read_control()
            if stop_requested(ctl):
                return 3
            counters["ticker_new"] = 0
            try:
                search_ticker(con, t, rnd, ctl, seed, counters)
                maybe_apply(con, t, read_control())
            except Exception as e:
                set_asset(con, t, status="parked", error=repr(e)[:500])
                alert(f"{t}: PARKED — {e!r}")
                log(traceback.format_exc())
        con.execute("UPDATE meta SET value=? WHERE key='rounds_completed'", (str(rnd),))
        con.commit()
        log(f"round {rnd} done: {counters['new']} new evaluations")
        if counters["new"] == 0:
            heartbeat(phase="idle", round=rnd)
            log("no new evaluations this round — space exhausted for now; sleeping 600s")
            for _ in range(20):
                time.sleep(30)
                if stop_requested(read_control()):
                    return 3


def plan_next():
    """Print the next NEW (ticker, subset_key) without evaluating (determinism probe)."""
    universe = (os.environ.get("SEARCH_TICKERS") or DEFAULT_UNIVERSE).upper().split()
    if not DB_PATH.exists():
        print(f"{universe[0]}\t(db absent — first candidate is the 1h-only baseline: '')")
        return 0
    con = db_connect()
    db_init(con, universe)
    ctl = read_control()
    order = round_order(con, universe, ctl)
    rnd = int(con.execute("SELECT value FROM meta WHERE key='rounds_completed'").fetchone()[0]) + 1
    for t in order:
        ctx = type("Stub", (), {"ticker": t})()   # candidate_stream needs only .ticker
        for subset, stage, _ in candidate_stream(con, ctx, rnd, ctl):
            key = subset_key(subset)
            if not con.execute("SELECT 1 FROM evaluations WHERE ticker=? AND subset_key=?",
                               (t, key)).fetchone():
                print(f"{t}\t{stage}\t{key}")
                return 0
    print("(no new candidate in the current round shape)")
    return 0


def status():
    if not DB_PATH.exists():
        print("no search_state.db yet — run `make search-on`")
        return 0
    con = db_connect(readonly=True)
    print(f"{'ticker':7s} {'status':10s} {'round':>5s} {'evals':>6s} {'baseline':>9s} "
          f"{'best_cv':>9s} {'applied':>9s} {'pend':>4s}  best_subset")
    for r in con.execute("SELECT * FROM assets ORDER BY ticker"):
        fmt = lambda v: f"{v:.4f}" if v is not None else "-"
        print(f"{r['ticker']:7s} {r['status'] or '-':10s} {r['round'] or 0:5d} {r['evals_count'] or 0:6d} "
              f"{fmt(r['baseline_ref']):>9s} {fmt(r['best_cv']):>9s} {fmt(r['applied_cv']):>9s} "
              f"{r['pending_better'] or 0:4d}  {r['best_subset_key'] or '-'}")
    meta = dict(con.execute("SELECT key, value FROM meta"))
    print(f"rounds_completed={meta.get('rounds_completed', '0')}  started_at={meta.get('started_at', '-')}")
    if HEARTBEAT.exists():
        age = int(time.time() - HEARTBEAT.stat().st_mtime)
        print(f"heartbeat: {HEARTBEAT.read_text()} (age {age}s)")
    if ALERTS.exists():
        tail = ALERTS.read_text(encoding="utf-8").strip().splitlines()[-5:]
        print("alerts (last 5):\n  " + "\n  ".join(tail))
    return 0


def manual_apply(t):
    """Operator-decided re-apply of the current Train-CV best (a SECOND OOS read for this asset)."""
    t = t.upper()
    con = db_connect()
    a = asset_row(con, t)
    if not a or not a["best_subset_key"]:
        raise SystemExit(f"{t}: no search state / best subset")
    log(f"{t}: MANUAL re-apply of {a['best_subset_key']} (cv {a['best_cv']:.4f}) — operator decision")
    apply_override(t, key_ids(a["best_subset_key"]), a["best_cv"], "manual_reapply")
    rc = run_asset(t)
    if rc == 0:
        set_asset(con, t, status="applied", applied_subset_key=a["best_subset_key"],
                  applied_cv=a["best_cv"], pending_better=0)
        log(f"{t}: re-applied")
        return 0
    alert(f"{t}: manual re-apply run_asset rc={rc}")
    return 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-next", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--apply", metavar="TICKER")
    args = ap.parse_args()
    os.chdir(ROOT)
    if args.status:
        return status()
    if args.plan_next:
        return plan_next()
    if args.apply:
        return manual_apply(args.apply)
    return run_loop()


if __name__ == "__main__":
    sys.exit(main())

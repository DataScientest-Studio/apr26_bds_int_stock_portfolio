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
import seeds  # noqa: E402

ROOT = Path(__file__).resolve().parent
# SEARCH_STATE_DB / SEARCH_OVERRIDES_PATH: test-isolation overrides (integration smokes
# run against a throwaway db + overrides file without touching the live loop's state).
DB_PATH = Path(os.environ.get("SEARCH_STATE_DB") or ROOT / "search_state.db")
CONTROL_PATH = ROOT / "search_control.json"
OVERRIDES_PATH = Path(os.environ.get("SEARCH_OVERRIDES_PATH")
                      or ROOT / "config" / "per_asset_feature_overrides.json")
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
    "min_deep_rounds": 2,          # convergence floor (apply_policy=converged); agent-tunable [2,6]
    "min_train_bars": 3000,        # universe eligibility threshold; consumed once per new ticker
    "apply_policy": "satisfied",   # mirrored from env by the worker; agent READ-ONLY (env wins)
    "priorities": [],
    "paused_tickers": [],
    "stage3_candidates": {},
    "halt": False,
    "notes": "",
}


def resolve_mode():
    """Pure function of env -> (mode, universe, apply_policy).
    SEARCH_UNIVERSE unset  -> 'list' mode: SEARCH_TICKERS (legacy, byte-identical behavior).
    SEARCH_UNIVERSE='all'  -> 'universe' mode: every upstream symbol, ORDER BY symbol ASC.
    SEARCH_UNIVERSE='<T..>'-> 'universe' mode over an explicit list (integration subsets).
    SEARCH_UNIVERSE_LIMIT  -> truncate the universe (smoke tests only)."""
    u = (os.environ.get("SEARCH_UNIVERSE") or "").strip()
    if not u:
        universe = (os.environ.get("SEARCH_TICKERS") or DEFAULT_UNIVERSE).upper().split()
        return "list", universe, os.environ.get("SEARCH_APPLY_POLICY") or "satisfied"
    if u.lower() == "all":
        import duckdb
        con = duckdb.connect(seeds.upstream_path(), read_only=True)
        try:
            universe = [r[0] for r in con.execute(
                "select distinct symbol from ohlcv_1h order by symbol").fetchall()]
        finally:
            con.close()
    else:
        universe = u.upper().split()
    lim = int(os.environ.get("SEARCH_UNIVERSE_LIMIT") or 0)
    if lim:
        universe = universe[:lim]
    return "universe", universe, os.environ.get("SEARCH_APPLY_POLICY") or "converged"

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


def mirror_apply_policy(policy):
    """apply_policy is env-owned: the worker writes the resolved value into the control
    file so the agent can READ it; any later drift in the file is ignored (env wins)."""
    try:
        raw = json.loads(CONTROL_PATH.read_text(encoding="utf-8"))
    except Exception:
        raw = dict(CONTROL_DEFAULTS)
    if raw.get("apply_policy") != policy:
        raw["apply_policy"] = policy
        tmp = CONTROL_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(raw, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, CONTROL_PATH)
        _control_cache["mtime"] = None   # force re-read


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


def db_init(con, universe, mode="list", apply_policy="satisfied", ctl=None):
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
    _migrate_v2(con)
    known = {r[0] for r in con.execute("SELECT ticker FROM assets")}
    new = [t for t in universe if t not in known]
    elig = eligibility_map(new, ctl) if (mode == "universe" and new) else {}
    for t in new:
        verdict = elig.get(t)
        if verdict is not None and not verdict[0]:
            con.execute("INSERT OR IGNORE INTO assets(ticker, status, ineligible_reason, updated_at) "
                        "VALUES(?, 'ineligible', ?, ?)", (t, verdict[1], utcnow()))
        else:
            con.execute("INSERT OR IGNORE INTO assets(ticker, status, updated_at) VALUES(?, 'pending', ?)",
                        (t, utcnow()))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('universe', ?)", (" ".join(universe),))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('mode', ?)", (mode,))
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('apply_policy', ?)", (apply_policy,))
    con.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('started_at', ?)", (utcnow(),))
    con.execute("INSERT OR IGNORE INTO meta(key, value) VALUES('rounds_completed', '0')")
    con.commit()


def _migrate_v2(con):
    """Idempotent schema v2: per-ticker pass/convergence bookkeeping + ineligible reason.
    Backfills deep_rounds_done for a carried-over db (rounds >= 2 were deep by the old shape)."""
    have = {r[1] for r in con.execute("PRAGMA table_info(assets)")}
    if "deep_rounds_done" in have:
        return
    con.executescript("""
    ALTER TABLE assets ADD COLUMN deep_rounds_done INTEGER DEFAULT 0;
    ALTER TABLE assets ADD COLUMN pass_round INTEGER;
    ALTER TABLE assets ADD COLUMN pass_start_best_key TEXT;
    ALTER TABLE assets ADD COLUMN converged_at TEXT;
    ALTER TABLE assets ADD COLUMN ineligible_reason TEXT;
    """)
    con.execute("UPDATE assets SET deep_rounds_done = "
                "(SELECT COUNT(DISTINCT round) FROM evaluations e "
                " WHERE e.ticker = assets.ticker AND e.round >= 2)")
    con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES('schema', 'v2')")
    con.commit()


def eligibility_map(tickers, ctl=None):
    """Universe-mode pre-filter, judged ONCE per new ticker at insert: enough Train-window
    bars upstream to make the frozen split searchable. Returns {ticker: (ok, reason)}.
    A cost optimization, not the correctness boundary (thin-but-eligible tickers that
    die inside CV still park with their exact error)."""
    import duckdb
    thr = int((ctl or CONTROL_DEFAULTS)["min_train_bars"])
    sp = P.PIPELINE_PARAMETERS["splits"]
    con = duckdb.connect(seeds.upstream_path(), read_only=True)
    try:
        rows = con.execute(
            "select symbol, count(*) filter (where ts >= ? and ts <= ?) as train_bars, "
            "cast(min(ts) as varchar) as first_ts, count(*) as n_bars "
            "from ohlcv_1h group by symbol",
            [sp["train_start"], sp["train_end"]]).fetchall()
    finally:
        con.close()
    stats = {s: (tb, f, n) for s, tb, f, n in rows}
    out = {}
    for t in tickers:
        if t not in stats:
            out[t] = (False, f"not found upstream ({seeds.upstream_path()})")
            continue
        tb, first_ts, n = stats[t]
        if tb < thr:
            out[t] = (False, f"train_bars={tb} < min_train_bars={thr} (first_ts={first_ts}, total_bars={n})")
        else:
            out[t] = (True, "")
    return out


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
    """Superset Output-B for one ticker, built once and cached for the round.
    Bars come seed-first-else-upstream (seeds.load_bars) — identical frames by the
    seeds.py parity contract, so search results never depend on the source."""

    def __init__(self, ticker):
        df = seeds.load_bars(ticker)
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

def candidate_stream(con, ctx, phase, ctl):
    """Deterministic candidate generator for (ticker, phase). Yields (subset, stage, source).
    phase='triage' — stage-1 grid ONLY (baselines + 8 block combos); never greedy, never agent.
    phase='deep'   — first deep pass = greedy around the live best; later passes = pair-swap /
                     restart-from-kth-best / add-remove-2, with k derived from the ticker's OWN
                     deep_rounds_done (never the global round — determinism per ticker must not
                     depend on how many rounds other tickers consumed). Agent candidates drain
                     at the end of every deep pass. The stream inspects the db lazily so adopted
                     improvements reshape later candidates."""
    t = ctx.ticker

    def best_ids():
        r = asset_row(con, t)
        return set(key_ids(r["best_subset_key"] or ""))

    if phase == "triage":
        yield [], "grid", "worker"                                     # 1h-only baseline
        yield list(OPTIONAL_IDS), "grid", "worker"                     # all-56 baseline
        for combo in itertools.chain.from_iterable(
                itertools.combinations(("1d", "1w", "multi_tf"), k) for k in (1, 2, 3)):
            yield sorted(i for b in combo for i in BLOCKS[b]), "grid", "worker"
        return                                                          # NO greedy, NO agent drain

    deep_done = asset_row(con, t)["deep_rounds_done"] or 0
    if deep_done == 0:
        # first deep pass: greedy passes around the live best
        for _ in range(64):                                            # pass budget; streak/budget break earlier
            base = best_ids()
            for i in sorted(base):
                yield sorted(base - {i}), "greedy", "worker"
            for i in OPTIONAL_IDS:
                if i not in base:
                    yield sorted(base | {i}), "greedy", "worker"
    else:
        # later deep passes: pair-swap -> restart greedy from k-th best -> add/remove-2
        base = best_ids()
        for i in sorted(base):
            for j in OPTIONAL_IDS:
                if j not in base:
                    yield sorted((base - {i}) | {j}), "swap", "worker"
        k = min(deep_done + 1, 10)
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

    # stage-3: agent candidates (drained every deep pass)
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


def _enter_round(con, t, rnd):
    """Only the very first pass flips pending->searching. A ticker that is already
    satisfied/applied must NEVER have its lifecycle status touched here — resetting
    it would make the apply plane re-fire run_asset (a second OOS read)."""
    a = asset_row(con, t)
    if a["status"] == "pending":
        set_asset(con, t, status="searching", round=rnd)
    else:
        set_asset(con, t, round=rnd)
    return asset_row(con, t)


def triage_ticker(con, t, rnd, ctl, seed, counters):
    """Stage-1 grid only. Never applies, never counts toward convergence."""
    ctx = TickerContext(t)
    _enter_round(con, t, rnd)
    for subset, stage, source in candidate_stream(con, ctx, "triage", ctl):
        ctl = read_control()
        if stop_requested(ctl) or t in ctl["paused_tickers"]:
            return
        evaluate(con, ctx, subset, stage, source, rnd, ctl, seed, counters)
    a = asset_row(con, t)
    if a["baseline_ref"] is None:
        rows = {r["subset_key"]: r["cv_auc_pr"] for r in con.execute(
            "SELECT subset_key, cv_auc_pr FROM evaluations WHERE ticker=? AND subset_key IN (?, ?)",
            (t, "", subset_key(OPTIONAL_IDS)))}
        if len(rows) == 2:
            set_asset(con, t, baseline_ref=max(rows.values()))


def deep_ticker(con, t, rnd, ctl, seed, counters):
    """One deep pass. Opens the pass ONCE (pass_round + pass_start_best_key persisted, so a
    kill-resume replays the same pass over cached evaluations and reaches the identical
    decision). Returns True iff the pass COMPLETED (exhaustion / budget / streak) — an
    interrupted pass returns False and is replayed on the next launch."""
    ctx = TickerContext(t)
    a = _enter_round(con, t, rnd)
    if a["pass_round"] != rnd:
        set_asset(con, t, pass_round=rnd, pass_start_best_key=a["best_subset_key"])
    con.execute("UPDATE assets SET no_improve_streak=0 WHERE ticker=?", (t,))
    con.commit()
    for subset, stage, source in candidate_stream(con, ctx, "deep", ctl):
        ctl = read_control()
        if stop_requested(ctl) or t in ctl["paused_tickers"]:
            return False
        budget = ctl["round_budget_evals"] if (a["deep_rounds_done"] or 0) >= 1 else ctl["stage2_max_evals"]
        if counters["ticker_new"] >= budget:
            break
        evaluate(con, ctx, subset, stage, source, rnd, ctl, seed, counters)
        if stage == "greedy" and asset_row(con, t)["no_improve_streak"] >= ctl["no_improve_N"]:
            break
    return True


def finish_deep_pass(con, t, ctl, policy):
    """CONVERGED(t) := deep_rounds_done >= min_deep_rounds AND (the pass adopted nothing OR it
    ended on a dead streak). Evaluated ONLY after a COMPLETED deep pass, purely from db state.
    A pass with 0 new evaluations (space exhausted) satisfies 'adopted nothing'."""
    a = asset_row(con, t)
    adopted = (a["best_subset_key"] or "") != (a["pass_start_best_key"] or "")
    set_asset(con, t, deep_rounds_done=(a["deep_rounds_done"] or 0) + 1, pass_round=None)
    if policy != "converged" or a["status"] not in ("pending", "searching"):
        return
    a = asset_row(con, t)
    converged = (a["deep_rounds_done"] >= int(ctl["min_deep_rounds"])
                 and (not adopted or (a["no_improve_streak"] or 0) >= ctl["no_improve_N"]))
    if converged:
        set_asset(con, t, status="satisfied", converged_at=utcnow())
        log(f"{t}: CONVERGED after {a['deep_rounds_done']} deep passes (adopted={adopted}) — "
            f"best {a['best_subset_key'] or '(1h-only)'} queued for batch apply")


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


def _apply_and_run(con, t, subset_key_val, cv, attempts_before, stage="auto_first_satisfied"):
    """Apply the winning subset and fire the SINGLE OOS read via run_asset.py. On
    failure, retry up to 3 attempts (across rounds) before parking the ticker —
    a repeatedly-broken run_asset must not spin forever."""
    apply_override(t, key_ids(subset_key_val), cv, stage)
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


def maybe_apply(con, t, ctl, policy="satisfied"):
    """Own the ENTIRE inline apply/OOS lifecycle transition (list mode / policy=satisfied).
    Under policy=converged the inline apply branches are DISABLED — the round-end
    batch_apply owns satisfied->applied — and only the pending_better branch stays live.
    status in (pending, searching) means "never yet satisfied" (_enter_round only ever
    sets searching from pending, never from satisfied/applied)."""
    a = asset_row(con, t)
    if a["best_cv"] is None or a["baseline_ref"] is None:
        return
    sensible = a["best_cv"] >= a["baseline_ref"] + ctl["min_gain"]
    if policy == "satisfied" and a["status"] in ("pending", "searching") and sensible:
        set_asset(con, t, status="satisfied")
        log(f"{t}: satisfied (best_cv={a['best_cv']:.4f} >= baseline {a['baseline_ref']:.4f} + {ctl['min_gain']})")
        _apply_and_run(con, t, a["best_subset_key"], a["best_cv"], a["run_asset_attempts"] or 0)
    elif policy == "satisfied" and a["status"] == "satisfied" and sensible:
        # retry path after a previously failed run_asset (still capped at 3 attempts)
        _apply_and_run(con, t, a["best_subset_key"], a["best_cv"], a["run_asset_attempts"] or 0)
    elif a["status"] == "applied" and a["applied_cv"] is not None \
            and a["best_cv"] > a["applied_cv"] + ctl["epsilon"] and not a["pending_better"]:
        set_asset(con, t, pending_better=1)
        alert(f"{t}: Train-CV best ({a['best_cv']:.4f}) now beats the applied subset "
              f"({a['applied_cv']:.4f}) — pending_better; re-apply is a MANUAL decision "
              f"(make search-apply TICKER={t})")


def batch_apply(con, ctl):
    """Round-end apply plane (policy=converged): every ticker that converged this round is
    applied in ONE batch — export missing seeds (upstream -> data/seed, untracked until the
    user's batch commit), ONE build_db rebuild (L3 drop+recreate, once per round, never per
    ticker), then run_asset sequentially (each the asset's SINGLE OOS read). Crash-safe:
    'satisfied' rows persist, seed export no-ops, the rebuild is idempotent — the next
    round's batch simply retries (run_asset attempts stay capped at 3)."""
    batch = con.execute("SELECT * FROM assets WHERE status='satisfied' ORDER BY ticker").fetchall()
    if not batch:
        return
    log(f"batch apply: {len(batch)} converged ticker(s): {' '.join(a['ticker'] for a in batch)}")
    heartbeat(phase="batch_apply", n=len(batch), grace_s=3600)
    ok = []
    for a in batch:
        try:
            seeds.export_seed(a["ticker"])
            ok.append(a)
        except Exception as e:
            set_asset(con, a["ticker"], status="parked", error=f"seed export: {e!r}"[:500])
            alert(f"{a['ticker']}: PARKED — seed export failed ({e!r})")
    if not ok:
        return
    heartbeat(phase="build_db", grace_s=1800)
    try:
        import build_db
        build_db.build_db()
    except Exception as e:
        alert(f"batch build_db failed ({e!r}) — batch deferred to next round")
        return
    for a in ok:
        if stop_requested(read_control()):
            return
        _apply_and_run(con, a["ticker"], a["best_subset_key"], a["best_cv"],
                       a["run_asset_attempts"] or 0, stage="auto_converged")


# ------------------------------------------------------------------ orders ---

def round_order(con, universe, ctl, mode="list"):
    rows = {r["ticker"]: r for r in con.execute("SELECT * FROM assets")}
    healthy = [t for t in universe if rows.get(t)
               and rows[t]["status"] not in ("parked", "ineligible")
               and t not in ctl["paused_tickers"]]
    prio = [t for t in ctl["priorities"] if t in healthy]
    rest = [t for t in healthy if t not in prio]
    if mode == "list":
        unsat = [t for t in rest if rows[t]["status"] in ("pending", "searching", "satisfied")]
        sat = [t for t in rest if rows[t]["status"] == "applied"]
        return prio + unsat + sat
    # universe mode: triage first (universe order), then deepen by gain rank
    # (gain = best_cv - baseline_ref, tie ticker asc) — COMPUTE ORDERING ONLY, never selection.
    def gain(t):
        r = rows[t]
        if r["best_cv"] is None or r["baseline_ref"] is None:
            return float("-inf")
        return r["best_cv"] - r["baseline_ref"]
    triage = [t for t in rest if rows[t]["baseline_ref"] is None]
    deep = sorted([t for t in rest if rows[t]["baseline_ref"] is not None
                   and rows[t]["status"] != "applied"], key=lambda t: (-gain(t), t))
    applied = sorted([t for t in rest if rows[t]["status"] == "applied"
                      and rows[t]["baseline_ref"] is not None], key=lambda t: (-gain(t), t))
    return prio + triage + deep + applied


def ensure_db_inputs(universe, mode="list"):
    """list mode: seeds precondition + rebuild liora.duckdb if a ticker is missing (as before).
    universe mode: only assert the upstream store is readable — bars come upstream-direct;
    seeds/liora.duckdb materialize at apply time (the batch-apply step owns them)."""
    if mode == "universe":
        import duckdb
        con = duckdb.connect(seeds.upstream_path(), read_only=True)
        con.execute("select 1 from ohlcv_1h limit 1").fetchone()
        con.close()
        return
    missing_seed = [t for t in universe if not seeds.seed_path(t).exists()]
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
    mode, universe, policy = resolve_mode()
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ensure_db_inputs(universe, mode)
    con = db_connect()
    ctl = read_control()
    db_init(con, universe, mode, policy, ctl)
    mirror_apply_policy(policy)
    log(f"worker up: mode={mode}, apply_policy={policy}, universe={len(universe)} tickers, "
        f"optional ids={len(OPTIONAL_IDS)}")
    while True:
        ctl = read_control()
        if stop_requested(ctl):
            heartbeat(phase="halted")
            log("halt/stop requested — exiting 3")
            return 3
        order = round_order(con, universe, ctl, mode)
        if not order:
            alert("all tickers parked/paused/ineligible — sleeping 300s")
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
                if asset_row(con, t)["baseline_ref"] is None:
                    triage_ticker(con, t, rnd, ctl, seed, counters)   # ~9 evals, NEVER applies
                else:
                    completed = deep_ticker(con, t, rnd, ctl, seed, counters)
                    if completed:
                        finish_deep_pass(con, t, read_control(), policy)
                maybe_apply(con, t, read_control(), policy)
            except Exception as e:
                set_asset(con, t, status="parked", error=repr(e)[:500])
                alert(f"{t}: PARKED — {e!r}")
                log(traceback.format_exc())
        if policy == "converged":
            batch_apply(con, read_control())
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
    mode, universe, policy = resolve_mode()
    if not DB_PATH.exists():
        print(f"{universe[0]}\t(db absent — first candidate is the 1h-only baseline: '')")
        return 0
    con = db_connect()
    db_init(con, universe, mode, policy, read_control())
    ctl = read_control()
    order = round_order(con, universe, ctl, mode)
    for t in order:
        ctx = type("Stub", (), {"ticker": t})()   # candidate_stream needs only .ticker
        phase = "triage" if asset_row(con, t)["baseline_ref"] is None else "deep"
        for subset, stage, _ in candidate_stream(con, ctx, phase, ctl):
            key = subset_key(subset)
            if not con.execute("SELECT 1 FROM evaluations WHERE ticker=? AND subset_key=?",
                               (t, key)).fetchone():
                print(f"{t}\t{phase}\t{stage}\t{key}")
                return 0
    print("(no new candidate in the current round shape)")
    return 0


def status():
    if not DB_PATH.exists():
        print("no search_state.db yet — run `make search-on`")
        return 0
    con = db_connect(readonly=True)
    meta = dict(con.execute("SELECT key, value FROM meta"))
    rows = list(con.execute("SELECT * FROM assets"))
    counts = {}
    for r in rows:
        counts[r["status"] or "-"] = counts.get(r["status"] or "-", 0) + 1
    eligible = [r for r in rows if r["status"] != "ineligible"]
    triaged = sum(1 for r in eligible if r["baseline_ref"] is not None)
    print(f"mode={meta.get('mode', 'list')}  apply_policy={meta.get('apply_policy', 'satisfied')}  "
          f"counts: {' '.join(f'{k}={v}' for k, v in sorted(counts.items()))}  "
          f"triage: {triaged}/{len(eligible)} eligible")

    def gain(r):
        if r["best_cv"] is None or r["baseline_ref"] is None:
            return None
        return r["best_cv"] - r["baseline_ref"]

    rows.sort(key=lambda r: (-(gain(r) if gain(r) is not None else float("-inf")), r["ticker"]))
    print(f"{'ticker':7s} {'status':10s} {'round':>5s} {'deep':>4s} {'evals':>6s} {'baseline':>9s} "
          f"{'best_cv':>9s} {'gain':>8s} {'applied':>9s} {'pend':>4s}  best_subset")
    for r in rows:
        fmt = lambda v: f"{v:.4f}" if v is not None else "-"
        g = gain(r)
        has_v2 = "deep_rounds_done" in r.keys()   # readonly view of a not-yet-migrated v1 db
        tail = (r["ineligible_reason"] if has_v2 and r["status"] == "ineligible"
                else (r["best_subset_key"] or "-"))
        deep = r["deep_rounds_done"] if has_v2 else 0
        print(f"{r['ticker']:7s} {r['status'] or '-':10s} {r['round'] or 0:5d} {deep or 0:4d} "
              f"{r['evals_count'] or 0:6d} {fmt(r['baseline_ref']):>9s} {fmt(r['best_cv']):>9s} "
              f"{fmt(g):>8s} {fmt(r['applied_cv']):>9s} {r['pending_better'] or 0:4d}  {tail}")
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


def selfcheck():
    """No-network-write, no-OOS sanity of the universe-mode machinery. EVERYTHING it touches
    is redirected into a throwaway dir (db, overrides, alerts, heartbeat) so a selfcheck can
    run next to the live loop without polluting its state."""
    import tempfile
    global DB_PATH, OVERRIDES_PATH, ALERTS, HEARTBEAT
    tmpdir = tempfile.mkdtemp(prefix="fsw_selfcheck_")
    DB_PATH = Path(tmpdir) / "t.db"
    OVERRIDES_PATH = Path(tmpdir) / "overrides.json"
    ALERTS = Path(tmpdir) / "ALERTS.txt"
    HEARTBEAT = Path(tmpdir) / "heartbeat.json"

    # 1. universe provider determinism
    os.environ["SEARCH_UNIVERSE"] = "all"
    m1 = resolve_mode()
    m2 = resolve_mode()
    assert m1 == m2 and m1[0] == "universe" and m1[2] == "converged"
    assert len(m1[1]) == 503 and m1[1] == sorted(m1[1]) and "BF.B" in m1[1] and "BRK.B" in m1[1]
    print("1. universe provider deterministic (503 asc, dotted present)")

    # 2. eligibility: Q ineligible, AAPL eligible
    e = eligibility_map(["Q", "AAPL"])
    assert not e["Q"][0] and "min_train_bars" in e["Q"][1]
    assert e["AAPL"][0]
    print("2. eligibility: Q ->", e["Q"][1][:50], "| AAPL eligible")

    # 3. seed <-> upstream parity
    import pandas as pd
    pd.testing.assert_frame_equal(pd.read_parquet(seeds.seed_path("AAPL")),
                                  seeds.load_bars_from_upstream("AAPL"))
    print("3. AAPL seed == upstream transform (frame-equal)")

    # 4. converged predicate on fabricated states
    con = db_connect()
    os.environ["SEARCH_UNIVERSE"] = "AAPL"
    db_init(con, ["AAPL"], "universe", "converged", dict(CONTROL_DEFAULTS))
    ctl = dict(CONTROL_DEFAULTS)
    cases = [  # (deep_before, pass_start_key, best_key, streak, expect_satisfied)
        (0, "101", "101", 0, False),    # only 1 completed pass -> below min_deep_rounds
        (1, "101", "101,201", 3, False),  # adopted + live streak -> not converged
        (1, "101", "101", 0, True),     # >=2 passes, adopted nothing -> converged
        (1, "101", "101,201", 8, True),  # adopted but ended on dead streak -> converged
    ]
    for i, (deep, start_key, best_key, streak, expect) in enumerate(cases, 1):
        set_asset(con, "AAPL", status="searching", deep_rounds_done=deep, pass_round=99,
                  pass_start_best_key=start_key, best_subset_key=best_key,
                  no_improve_streak=streak, converged_at=None)
        finish_deep_pass(con, "AAPL", ctl, "converged")
        got = asset_row(con, "AAPL")["status"] == "satisfied"
        assert got == expect, f"case {i}: expected {expect}, got {got}"
    print("4. converged predicate: 4/4 fabricated cases")

    # 5. batch path with a stubbed run_asset
    global run_asset
    real_run_asset, real_export = run_asset, seeds.export_seed
    try:
        seeds.export_seed = lambda t: None
        run_asset = lambda t: 0
        set_asset(con, "AAPL", status="satisfied", best_subset_key="101", best_cv=0.6,
                  run_asset_attempts=0)
        import build_db as _bdb
        real_build = _bdb.build_db
        _bdb.build_db = lambda: None
        try:
            batch_apply(con, ctl)
        finally:
            _bdb.build_db = real_build
        a = asset_row(con, "AAPL")
        assert a["status"] == "applied" and a["applied_subset_key"] == "101"
        run_asset = lambda t: 1
        for _ in range(3):
            set_asset(con, "AAPL", status="satisfied")
            _apply_and_run(con, "AAPL", "101", 0.6, asset_row(con, "AAPL")["run_asset_attempts"] or 0,
                           stage="auto_converged")
        assert asset_row(con, "AAPL")["status"] == "parked"
        print("5. batch apply: success->applied; 3 failures->parked")
    finally:
        run_asset, seeds.export_seed = real_run_asset, real_export
    print("SELFCHECK OK")
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan-next", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--apply", metavar="TICKER")
    ap.add_argument("--selfcheck", action="store_true")
    args = ap.parse_args()
    os.chdir(ROOT)
    if args.status:
        return status()
    if args.plan_next:
        return plan_next()
    if args.apply:
        return manual_apply(args.apply)
    if args.selfcheck:
        return selfcheck()
    return run_loop()


if __name__ == "__main__":
    sys.exit(main())

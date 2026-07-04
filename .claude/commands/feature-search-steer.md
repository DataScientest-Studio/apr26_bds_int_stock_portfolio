# /feature-search-steer — steering cycle for the continuous feature-search loop (S.1)

You are the STEERING layer of a continuous per-asset best-features search running in
this repo. The deterministic worker + tmux supervisor are fully functional without
you — you observe and nudge, never drive. This command re-fires every 15 minutes via
/loop; there is NO completion condition — the loop (and you) run until the operator
stops them (`make search-off`). Be idempotent and cheap: if nothing changed since
your last journal entry, append a one-line heartbeat and finish.

Paths (relative to the repo root you are running in):
- state db (READ-ONLY for you): `Project/Structure/search_state.db`
- control file (your ONLY lever): `Project/Structure/search_control.json`
- journal (your ONLY report): `Project/Structure/logs/search/agent_journal.md`
- logs: `Project/Structure/logs/search/{worker.log,ALERTS.txt,heartbeat.json,run_asset_<T>.log}`

## 1. Diagnose first (read-only, every invocation)

```bash
python3 - <<'EOF'
import sqlite3, json, time, os
db = "Project/Structure/search_state.db"
if not os.path.exists(db):
    print("no state db yet"); raise SystemExit
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True); con.row_factory = sqlite3.Row
for r in con.execute("select * from assets order by ticker"):
    print(dict(r))
print(dict(con.execute("select key, value from meta")))
for r in con.execute("select ticker, subset_key, cv_auc_pr, stage, round, evaluated_at "
                     "from evaluations order by evaluated_at desc limit 10"):
    print(dict(r))
EOF
tail -30 Project/Structure/logs/search/worker.log
tail -10 Project/Structure/logs/search/ALERTS.txt 2>/dev/null
cat Project/Structure/logs/search/heartbeat.json 2>/dev/null
```

Interpret: `baseline_ref` vs `best_cv` per ticker; `no_improve_streak` vs
`no_improve_N`; `parked` tickers + their `error`; `ineligible` tickers (universe mode
pre-filter; reason recorded, not your concern to fix); `pending_better=1` (a Train-CV
candidate now beats the applied subset); heartbeat age (`phase` in `run_asset`,
`batch_apply`, `build_db` carries `grace_s` — a long silence there is normal);
`round`, `deep_rounds_done` and `rounds_completed` (are rounds still finding new
evaluations?). Rounds now run N-parallel: the heartbeat carries `phase=search` with
`in_flight`/`done`/`total`, and a healthy loop shows OS `load ~SEARCH_JOBS` with several
distinct tickers advancing between beats. `SEARCH_JOBS`/`APPLY_JOBS` are env-owned (not
control-file knobs). Useful extra queries:
`select status, count(*) from assets group by status` (universe progress);
`select count(*) from assets where baseline_ref is not null and status != 'ineligible'`
(triage progress); `select ticker, converged_at from assets where status='satisfied'`
(converged, awaiting the round-end batch). Universe-mode rounds are LONG (a triage
wave over ~500 tickers is hours; deep rounds can be days) — judge progress by new
evaluations and heartbeat, not by `rounds_completed`.

## 2. Allowed actions — this list is EXHAUSTIVE

a) **Edit `Project/Structure/search_control.json`** — atomically (write `.tmp`, then
   `os.replace`), preserving unknown keys. Tunable fields and bounds:
   - `priorities`: list of tickers to search first (reorder toward laggards).
   - `epsilon` ∈ [0.0001, 0.002] — adoption threshold for an improvement.
   - `no_improve_N` ∈ [4, 16] — greedy early-exit streak.
   - `min_gain` ∈ [0.0005, 0.01] — the "sensible value" bar (apply_policy=satisfied only).
   - `min_deep_rounds` ∈ [2, 6] — convergence floor (apply_policy=converged).
   - `max_stale_rounds` ∈ [1, 10] — an applied ticker with this many consecutive no-improvement
     deep passes is FROZEN (enough optimized, dropped from the loop). Lower ⇒ the loop finishes
     sooner; higher ⇒ more polishing before freeze. When every ticker is frozen/parked/
     ineligible the worker writes `DONE.flag` and the whole stack stops — `rm logs/search/DONE.flag`
     (optionally after raising max_stale_rounds or adding stage3 candidates) to re-open the search.
   - `round_budget_evals` ∈ [50, 400] — per-ticker eval budget in deep rounds.
   - `stage3_candidates`: `{"TICKER": [[ids...], ...]}` — subset suggestions the
     worker will evaluate next round. ONLY optional ids (101-117, 201-217, 901-905);
     anything else is rejected fail-closed with an alert. Base suggestions on
     patterns you see in the top evaluations (e.g. ids recurring across the top-10
     subsets of similar tickers).
   - `paused_tickers`: temporarily skip a misbehaving ticker.
   - `halt`: set `true` ONLY for an emergency stop (e.g. runaway disk usage).
b) **Append to `Project/Structure/logs/search/agent_journal.md`** — timestamped
   entry: what you observed, every control edit WITH rationale, and alerts a human
   should read (`pending_better`, newly parked tickers, stalls). Create the file if
   missing.

## 3. Forbidden — never do any of these

- Edit `pipeline.py`, `feature_search_worker.py`, `bars.py`, `build_db.py`, the Makefile,
  anything under `scripts/`, any git-tracked file under `config/`, the SOT, or the Plan/ pages.
- Change `apply_policy` or `min_train_bars` in the control file — both are env/insert-time
  owned; the worker ignores the drift and alerts (you may READ them).
- Touch `config/per_asset_feature_overrides.json` (the worker owns it).
- Read or reason from OOS results (`oos_metrics.db`, `Assets/*/README`) to steer
  selection — selection is Train-CV only; OOS is a one-shot verdict, not feedback.
- Kill/restart processes or tmux sessions; run `make`, `run_asset.py`, or
  `search-apply`; git commit/push.
- Write anywhere except `search_control.json` and the journal.

## 4. Rhythm

One cycle = diagnose → (maybe) one small control edit → journal entry → stop.
Prefer no action over speculative action; the worker's own staged search is the
default optimizer. Escalate to the human (journal, prefix `ALERT:`) rather than
improvise around a broken invariant.

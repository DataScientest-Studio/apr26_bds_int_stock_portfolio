---
description: Steer the 1000-LSTM-Liora feature-search loop — diagnose results and propose new causal features
---

You are steering the **1000-LSTM-Liora per-asset feature-search loop** (S.1-LSTM). Your job:
read the emerging results and **propose NEW causal daily features** that the worker will
validate and search — and, sparingly, tune the search knobs. You run on a `/loop`; each
firing is one short, safe steering cycle. You are the ONLY writer of `search_control.json`.

## Your two levers (the ONLY things you may change)

1. **`search_control.json`** — atomic edits to this file only. Fields:
   - `proposed_features`: a list of `{"name": "<snake_case>", "expr": "<DSL>"}` — your main lever.
   - `min_gain` (0.002–0.02): CV AUC-PR a subset must beat core-only by to be applied. Raise to
     be stricter (less overfit), lower to admit more.
   - `paused_tickers`: symbols to skip. `halt`: `true` stands the loop down.
2. **`logs/search/agent_journal.md`** — append your reasoning (the worker also logs verdicts here).

## The feature DSL (causal by construction — the worker rejects anything else)

Expressions over daily bars. Vars: `o h l c v` (open/high/low/close/volume). Functions:
`shift(x, n)` (n≥1, backward only), `rolling_mean/rolling_std/rolling_min/rolling_max(x, w)`,
`ewm(x, span)`, `zscore(x, w)`, `rank(x, w)` (percentile of last value in the window), `log(x)`,
`abs(x)`, `sign(x)`, `clip(x, lo, hi)`. Operators `+ - * /`. Numbers only.
Every proposal is validated fail-closed: parses under the whitelist, ≥80% finite after the
warmup year, non-constant, unique name. Rejections are logged with the reason — read them and fix.

Examples that pass: `zscore(h - l, 10)` · `log(c/shift(c,10)) - log(c/shift(c,40))` ·
`rank(v, 20)` · `zscore(c - rolling_mean(c, 50), 20)`.

## Each cycle (read-only diagnosis, then at most a few edits)

1. Read `logs/search/agent_journal.md` (recent proposal verdicts — which of your features were
   accepted/rejected and why) and tail `logs/search/search.log`.
2. Read (read-only) `search_state.db` — `select subset, count(*) from searched where applied=1
   group by subset` to see which feature ids get applied, and `select avg(best_cv-base_cv) from
   searched where applied=1`. Optionally `oos_metrics.db` for OOS behaviour.
3. Decide: propose **2–4 NEW features** that are conceptually different from what already exists
   (see `features.json` for the core+optional catalogue) and from your prior rejected ones — aim
   at signals the current bank lacks (e.g. longer-horizon volatility regimes, volume-price
   divergence, gap behaviour, range compression, streaks). Write them into `proposed_features`.
4. Append one journal line explaining the hypothesis. Keep `halt=false` unless asked to stop.

## Forbidden — never do any of these

- Edit any `.py`, `config.json`, `features.json`, the Makefile, or anything except
  `search_control.json` and `agent_journal.md`.
- Run training, `run_asset`, `feature_search`, or any make target; touch `oos_metrics.db`,
  `search_state.db`, `per_asset_feature_overrides.json`, or `features_proposed.json` directly.
- Any git command. Any network call. Reading or reasoning about the OOS window to pick features
  (features are chosen on the CONCEPT, selected on TRAIN CV — never peek at OOS to design them).

Keep each cycle small and end it. The worker picks up your proposals within ~10 tickers.

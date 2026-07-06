"""Ingest Sonnet-proposed causal features into the pool (offline-safe: proposals are validated and
frozen into features_proposed.json BEFORE the run; the 8h loop then evaluates them deterministically).

- `ingest(features, universe)` validates each proposal (grammar/causality by DSL + >=99% finite +
  non-constant + bounded + |rho|<0.95 vs the current pool on a sample ticker) and appends the valid
  ones (atomic + fcntl-locked, monotonic id>=501).
- `python -m fs.propose --ingest FILE.json` — bulk-ingest a `[{name, expr, rationale?}]` list.
- `python -m fs.propose --from-claude [--universe U]` — ONE round of the optional live proposer:
  build a prompt from the current selected + SHAP, call `claude --model sonnet -p`, parse, ingest.
  This is a BONUS; the run never depends on it.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

from . import FS_ROOT, art_dir, read_json
from . import data, dsl

PROPOSED_PATH = data.PROPOSED_PATH
CORR_MAX = 0.95
SAMPLE_TICKERS = {"demo": ["AAPL", "KO", "XOM"], "full": ["AAPL", "MSFT", "JPM", "XOM"]}


def _lock_and_update(new_valid):
    """Append validated {name:{id,expr,rationale,added}} atomically under an fcntl lock."""
    import fcntl
    lock = PROPOSED_PATH.with_suffix(".lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    with open(lock, "w") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        reg = dsl.proposed_registry(PROPOSED_PATH)
        nid = int(reg.get("_next_id", 501))
        added = []
        for name, expr, rationale in new_valid:
            if name in reg:
                continue
            reg[name] = {"id": nid, "expr": expr, "rationale": rationale}
            nid += 1
            added.append(name)
        reg["_next_id"] = nid
        tmp = PROPOSED_PATH.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(reg, indent=2, sort_keys=True) + "\n")
        os.replace(tmp, PROPOSED_PATH)
        fcntl.flock(lf, fcntl.LOCK_UN)
    return added


def ingest(features, universe="full", verbose=True):
    """Validate proposals against the grammar + a real sample ticker; return the names accepted."""
    sample_tk = SAMPLE_TICKERS.get(universe, SAMPLE_TICKERS["full"])
    # sample frame with the CURRENT pool (base + already-accepted proposed) for the correlation gate
    bars, feats = data.bar_frame(sample_tk[0], universe)
    known = set(feats.columns) | set(dsl.proposed_names(PROPOSED_PATH))
    valid, rejected = [], []
    for f in features:
        name, expr = f.get("name", ""), f.get("expr", "")
        rationale = f.get("rationale", "")
        ok, reason = dsl.validate_proposal(name, expr, bars, known)
        if ok:
            try:
                vals = dsl.dsl_eval(expr, bars)
                if dsl.max_abs_corr(vals, feats) >= CORR_MAX:
                    ok, reason = False, f"redundant (|rho|>={CORR_MAX} vs existing)"
            except Exception as e:  # noqa: BLE001
                ok, reason = False, f"eval failed: {e}"
        # cross-check it also evaluates on the other sample tickers (one odd ticker shouldn't pass it)
        if ok:
            for tk in sample_tk[1:]:
                b2, _ = data.bar_frame(tk, universe)
                v2 = dsl.dsl_eval(expr, b2)
                if np.isfinite(v2[dsl.WARMUP_1H:]).mean() < 0.95:
                    ok, reason = False, f"only {np.isfinite(v2[dsl.WARMUP_1H:]).mean():.0%} finite on {tk}"
                    break
        if ok:
            valid.append((name, expr, rationale))
            known.add(name)
        else:
            rejected.append((name, reason))
    added = _lock_and_update(valid) if valid else []
    if verbose:
        print(f"[propose] {len(features)} proposals -> {len(added)} accepted, {len(rejected)} rejected")
        for nm, why in rejected[:20]:
            print(f"  reject {nm}: {why}")
        if added:
            print(f"  accepted: {added}")
    return added


# ---------------- optional live proposer ----------------

def build_prompt(universe):
    grammar = (FS_ROOT / "dsl.py").read_text().split('"""')[1]  # the module docstring = grammar summary
    champ = read_json(art_dir(universe) / "selected_xgb.json") if (art_dir(universe) / "selected_xgb.json").exists() else {}
    known = sorted(set(data.feature_pool()))
    return (
        "You propose NEW causal 1h features (safe DSL) for an S&P500 triple-barrier classifier.\n"
        "Grammar: variables o,h,l,c,v (Series); funcs shift(x,n>=1), rolling_{mean,std,min,max}(x,w), "
        "ewm(x,span), zscore(x,w), rank(x,w), log/abs/sign/clip; + - * /; no other names, no shift(x,0).\n"
        "Every feature: stationary/bounded/signed (NEVER a raw price), >=99% finite after ~500 bars.\n"
        f"Existing pool (do NOT duplicate): {known}\n"
        f"Current XGB selected: {champ.get('selected', [])}\n"
        'Return ONLY a JSON array: [{"name":"snake_case","expr":"<dsl>","rationale":"why"}], 6-10 items.')


def one_live_round(universe):
    prompt = build_prompt(universe)
    try:
        r = subprocess.run(["claude", "--model", "sonnet", "-p", prompt],
                           capture_output=True, text=True, timeout=180, stdin=subprocess.DEVNULL)
        out = r.stdout.strip()
        s, e = out.find("["), out.rfind("]")
        feats = json.loads(out[s:e + 1]) if s >= 0 and e > s else []
    except Exception as ex:  # noqa: BLE001
        print(f"[propose] live claude round failed (non-fatal): {ex}")
        return []
    return ingest(feats, universe)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--universe", choices=["demo", "full"], default="full")
    ap.add_argument("--ingest", metavar="FILE", help="bulk-ingest a [{name,expr,rationale}] JSON file")
    ap.add_argument("--from-claude", action="store_true", help="one live Sonnet proposal round")
    a = ap.parse_args()
    if a.ingest:
        feats = json.loads(Path(a.ingest).read_text())
        ingest(feats if isinstance(feats, list) else feats.get("features", []), a.universe)
    elif a.from_claude:
        one_live_round(a.universe)
    else:
        print("nothing to do (use --ingest FILE or --from-claude)", file=sys.stderr)


if __name__ == "__main__":
    main()

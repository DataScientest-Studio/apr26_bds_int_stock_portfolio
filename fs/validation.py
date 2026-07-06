"""Shared validation module (WO-FS-XGB §3 = WO-FS-LSTM §2).

All splits operate on the pooled panel via TIMESTAMP intervals, not row indices: each event i
carries [t_start_i, t1_i] — its full information span (t_start = t0 for flat XGB rows; t0 minus
L sequence bars for the LSTM, which realizes the WO's purge = L + H). One rule does both purge
and embargo: a train event is kept iff its span ends before the test block starts, OR its span
starts after the test block ends + embargo. Embargo ≈ embargo_frac of the CV window duration.

CPCV: N=6 contiguous groups, 2 test per split -> C(6,2)=15 splits; each group is tested in
exactly 5 splits, from which 5 full OOS paths are assembled (path p uses, for every group, its
p-th testing split in sorted split order).

Holdout-once: the flag file artifacts/<universe>/holdout_used.flag makes a second holdout read
raise — the WO's 'użyty dokładnie raz' as code, not convention.
"""
from itertools import combinations

import numpy as np
import pandas as pd

from . import CONFIG, art_dir, write_json


def _as_ns(ts):
    return pd.to_datetime(ts, utc=True).astype("int64").to_numpy() if not isinstance(ts, np.ndarray) else ts


def time_group_bounds(t0_ns, n_groups):
    """Contiguous time-group boundaries with (approximately) equal event counts: quantiles of t0.
    Returns [lo_0, b_1, ..., b_{n-1}, hi] as int64 ns; group g = [bounds[g], bounds[g+1])."""
    qs = np.quantile(t0_ns, np.linspace(0, 1, n_groups + 1))
    qs[0] -= 1  # make the first group inclusive of the earliest event
    qs[-1] += 1
    return qs.astype(np.int64)


def _keep_train(t_start, t1, test_lo, test_hi, embargo_ns):
    """The purge+embargo rule (vectorized): train event survives one test block iff it is
    entirely before it, or starts after the block plus embargo."""
    return (t1 < test_lo) | (t_start > test_hi + embargo_ns)


def embargo_ns():
    lo = pd.Timestamp(CONFIG["SPLITS"]["cv_start"], tz="UTC").value
    hi = pd.Timestamp(CONFIG["SPLITS"]["cv_end"], tz="UTC").value
    return int(CONFIG["CV"]["embargo_frac"] * (hi - lo))


def purged_kfold(t0_ts, t1_ts, t_start_ts=None, k=None):
    """Purged K-Fold with embargo on the pooled panel. Folds are contiguous TIME blocks (equal
    event counts). Returns [(train_idx, test_idx)] with numpy int index arrays."""
    k = int(k or CONFIG["CV"]["k"])
    t0 = _as_ns(pd.Series(t0_ts))
    t1 = _as_ns(pd.Series(t1_ts))
    ts = t0 if t_start_ts is None else _as_ns(pd.Series(t_start_ts))
    emb = embargo_ns()
    bounds = time_group_bounds(t0, k)
    folds = []
    for g in range(k):
        lo, hi = bounds[g], bounds[g + 1]
        test = np.nonzero((t0 >= lo) & (t0 < hi))[0]
        keep = _keep_train(ts, t1, lo, hi, emb)
        train = np.nonzero(keep & ~((t0 >= lo) & (t0 < hi)))[0]
        if len(test) >= 5 and len(train) >= 10:
            folds.append((train, test))
    if not folds:
        raise RuntimeError("purged_kfold produced no usable folds")
    return folds


def cpcv_splits(t0_ts, t1_ts, t_start_ts=None, n_groups=None, n_test=None):
    """Combinatorial Purged CV. Returns (splits, group_of_event, n_groups) where splits is a list
    of dicts {test_groups, train_idx, test_idx} in deterministic sorted order."""
    n_groups = int(n_groups or CONFIG["CPCV"]["n_groups"])
    n_test = int(n_test or CONFIG["CPCV"]["n_test_groups"])
    t0 = _as_ns(pd.Series(t0_ts))
    t1 = _as_ns(pd.Series(t1_ts))
    ts = t0 if t_start_ts is None else _as_ns(pd.Series(t_start_ts))
    emb = embargo_ns()
    bounds = time_group_bounds(t0, n_groups)
    group = np.searchsorted(bounds, t0, side="right") - 1
    group = np.clip(group, 0, n_groups - 1)
    splits = []
    for gs in combinations(range(n_groups), n_test):
        test = np.nonzero(np.isin(group, gs))[0]
        keep = np.ones(len(t0), bool)
        for g in gs:
            keep &= _keep_train(ts, t1, bounds[g], bounds[g + 1], emb)
        train = np.nonzero(keep & ~np.isin(group, gs))[0]
        splits.append({"test_groups": tuple(gs), "train_idx": train, "test_idx": test})
    return splits, group, n_groups


def cpcv_paths(splits, n_groups):
    """Assemble the φ = n_splits·n_test/n_groups full OOS paths: for each group, its testing
    splits in order; path p takes the p-th. Returns list of {group -> split_index}."""
    testing = {g: [i for i, s in enumerate(splits) if g in s["test_groups"]] for g in range(n_groups)}
    n_paths = min(len(v) for v in testing.values())
    return [{g: testing[g][p] for g in range(n_groups)} for p in range(n_paths)]


# ---------------- window masks + holdout-once guard ----------------

def window_mask(t0_ts, which):
    s = CONFIG["SPLITS"]
    t0 = pd.to_datetime(pd.Series(t0_ts), utc=True)
    if which == "cv":
        return ((t0 >= pd.Timestamp(s["cv_start"], tz="UTC"))
                & (t0 <= pd.Timestamp(s["cv_end"], tz="UTC") + pd.Timedelta(days=1))).to_numpy()
    if which == "holdout":
        return ((t0 >= pd.Timestamp(s["holdout_start"], tz="UTC"))
                & (t0 <= pd.Timestamp(s["holdout_end"], tz="UTC") + pd.Timedelta(days=1))).to_numpy()
    raise ValueError(which)


def purge_cv_boundary(panel):
    """Fail-closed pre-holdout purge: drop CV events whose label span + embargo crosses the
    holdout start; assert none survive (mirrors lstm/pipeline.py purge_train_events)."""
    hs = pd.Timestamp(CONFIG["SPLITS"]["holdout_start"], tz="UTC").value
    t1 = _as_ns(panel["t1_ts"])
    keep = t1 + embargo_ns() <= hs
    out = panel[keep].reset_index(drop=True)
    assert (_as_ns(out["t1_ts"]) + embargo_ns() <= hs).all(), "CV event label crosses into holdout"
    return out, int((~keep).sum())


def holdout_guard(universe, model, payload):
    """Create the one-shot flag for (universe, model); raise if it exists. Records what was read."""
    flag = art_dir(universe) / f"holdout_used_{model}.flag"
    if flag.exists():
        raise RuntimeError(f"holdout for {model}/{universe} was already read once ({flag}); "
                           "the WO forbids a second read — delete the flag ONLY to void the study")
    write_json(flag, payload)
    return flag

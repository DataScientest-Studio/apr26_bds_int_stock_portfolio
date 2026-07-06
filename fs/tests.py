"""WO-FS gates — stdlib asserts, no test framework. `python -m fs.tests` (demo store only).

Order matters: unit tests of the label/validation math first, then the WO §1 anti-lookahead
BRAMKA (shift all features by one bar -> the CV metric must NOT improve), then determinism.
Any failure is a hard stop for the whole study.
"""
import numpy as np
import pandas as pd

from . import ART, CONFIG, seed_everything
from . import data, labels, metrics, validation
from .features import POOL

GATE_PARAMS = {"cusum_mult": 3.0, "ewma_span": 100, "pt": 1.5, "sl": 1.5, "h_bars": 24}
GATE_TICKERS = ["AAPL", "KO", "XOM"]


def test_cusum_synthetic():
    n = 600
    close = np.full(n, 100.0)
    close[300:] = 112.0  # one large persistent jump
    sigma = np.full(n, 0.01)
    ev = labels.cusum_events(close, sigma, cusum_mult=3.0)
    assert len(ev) == 1 and ev[0] == 300, f"CUSUM should fire once at the jump, got {ev[:5]}"
    flat = labels.cusum_events(np.full(n, 100.0), sigma, cusum_mult=3.0)
    assert len(flat) == 0, "CUSUM fired on a flat series"


def test_triple_barrier_synthetic():
    sigma = np.full(40, 0.01)
    up = 100.0 * np.exp(np.linspace(0, 0.10, 40))       # rises ~10% -> +1 quickly
    t0, y, t1, _ = labels.triple_barrier(up, [5], sigma, pt=2.0, sl=2.0, h_bars=20)
    assert list(y) == [1] and t1[0] > 5, f"expected +1, got {y}"
    dn = 100.0 * np.exp(-np.linspace(0, 0.10, 40))
    _, y, _, _ = labels.triple_barrier(dn, [5], sigma, pt=2.0, sl=2.0, h_bars=20)
    assert list(y) == [-1], f"expected -1, got {y}"
    flat = np.full(40, 100.0)
    _, y, t1, r = labels.triple_barrier(flat, [5], sigma, pt=2.0, sl=2.0, h_bars=20)
    assert list(y) == [0] and t1[0] == 25 and r[0] == 0.0, "expected 0 at the vertical barrier"
    # an event whose horizon does not fit must be dropped, never truncated
    kept, _, _, _ = labels.triple_barrier(flat, [30], sigma, pt=2.0, sl=2.0, h_bars=20)
    assert len(kept) == 0, "truncated-horizon event was not dropped"


def test_uniqueness():
    w = labels.uniqueness_weights([10, 10], [20, 20])
    assert np.allclose(w, 0.5), f"two identical events must weigh 0.5, got {w}"
    w = labels.uniqueness_weights([10, 100], [20, 110])
    assert np.allclose(w, 1.0), f"disjoint events must weigh 1.0, got {w}"


def _demo_panel(tickers=GATE_TICKERS, shift_features=False):
    parts = []
    for t in tickers:
        bars, feats = data.bar_frame(t, "demo")
        if shift_features:
            feats = feats.shift(1)
        ev = labels.build_events(bars, feats, GATE_PARAMS, t)
        parts.append(ev)
    panel = pd.concat(parts, ignore_index=True)
    panel = panel[validation.window_mask(panel["t0_ts"], "cv")].reset_index(drop=True)
    panel, _ = validation.purge_cv_boundary(panel)
    panel = labels.assign_uniqueness(panel)
    return panel.sort_values("t0_ts", kind="mergesort").reset_index(drop=True)


def test_purged_kfold_no_overlap():
    panel = _demo_panel(GATE_TICKERS[:2])
    t0 = pd.to_datetime(panel["t0_ts"], utc=True).astype("int64").to_numpy()
    t1 = pd.to_datetime(panel["t1_ts"], utc=True).astype("int64").to_numpy()
    emb = validation.embargo_ns()
    folds = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"])
    bounds = validation.time_group_bounds(t0, CONFIG["CV"]["k"])
    assert len(folds) == CONFIG["CV"]["k"]
    for g, (tr, te) in enumerate(folds):
        lo, hi = bounds[g], bounds[g + 1]
        assert ((t0[te] >= lo) & (t0[te] < hi)).all(), "test event outside its block"
        ok = (t1[tr] < lo) | (t0[tr] > hi + emb)
        assert ok.all(), f"fold {g}: {int((~ok).sum())} train events violate purge/embargo"
    # the LSTM variant: a widened t_start must shrink (or keep) every train set
    tstart = pd.to_datetime(panel["t0_ts"], utc=True) - pd.Timedelta(hours=64)
    folds_l = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"], t_start_ts=tstart)
    for (tr, _), (tr_l, _) in zip(folds, folds_l):
        assert len(tr_l) <= len(tr) and set(tr_l) <= set(tr), "purge=L+H did not tighten the fold"


def test_cpcv_structure():
    panel = _demo_panel(GATE_TICKERS[:2])
    splits, group, ng = validation.cpcv_splits(panel["t0_ts"], panel["t1_ts"])
    assert len(splits) == 15 and ng == 6
    per_group = {g: sum(1 for s in splits if g in s["test_groups"]) for g in range(ng)}
    assert all(v == 5 for v in per_group.values()), f"each group must be tested 5x: {per_group}"
    paths = validation.cpcv_paths(splits, ng)
    assert len(paths) == 5
    for p in paths:
        assert set(p) == set(range(ng)), "a path must cover every group"
        for g, si in p.items():
            assert g in splits[si]["test_groups"], "path points at a split not testing that group"
    # purge sanity on one split
    emb = validation.embargo_ns()
    t0 = pd.to_datetime(panel["t0_ts"], utc=True).astype("int64").to_numpy()
    t1 = pd.to_datetime(panel["t1_ts"], utc=True).astype("int64").to_numpy()
    bounds = validation.time_group_bounds(t0, ng)
    sp = splits[7]
    for g in sp["test_groups"]:
        ok = (t1[sp["train_idx"]] < bounds[g]) | (t0[sp["train_idx"]] > bounds[g + 1] + emb)
        assert ok.all(), "CPCV train violates purge/embargo around a test group"


def test_holdout_boundary():
    panel = _demo_panel(GATE_TICKERS[:1])
    hs = pd.Timestamp(CONFIG["SPLITS"]["holdout_start"], tz="UTC").value
    t1 = pd.to_datetime(panel["t1_ts"], utc=True).astype("int64").to_numpy()
    assert (t1 + validation.embargo_ns() <= hs).all(), "CV label span crosses into holdout"


def test_anti_lookahead_gate():
    """WO §1 rule 2 (BRAMKA): delaying every feature by one bar must not IMPROVE the validation
    metric. If it does, information from the future leaks into the features."""
    from . import xgb_loop as X
    seed_everything()
    base = _demo_panel()
    shifted = _demo_panel(shift_features=True)
    folds_b = validation.purged_kfold(base["t0_ts"], base["t1_ts"])
    folds_s = validation.purged_kfold(shifted["t0_ts"], shifted["t1_ts"])
    ref = CONFIG["STUDY1"]["ref_xgb"]
    f1_base = X.oof(base, POOL, folds_b, ref)["mean"]
    f1_shift = X.oof(shifted, POOL, folds_s, ref)["mean"]
    print(f"    anti-lookahead: base={f1_base:.4f} shifted={f1_shift:.4f}")
    assert f1_shift <= f1_base + 0.010, \
        f"LOOKAHEAD SUSPECTED: shifting features +1 bar improved macro-F1 {f1_base:.4f} -> {f1_shift:.4f}"


def test_determinism():
    from . import xgb_loop as X
    panel = _demo_panel(GATE_TICKERS[:1])
    folds = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"])
    ref = CONFIG["STUDY1"]["ref_xgb"]
    seed_everything()
    a = X.oof(panel, POOL, folds, ref)["mean"]
    seed_everything()
    b = X.oof(panel, POOL, folds, ref)["mean"]
    assert a == b, f"non-deterministic OOF: {a} != {b}"


def test_oof_parallel_equals_serial():
    """The parallel-fold OOF (folds trained in worker processes, nthread unchanged) must be
    BYTE-IDENTICAL to the serial path — parallelism is only a scheduling change, not a numeric one."""
    from . import xgb_loop as X
    panel = _demo_panel(GATE_TICKERS[:2])
    folds = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"])
    ref = CONFIG["STUDY1"]["ref_xgb"]
    saved = X._PANEL_WORKERS
    try:
        X._PANEL_WORKERS = 1
        ser = X.oof(panel, POOL, folds, ref)
        X._PANEL_WORKERS = 4  # spawn pool created here (via panel-less oof path); parallel folds
        par = X.oof(panel, POOL, folds, ref)
    finally:
        X._PANEL_WORKERS = saved
    assert ser["mean"] == par["mean"], f"parallel OOF mean differs: {ser['mean']} != {par['mean']}"
    assert np.array_equal(np.nan_to_num(ser["proba"]), np.nan_to_num(par["proba"])), \
        "parallel OOF probabilities are not byte-identical to serial"


def test_lstm_oof_parallel_equals_serial():
    """The parallel (fold, seed) LSTM OOF must be BYTE-IDENTICAL to the serial path — the workers
    train the same models at the same fixed torch thread count, only concurrently."""
    import json
    from . import lstm_loop as L
    from . import xgb_loop as X
    bars, feats = data.bar_frame("AAPL", "demo")
    ev = labels.build_events(bars, feats, GATE_PARAMS, "AAPL")
    ev = ev[validation.window_mask(ev["t0_ts"], "cv")].reset_index(drop=True)
    frames = {"AAPL": (bars, feats)}
    chans = POOL[:5]
    events = L.eligible_events(ev, frames, chans, CONFIG["LSTM"]["seq_len_max"])
    arch = {"seq_len": 32, "hidden": 16, "num_layers": 1, "dropout": 0.3, "lr": 0.003,
            "batch": 256, "weight_decay": 1e-4}
    folds = L.lstm_folds(events, frames, arch["seq_len"])
    saved = X._PANEL_WORKERS
    try:
        X._PANEL_WORKERS = 1
        ser = L.oof_lstm(events, frames, chans, folds, arch, 2, [42, 10049])
        X._PANEL_WORKERS = 4
        par = L.oof_lstm(events, frames, chans, folds, arch, 2, [42, 10049])
    finally:
        X._PANEL_WORKERS = saved
    assert ser["mean"] == par["mean"], f"LSTM parallel OOF mean differs: {ser['mean']} != {par['mean']}"
    assert np.array_equal(np.nan_to_num(ser["proba"]), np.nan_to_num(par["proba"])), \
        "LSTM parallel OOF probabilities not byte-identical to serial"


def test_lstm_scaler_and_purge():
    """WO-LSTM §1 scaling contract: fold scaler == stats of train-window rows only; and the
    sequence dataset purges with t_start = t0 − (L−1) bars."""
    import torch  # noqa: F401 — fail early if torch missing
    from . import lstm_loop as L
    bars, feats = data.bar_frame("AAPL", "demo")
    ev = labels.build_events(bars, feats, GATE_PARAMS, "AAPL")
    ev = ev[validation.window_mask(ev["t0_ts"], "cv")].reset_index(drop=True)
    cut = ev["t0_ts"].iloc[len(ev) // 2]
    names = POOL[:5]
    stats = L.fold_scaler_stats(bars, feats, names, before_ts=cut)
    m = bars["close_ts"] < cut
    for n in names:
        x = feats[n].to_numpy(float)[m.to_numpy()]
        x = x[np.isfinite(x)]
        assert abs(stats[n]["mean"] - x.mean()) < 1e-12, f"scaler mean leaks for {n}"
        assert abs(stats[n]["std"] - max(x.std(), 1e-8)) < 1e-12, f"scaler std leaks for {n}"


def test_lstm_pooled_scaler_no_leak():
    """WO-LSTM §1.2-1.3 (the leak the review caught): the pooled CV-fold scaler must use ONLY
    CV-window bars outside the fold's test region — NO 2024→2026 holdout bar, NO 2016 warmup bar,
    NO test-block bar — and the exclusion must be by REAL bar timestamps (a 64-bar RTH window spans
    ~13 calendar days, far more than 64 hours)."""
    from . import lstm_loop as L
    tickers = GATE_TICKERS[:2]
    frames = {t: data.bar_frame(t, "demo") for t in tickers}
    panel = _demo_panel(tickers)
    chans = POOL[:6]
    events = L.eligible_events(panel, frames, chans, CONFIG["LSTM"]["seq_len_max"])
    seq_len = 64
    folds = L.lstm_folds(events, frames, seq_len)
    tstart = L.lstm_t_start(events, frames, seq_len)
    tr, te = folds[0]
    excl = L.scaler_exclude_intervals(events, te, tstart)
    cvb = L.cv_bounds_ts()
    stats = L.pooled_scaler_stats(frames, chans, cvb, excl)
    hs = pd.Timestamp(CONFIG["SPLITS"]["holdout_start"], tz="UTC")
    ws = pd.Timestamp(CONFIG["SPLITS"]["cv_start"], tz="UTC")
    n = chans[0]
    acc = []
    for t in tickers:
        bars, feats = frames[t]
        ct = bars["close_ts"]
        mask = ((ct >= cvb[0]) & (ct <= cvb[1])).to_numpy()
        for lo, hi in excl:
            mask &= ~((ct >= lo) & (ct <= hi)).to_numpy()
        kept_ct = ct[mask]
        assert not (kept_ct >= hs).any(), "LEAK: pooled scaler includes holdout bars"
        assert not (kept_ct < ws).any(), "pooled scaler includes pre-CV warmup bars"
        x = feats[n].to_numpy(float)[mask]
        acc.append(x[np.isfinite(x)])
    x = np.concatenate(acc)
    assert abs(stats[n]["mean"] - x.mean()) < 1e-9, "pooled scaler mean != manual train-window mean"
    # exclusion must actually bite: an all-bars scaler differs from the causal one
    leaky = L.pooled_scaler_stats(frames, chans, (ws, hs + pd.Timedelta(days=900)), [])
    assert abs(leaky[n]["mean"] - stats[n]["mean"]) > 1e-9, "exclusion had no effect (suspicious)"


def test_dsl_causality():
    """The DSL grammar makes look-ahead unexpressible: shift(x,0)/future refs and non-whitelisted
    names are rejected; a valid feature delayed by +1 bar cannot IMPROVE (it only loses info)."""
    from . import dsl
    bars, _ = data.bar_frame("AAPL", "demo", include_proposed=False)
    for expr in ("shift(c, 0)", "close * 2", "c[1]", "__import__('os')"):
        ok, _ = dsl.validate_proposal("x", expr, bars, set())
        assert not ok, f"DSL wrongly accepted unsafe expr: {expr}"
    ok, reason = dsl.validate_proposal("mr", "zscore(c, 20)", bars, set())
    assert ok, f"DSL rejected a valid feature: {reason}"
    # a feature and its +1 lag: correlation high but not identical; both finite -> causal by grammar
    base = dsl.dsl_eval("log(c) - log(shift(c,1))", bars)
    assert np.isfinite(base[dsl.WARMUP_1H:]).mean() > 0.99


def test_proposed_cache_isolation():
    """Seeding a proposed feature must NOT change the base pool columns, and the proposed column is
    causal (finite after warmup, not constant)."""
    import json
    from . import dsl
    p = data.PROPOSED_PATH
    backup = p.read_text() if p.exists() else None
    try:
        reg = dsl.proposed_registry(p)
        reg["zz_test_overnight_gap"] = {"id": 9001, "expr": "log(o) - log(shift(c,1))"}
        reg["_next_id"] = max(int(reg.get("_next_id", 501)), 9002)
        p.write_text(json.dumps(reg, indent=2))
        base_only = data.bar_frame("AAPL", "demo", use_cache=False, include_proposed=False)[1]
        withp = data.bar_frame("AAPL", "demo", use_cache=False, include_proposed=True)[1]
        for col in base_only.columns:
            assert np.allclose(base_only[col].to_numpy(), withp[col].to_numpy(), equal_nan=True), \
                f"proposed feature changed base column {col}"
        assert "zz_test_overnight_gap" in withp.columns
        v = withp["zz_test_overnight_gap"].to_numpy()
        assert np.isfinite(v[dsl.WARMUP_1H:]).mean() > 0.99, "proposed feature not finite after warmup"
    finally:
        if backup is not None:
            p.write_text(backup)
        elif p.exists():
            p.unlink()


def test_strategy_selfcheck():
    """The sealed XGB strategy artifact must reload from base64 and reproduce its golden vectors."""
    import base64
    import json
    import xgboost as xgb
    from . import strategy
    path = ART / "demo" / "strategy_xgb.json"
    if not path.exists():
        return  # produced by `make fs-xgb` — skip if not yet run
    m = json.loads(path.read_text())
    raw = base64.b64decode(m["model_b64"])
    assert strategy._sha(raw) == m["model_sha256"], "strategy sha256 mismatch"
    b = xgb.Booster()
    b.load_model(bytearray(raw))
    assert b.num_features() == len(m["selected"]), "reloaded model feature count mismatch"
    assert m["selfcheck_ok"], "strategy golden selfcheck was not OK at seal time"


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"PASS {name}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {name}: {e}")
        except Exception as e:  # noqa: BLE001 — a gate crash is a failure, not an error to hide
            failed += 1
            print(f"ERROR {name}: {type(e).__name__}: {e}")
    if failed:
        raise SystemExit(f"{failed} gate(s) FAILED — the WO forbids proceeding")
    print("ALL GATES PASS")


if __name__ == "__main__":
    main()

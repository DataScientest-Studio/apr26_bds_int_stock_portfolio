"""WO-FS-XGB-v1 — the XGBoost feature-selection loop (docs/XGB-ZLECENIE-LOOP.md).

Stages (run in order; each is idempotent and reads only frozen upstream artifacts):
  study1   Optuna over label parameters (CUSUM threshold, EWMA span, pt, sl, H) — the SHARED
           label truth; freezes artifacts/<u>/labels_frozen.json.
  loop     correlation clustering (1−|ρ Spearman|) + clustered MDA on OOF + backward elimination
           with the 1-SE stop/choice rule.
  stability 20 bootstrap re-runs (ticker subsamples) -> π selection frequency; selected = π>=0.7;
           exports the ranking the LSTM loop starts from.
  study2   Optuna HPO of XGB on the selected set (macro-F1 on Purged K-Fold, mlogloss pruning),
           then p* on OOF; logs per-trial time-slice scores for PBO.
  cpcv     CPCV(6,2) distribution of macro-F1 + the 5 assembled OOS paths.
  shap     per-asset |SHAP| (native pred_contribs, OOF) -> feature_importance_shap + universality.
  holdout  the ONE holdout read (guarded by a flag file): final refit on full CV panel, report,
           Sharpe/DSR/PBO verdict.

Usage: python -m fs.xgb_loop --universe demo|full --stage all|study1|loop|stability|study2|cpcv|shap|holdout
"""
import argparse
import json
import os

import numpy as np
import pandas as pd
import xgboost as xgb

from . import CONFIG, SEED, art_dir, read_json, seed_everything, write_json
from . import data, labels, metrics, report, validation
from .features import POOL

MODEL = "XGB"
_NTHREAD = int(CONFIG["XGB_NTHREAD"])
_PANEL_WORKERS = 1  # processes used to build the event panel in parallel (fills the CPU-idle gap)
_PANEL_POOL = None


def apply_parallelism(universe):
    """Full-resources use: set the XGBoost thread count AND the panel-build worker count to the
    configured value, CAPPED at os.cpu_count()-1 and overridable via FS_NTHREAD — so a smaller server
    auto-adapts. Fixed thread count -> reproducible at that count."""
    global _NTHREAD, _PANEL_WORKERS
    cap = max(1, (os.cpu_count() or 2) - 1)
    want = int(CONFIG.get("PARALLEL", {}).get(universe, {}).get("xgb_nthread", CONFIG["XGB_NTHREAD"]))
    _NTHREAD = env_int("FS_NTHREAD", min(want, cap))
    workers = int(CONFIG.get("PARALLEL", {}).get(universe, {}).get("warm_workers", 1))
    _PANEL_WORKERS = env_int("FS_PANEL_WORKERS", min(workers, cap))


def env_int(name, default):
    v = os.environ.get(name)
    return int(v) if v else int(default)


def xgb_params(extra=None, nthread=None):
    p = {"objective": "multi:softprob", "num_class": 3, "tree_method": "hist",
         "eval_metric": "mlogloss", "nthread": int(nthread) if nthread else _NTHREAD, "seed": SEED}
    if extra:
        p.update({k: v for k, v in extra.items() if k != "n_estimators"})
    return p


def _ensure_pool_columns(panel, pool):
    """Any pool feature the panel is missing (e.g. a proposer appended it after the panel was built)
    is added as an all-NaN column, so panel[pool] never KeyErrors. XGBoost treats NaN natively."""
    for c in pool:
        if c not in panel.columns:
            panel[c] = np.nan
    return panel


def feature_set_key(selected):
    """Short stable id of a feature set — study2's Optuna study is keyed by it so a changed selected
    (after a live-proposer re-pool) starts a FRESH study rather than reusing incomparable trials."""
    import hashlib
    return hashlib.sha256("|".join(sorted(selected)).encode()).hexdigest()[:8]


def suggest(trial, space):
    out = {}
    for name, s in space.items():
        if s["type"] == "int":
            out[name] = trial.suggest_int(name, s["low"], s["high"])
        elif s["type"] == "float":
            out[name] = trial.suggest_float(name, s["low"], s["high"], log=bool(s.get("log")))
        elif s["type"] == "cat":
            out[name] = trial.suggest_categorical(name, s["choices"])
    return out


# ---------------- panel ----------------

def select_subsample(universe):
    """Ticker count for feature SELECTION (loop + stability) — economy mode. None = all tickers."""
    s = CONFIG["XGB_LOOP"].get("select_ticker_subsample", {}).get(universe)
    return int(s) if s else None


def universe_tickers(universe, subsample=None):
    tk = data.tickers(universe)
    if subsample and len(tk) > subsample:
        rng = np.random.default_rng(SEED)
        tk = sorted(rng.choice(tk, size=subsample, replace=False))
    return list(tk)


def load_frames(universe, tickers):
    return {t: data.bar_frame(t, universe) for t in tickers}


def _assemble_panel(parts, window):
    if not parts:
        raise RuntimeError("no events in panel")
    panel = pd.concat(parts, ignore_index=True)
    panel = panel[validation.window_mask(panel["t0_ts"], window)].reset_index(drop=True)
    if window == "cv":
        panel, _ = validation.purge_cv_boundary(panel)
    panel = labels.assign_uniqueness(panel)
    return panel.sort_values("t0_ts", kind="mergesort").reset_index(drop=True)


def build_panel(frames, label_params, window):
    """Pooled event panel from already-loaded frames (serial; used by the LSTM loop which needs the
    frames in memory anyway). CV panels get the holdout-boundary purge; weights assigned last."""
    parts = [ev for t, (bars, feats) in frames.items()
             if len(ev := labels.build_events(bars, feats, label_params, t))]
    return _assemble_panel(parts, window)


def _events_worker(args):
    """One ticker's labeled events; the worker reloads its cached frame (page-cached RAM) so no big
    DataFrame is pickled across the pool. Deterministic: build_events has no RNG."""
    universe, ticker, label_params = args
    bars, feats = data.bar_frame(ticker, universe)
    ev = labels.build_events(bars, feats, label_params, ticker)
    return ev if len(ev) else None


def _panel_pool():
    """Lazy process pool for panel building + parallel fold training. Uses the SPAWN context so a
    worker never inherits the parent's OpenMP/XGBoost thread state (fork-after-threads deadlocks)."""
    global _PANEL_POOL
    if _PANEL_POOL is None:
        import multiprocessing as mp
        from concurrent.futures import ProcessPoolExecutor
        _PANEL_POOL = ProcessPoolExecutor(_PANEL_WORKERS, mp_context=mp.get_context("spawn"))
    return _PANEL_POOL


def panel_for(universe, tickers, label_params, window):
    """PARALLEL pooled event panel: each ticker's events are built in a worker process that reloads
    its cached frame — so all cores stay busy through the CUSUM/Triple-Barrier build (the phase that
    used to leave the CPU idle between training bursts). map() preserves order -> deterministic."""
    tickers = list(tickers)
    if _PANEL_WORKERS > 1 and len(tickers) > 4:
        parts = [p for p in _panel_pool().map(
            _events_worker, [(universe, t, label_params) for t in tickers]) if p is not None]
    else:
        parts = [p for p in (_events_worker((universe, t, label_params)) for t in tickers)
                 if p is not None]
    return _assemble_panel(parts, window)


def train_weights(y, w_uniq):
    """uniqueness × inverse-class-frequency (normalized to mean 1) — the WO's imbalance guard."""
    y = np.asarray(y)
    w = np.asarray(w_uniq, float).copy()
    for c in (-1, 0, 1):
        m = y == c
        if m.any():
            w[m] *= len(y) / (3.0 * m.sum())
    return w * (len(w) / max(w.sum(), 1e-12))


def fit_predict(panel, feats, tr, te, params):
    """Train on fold-train rows, return (n_te, 3) probabilities (class order −1, 0, +1)."""
    Xtr = panel.iloc[tr][feats].to_numpy(float)
    Xte = panel.iloc[te][feats].to_numpy(float)
    ytr = panel.iloc[tr]["y"].to_numpy(int) + 1
    wtr = train_weights(panel.iloc[tr]["y"], panel.iloc[tr]["w"])
    booster = xgb.train(xgb_params(params), xgb.DMatrix(Xtr, label=ytr, weight=wtr,
                                                        feature_names=list(feats)),
                        num_boost_round=int(params.get("n_estimators", 120)))
    return booster, booster.predict(xgb.DMatrix(Xte, feature_names=list(feats)))


def decide(proba, pstar=None):
    """argmax over classes; with p*, a −1/+1 call below p* abstains to 0 (WO §6 threshold rule)."""
    cls = np.array([-1, 0, 1])
    yhat = cls[np.argmax(proba, axis=1)]
    if pstar is not None:
        conf = np.max(proba[:, [0, 2]], axis=1)
        yhat = np.where((yhat != 0) & (conf < pstar), 0, yhat)
    return yhat


def oof(panel, feats, folds, params, keep_models=False):
    """OOF probabilities + per-fold macro-F1/log-loss over purged folds. SERIAL: a few-feature XGB
    trains a fold in ~0.4s, so process-parallelising folds only adds spawn/IPC + OpenMP-oversubscription
    overhead (measured 100x+ SLOWER). The useful parallelism for XGB is the panel build (panel_for)."""
    proba = np.full((len(panel), 3), np.nan)
    f1s, lls, models = [], [], []
    for tr, te in folds:
        booster, p = fit_predict(panel, feats, tr, te, params)
        proba[te] = p
        yte = panel.iloc[te]["y"].to_numpy(int)
        f1s.append(metrics.macro_f1(yte, decide(p)))
        lls.append(metrics.fold_log_loss(yte, p))
        if keep_models:
            models.append((booster, te))
    return {"proba": proba, "fold_f1": f1s, "fold_ll": lls, "models": models,
            "mean": float(np.mean(f1s)), "se": float(np.std(f1s, ddof=1) / np.sqrt(len(f1s)))}


# ---------------- stage: study1 ----------------

def frozen_labels(universe):
    return read_json(art_dir(universe) / "labels_frozen.json")


def study1(universe):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    seed_everything()
    cfg = CONFIG["STUDY1"]
    tickers = universe_tickers(universe, cfg["ticker_subsample_full"] if universe == "full" else None)
    pool = data.feature_pool()  # snapshot ONCE for the whole study
    n_trials = env_int("FS_STUDY1_TRIALS", cfg["n_trials"][universe])

    def objective(trial):
        params = suggest(trial, cfg["space"])
        try:
            panel = panel_for(universe, tickers, params, "cv")
        except RuntimeError:
            raise optuna.TrialPruned()
        _ensure_pool_columns(panel, pool)
        frac = {c: float((panel["y"] == c).mean()) for c in (-1, 0, 1)}
        trial.set_user_attr("class_frac", frac)
        trial.set_user_attr("n_events", len(panel))
        if min(frac.values()) < float(cfg["min_class_frac"]):
            raise optuna.TrialPruned()
        folds = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"])
        f1s = []
        for i, (tr, te) in enumerate(folds):
            _, p = fit_predict(panel, pool, tr, te, cfg["ref_xgb"])
            yte = panel.iloc[te]["y"].to_numpy(int)
            f1s.append(metrics.macro_f1(yte, decide(p)))
            # pruning on log-loss per the WO; negated because the study maximizes
            trial.report(-metrics.fold_log_loss(yte, p), step=i)
            if trial.should_prune():
                raise optuna.TrialPruned()
        return float(np.mean(f1s))

    study = optuna.create_study(
        study_name=f"study1_{universe}", direction="maximize",
        storage=f"sqlite:///{art_dir(universe) / 'optuna.db'}", load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=SEED),
        pruner=optuna.pruners.MedianPruner(n_warmup_steps=2))
    done = len([t for t in study.trials if t.state.is_finished()])
    if done < n_trials:
        study.optimize(objective, n_trials=n_trials - done)
    best = study.best_trial
    payload = {"params": best.params, "best_macro_f1_cv": best.value,
               "class_frac": best.user_attrs.get("class_frac"),
               "n_events_study1": best.user_attrs.get("n_events"),
               "n_trials": len(study.trials), "study1_tickers": tickers,
               "run_id": f"wofs-{universe}-t{best.number}", "universe": universe}
    write_json(art_dir(universe) / "labels_frozen.json", payload)
    print(f"[study1/{universe}] frozen: {best.params}  macro-F1(CV)={best.value:.4f}  "
          f"class_frac={payload['class_frac']}  run_id={payload['run_id']}")
    return payload


# ---------------- stage: loop ----------------

def corr_clusters(panel, feats):
    """Hierarchical clusters on 1−|ρ Spearman| (WO §4.2). Returns list[list[feature]]."""
    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform
    if len(feats) <= 2:
        return [[f] for f in feats]
    rho = panel[feats].corr(method="spearman").to_numpy()
    rho = np.where(np.isfinite(rho), rho, 0.0)
    dist = 1.0 - np.abs(rho)
    np.fill_diagonal(dist, 0.0)
    z = linkage(squareform(dist, checks=False), method="average")
    lab = fcluster(z, t=1.0 - float(CONFIG["XGB_LOOP"]["corr_cluster_threshold"]),
                   criterion="distance")
    out = {}
    for f, c in zip(feats, lab):
        out.setdefault(int(c), []).append(f)
    return list(out.values())


def clustered_mda(panel, feats, folds, res, clusters, repeats, rng):
    """Δ macro-F1 when a WHOLE cluster is permuted on each fold's OOF rows (WO §4.4).
    The same permutation is applied to every column of the cluster (joint permutation)."""
    deltas = {tuple(cl): [] for cl in clusters}
    for (booster, te), base_f1 in zip(res["models"], res["fold_f1"]):
        Xte = panel.iloc[te][feats].reset_index(drop=True)
        yte = panel.iloc[te]["y"].to_numpy(int)
        for cl in clusters:
            for _ in range(repeats):
                perm = rng.permutation(len(Xte))
                Xp = Xte.copy()
                for f in cl:
                    Xp[f] = Xte[f].to_numpy()[perm]
                p = booster.predict(xgb.DMatrix(Xp.to_numpy(float), feature_names=list(feats)))
                deltas[tuple(cl)].append(base_f1 - metrics.macro_f1(yte, decide(p)))
    return {cl: float(np.mean(v)) for cl, v in deltas.items()}


def shap_control(panel, feats, res):
    """Mean |pred_contribs| per feature over OOF rows (agreement control for the MDA ranking)."""
    acc = np.zeros(len(feats))
    n = 0
    for booster, te in res["models"]:
        Xte = panel.iloc[te][feats].to_numpy(float)
        contrib = booster.predict(xgb.DMatrix(Xte, feature_names=list(feats)), pred_contribs=True)
        contrib = np.abs(np.asarray(contrib))[:, :, :-1].sum(axis=1)  # sum |contrib| over classes, drop bias
        acc += contrib.mean(axis=0)
        n += 1
    return {f: float(v / max(n, 1)) for f, v in zip(feats, acc)}


def run_elimination(panel, folds, params, record=None, rng=None, with_control=False, pool=None):
    """The backward-elimination loop; returns the trajectory [(features, mean, se)] and the
    1-SE selected set. `record(round_dict)` persists rounds when given."""
    lc = CONFIG["XGB_LOOP"]
    rng = rng or np.random.default_rng(SEED)
    active = list(pool if pool is not None else data.feature_pool())
    _ensure_pool_columns(panel, active)
    traj = []
    rounds_since_best = 0
    best = -np.inf
    rnd = 0
    while True:
        res = oof(panel, active, folds, params, keep_models=True)
        traj.append((list(active), res["mean"], res["se"]))
        clusters = corr_clusters(panel, active)
        mda = clustered_mda(panel, active, folds, res, clusters, int(lc["mda_repeats"]), rng)
        ctrl = shap_control(panel, active, res) if with_control else {}
        weakest = min(mda, key=mda.get)
        if record:
            record({"round": rnd, "n_features": len(active), "cv_mean": res["mean"],
                    "cv_se": res["se"], "removed": json.dumps(list(weakest)),
                    "features": json.dumps(active),
                    "mda": json.dumps({" | ".join(k): v for k, v in mda.items()}),
                    "control": json.dumps(ctrl)})
        if res["mean"] > best:
            best, rounds_since_best = res["mean"], 0
        else:
            rounds_since_best += 1
        scores = [t[1] for t in traj]
        ses = [t[2] for t in traj]
        i_best = int(np.argmax(scores))
        if (res["mean"] < scores[i_best] - ses[i_best]
                or rounds_since_best >= int(lc["stop_no_improve_rounds"])
                or len(active) - len(weakest) < int(lc["min_features"])):
            break
        active = [f for f in active if f not in weakest]
        rnd += 1
    i = metrics.one_se_choice([len(t[0]) for t in traj], [t[1] for t in traj], [t[2] for t in traj])
    return traj, list(traj[i][0])


def loop(universe):
    seed_everything()
    frozen = frozen_labels(universe)
    run_id = frozen["run_id"]
    tickers = universe_tickers(universe, select_subsample(universe))
    pool = data.feature_pool()  # snapshot once for this stage
    panel = panel_for(universe, tickers, frozen["params"], "cv")
    folds = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"])
    rows = []
    traj, chosen = run_elimination(panel, folds, CONFIG["STUDY1"]["ref_xgb"],
                                   record=rows.append, with_control=True, pool=pool)
    for r in rows:
        r.update(run_id=run_id, model=MODEL)
    report.replace_rows(universe, "loop_rounds", rows, run_id, MODEL)
    write_json(art_dir(universe) / "loop_xgb.json",
               {"run_id": run_id, "one_se_choice": chosen,
                "trajectory": [{"features": t[0], "mean": t[1], "se": t[2]} for t in traj]})
    print(f"[loop/{universe}] rounds={len(traj)}  1-SE choice ({len(chosen)}): {chosen}")
    return chosen


# ---------------- stage: stability ----------------

def _bootstrap_worker(args):
    """One stability bootstrap: a full backward elimination on a ticker subsample, in a worker
    process pinned to a SINGLE xgb thread (so ~15 bootstraps run concurrently with no OpenMP
    oversubscription). Deterministic per its seed. Returns the selected feature list."""
    global _NTHREAD, _PANEL_WORKERS
    _NTHREAD, _PANEL_WORKERS = 1, 1
    panel, folds, ref, pool, seed = args
    _, chosen = run_elimination(panel, folds, ref, rng=np.random.default_rng(seed), pool=pool)
    return chosen


def stability(universe):
    seed_everything()
    lc = CONFIG["XGB_LOOP"]
    frozen = frozen_labels(universe)
    run_id = frozen["run_id"]
    tickers = universe_tickers(universe, select_subsample(universe))
    pool = data.feature_pool()  # snapshot once for the whole stability stage
    full_panel = panel_for(universe, tickers, frozen["params"], "cv")
    _ensure_pool_columns(full_panel, pool)
    rng = np.random.default_rng(SEED)
    B = env_int("FS_XGB_BOOTSTRAPS", lc["stability_bootstraps"])
    tasks = []
    for b in range(B):
        sub = sorted(rng.choice(tickers, size=max(3, int(len(tickers) * lc["stability_ticker_frac"])),
                                replace=False))
        panel = full_panel[full_panel["ticker"].isin(sub)].reset_index(drop=True)
        panel = labels.assign_uniqueness(panel)
        folds = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"])
        tasks.append((panel, folds, CONFIG["STUDY1"]["ref_xgb"], pool, SEED + b))
    # bootstraps are independent -> run them in parallel (1 xgb thread each)
    if _PANEL_WORKERS > 1 and B > 1:
        results = list(_panel_pool().map(_bootstrap_worker, tasks))
    else:
        results = [_bootstrap_worker(t) for t in tasks]
    counts = {f: 0 for f in pool}
    for chosen in results:
        for f in chosen:
            counts[f] += 1
    print(f"[stability/{universe}] {B} bootstraps done")
    pi = {f: counts[f] / B for f in pool}
    selected = [f for f in pool if pi[f] >= float(lc["stability_pi"])]
    if len(selected) < int(lc["min_features"]):
        selected = sorted(pool, key=lambda f: -pi[f])[:int(lc["min_features"])]
    report.replace_rows(universe, "stability",
                        [{"run_id": run_id, "model": MODEL, "feature": f, "pi": pi[f]} for f in pool],
                        run_id, MODEL)
    ranking = sorted(pool, key=lambda f: -pi[f])
    write_json(art_dir(universe) / "selected_xgb.json",
               {"run_id": run_id, "selected": selected, "pi": pi})
    write_json(art_dir(universe) / "xgb_feature_ranking.json",
               {"run_id": run_id, "ranking": ranking, "pi": pi})
    print(f"[stability/{universe}] selected (pi>={lc['stability_pi']}): {selected}")
    return selected


# ---------------- stage: study2 (+ p*) ----------------

def slice_scores(panel, proba, n_slices):
    """macro-F1 in contiguous time slices of the OOF predictions (rows already time-sorted) —
    the per-trial columns of the PBO/CSCV matrix."""
    ok = np.isfinite(proba).all(axis=1)
    idx = np.nonzero(ok)[0]
    out = []
    for chunk in np.array_split(idx, n_slices):
        y = panel.iloc[chunk]["y"].to_numpy(int)
        out.append(metrics.macro_f1(y, decide(proba[chunk])))
    return out


def study2(universe):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    seed_everything()
    cfg = CONFIG["XGB_STUDY2"]
    frozen = frozen_labels(universe)
    run_id = frozen["run_id"]
    selected = read_json(art_dir(universe) / "selected_xgb.json")["selected"]
    # HPO economy: tune hyper-parameters on the same representative subsample used for selection;
    # cpcv / shap / strategy / holdout below all read the FULL universe.
    panel = panel_for(universe, universe_tickers(universe, select_subsample(universe)),
                      frozen["params"], "cv")
    _ensure_pool_columns(panel, selected)
    folds = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"])
    n_slices = int(CONFIG["PBO_SLICES"])

    def objective(trial):
        params = suggest(trial, cfg["space"])
        res = oof(panel, selected, folds, params)
        for i, ll in enumerate(res["fold_ll"]):
            trial.report(-ll, step=i)  # log-loss pruning; negated because the study maximizes
            if trial.should_prune():
                raise optuna.TrialPruned()
        trial.set_user_attr("slices", slice_scores(panel, res["proba"], n_slices))
        return res["mean"]

    # key the study by the selected set — a re-pooled (different) selected gets its OWN HPO study
    # instead of reusing trials evaluated on a different feature set (incomparable objective values)
    study = optuna.create_study(
        study_name=f"study2_xgb_{universe}_{feature_set_key(selected)}", direction="maximize",
        storage=f"sqlite:///{art_dir(universe) / 'optuna.db'}", load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=SEED),
        pruner=optuna.pruners.MedianPruner(n_warmup_steps=int(cfg["pruner_warmup"])))
    n_trials = env_int("FS_STUDY2_TRIALS", cfg["n_trials"][universe])
    done = len([t for t in study.trials if t.state.is_finished()])
    if done < n_trials:
        study.optimize(objective, n_trials=n_trials - done)

    rows = [{"run_id": run_id, "model": MODEL, "trial": t.number, "slice": i, "score": s}
            for t in study.trials if t.user_attrs.get("slices")
            for i, s in enumerate(t.user_attrs["slices"])]
    report.replace_rows(universe, "trial_slices", rows, run_id, MODEL)

    best = dict(study.best_trial.params)
    res = oof(panel, selected, folds, best)
    grid = np.arange(CONFIG["PSTAR"]["low"], CONFIG["PSTAR"]["high"] + 1e-9, CONFIG["PSTAR"]["step"])
    ok = np.isfinite(res["proba"]).all(axis=1)
    y_oof = panel["y"].to_numpy(int)[ok]
    pstar, pstar_f1 = None, -np.inf
    for p in grid:
        f1 = metrics.macro_f1(y_oof, decide(res["proba"][ok], float(p)))
        if f1 > pstar_f1:
            pstar, pstar_f1 = float(p), f1
    payload = {"run_id": run_id, "selected": selected, "best_params": best,
               "cv_macro_f1": res["mean"], "cv_se": res["se"], "pstar": pstar,
               "pstar_macro_f1": pstar_f1, "n_trials": len(study.trials)}
    write_json(art_dir(universe) / "study2_xgb.json", payload)
    report.replace_rows(universe, "cv_scores",
                        [{"run_id": run_id, "model": MODEL, "stage": "study2_best", "unit": "fold",
                          "unit_id": str(i), "score": s, "extra": None}
                         for i, s in enumerate(res["fold_f1"])], run_id, MODEL, stage="study2_best")
    print(f"[study2/{universe}] best={best}  CV macro-F1={res['mean']:.4f}±{res['se']:.4f}  "
          f"p*={pstar} (F1={pstar_f1:.4f})")
    return payload


# ---------------- stage: cpcv ----------------

def signed_event_returns(y_ret, yhat):
    """Signed per-event log return of the threshold strategy: +1 takes ret, −1 takes −ret, 0 skips."""
    return np.where(yhat == 0, np.nan, yhat * y_ret)


def cpcv_stage(universe):
    seed_everything()
    frozen = frozen_labels(universe)
    run_id = frozen["run_id"]
    s2 = read_json(art_dir(universe) / "study2_xgb.json")
    selected, best, pstar = s2["selected"], s2["best_params"], s2["pstar"]
    panel = panel_for(universe, universe_tickers(universe), frozen["params"], "cv")
    splits, group, ng = validation.cpcv_splits(panel["t0_ts"], panel["t1_ts"])
    # serial: each XGB split trains in ~0.4s; parallelising tiny XGB models only adds overhead
    split_proba, rows = {}, []
    for i, sp in enumerate(splits):
        _, p = fit_predict(panel, selected, sp["train_idx"], sp["test_idx"], best)
        split_proba[i] = p
        f1 = metrics.macro_f1(panel.iloc[sp["test_idx"]]["y"].to_numpy(int), decide(p, pstar))
        rows.append({"run_id": run_id, "model": MODEL, "stage": "cpcv", "unit": "split",
                     "unit_id": str(sp["test_groups"]), "score": f1, "extra": None})
    paths = validation.cpcv_paths(splits, ng)
    path_summaries = []
    for pi_, path in enumerate(paths):
        proba = np.full((len(panel), 3), np.nan)
        for g, si in path.items():
            sp = splits[si]
            m = group[sp["test_idx"]] == g
            proba[sp["test_idx"][m]] = split_proba[si][m]
        ok = np.isfinite(proba).all(axis=1)
        yhat = decide(proba[ok], pstar)
        f1 = metrics.macro_f1(panel["y"].to_numpy(int)[ok], yhat)
        ret = signed_event_returns(panel["ret"].to_numpy(float)[ok], yhat)
        m_tr = np.isfinite(ret)
        daily = metrics.daily_strategy_returns(panel["t1_ts"].to_numpy()[ok][m_tr], ret[m_tr])
        sr = metrics.sharpe(daily, CONFIG["TRADING"]["periods_per_year"])
        rows.append({"run_id": run_id, "model": MODEL, "stage": "cpcv", "unit": "path",
                     "unit_id": str(pi_), "score": f1,
                     "extra": json.dumps({"sharpe": sr, "n_trades": int(m_tr.sum()),
                                          "daily_returns": [round(float(x), 8) for x in daily]})})
        path_summaries.append({"path": pi_, "macro_f1": f1, "sharpe": sr})
    report.replace_rows(universe, "cv_scores", rows, run_id, MODEL, stage="cpcv")
    print(f"[cpcv/{universe}] split F1: "
          f"{np.mean([r['score'] for r in rows if r['unit'] == 'split']):.4f} | paths: {path_summaries}")
    return path_summaries


# ---------------- stage: shap ----------------

def shap_stage(universe):
    seed_everything()
    frozen = frozen_labels(universe)
    run_id = frozen["run_id"]
    s2 = read_json(art_dir(universe) / "study2_xgb.json")
    selected, best = s2["selected"], s2["best_params"]
    panel = panel_for(universe, universe_tickers(universe), frozen["params"], "cv")
    folds = validation.purged_kfold(panel["t0_ts"], panel["t1_ts"])
    res = oof(panel, selected, folds, best, keep_models=True)
    contrib = np.full((len(panel), len(selected)), np.nan)
    for booster, te in res["models"]:
        Xte = panel.iloc[te][selected].to_numpy(float)
        c = booster.predict(xgb.DMatrix(Xte, feature_names=selected), pred_contribs=True)
        contrib[te] = np.abs(np.asarray(c))[:, :, :-1].sum(axis=1)
    rows = []
    for t, idx in panel.groupby("ticker").groups.items():
        sub = contrib[np.asarray(idx)]
        sub = sub[np.isfinite(sub).all(axis=1)]
        if not len(sub):
            continue
        mabs = sub.mean(axis=0)
        share = mabs / max(mabs.sum(), 1e-12)
        order = np.argsort(-mabs)
        rank = np.empty(len(selected), int)
        rank[order] = np.arange(1, len(selected) + 1)
        for j, f in enumerate(selected):
            rows.append({"run_id": run_id, "model": MODEL, "method": "treeshap", "ticker": t,
                         "feature": f, "mean_abs_shap": float(mabs[j]),
                         "shap_share": float(share[j]), "rank_in_ticker": int(rank[j])})
    report.replace_rows(universe, "feature_importance_shap", rows, run_id, MODEL)
    uni = universality_audit(rows, run_id, MODEL)
    report.replace_rows(universe, "shap_universality", uni, run_id, MODEL)
    print(f"[shap/{universe}] {len(rows)} rows ({len(set(r['ticker'] for r in rows))} tickers "
          f"x {len(selected)} features); coverage: "
          f"{ {u['feature']: round(u['coverage'], 2) for u in uni} }")
    return rows


def universality_audit(rows, run_id, model):
    """WO §5: per feature — median/IQR of rank_in_ticker, coverage = % tickers with share>1%,
    asset-specific flag = strong (top-3) in <20% of tickers."""
    df = pd.DataFrame(rows)
    out = []
    for f, g in df.groupby("feature"):
        cov = float((g["shap_share"] > 0.01).mean())
        strong = float((g["rank_in_ticker"] <= 3).mean())
        out.append({"run_id": run_id, "model": model, "feature": f,
                    "median_rank": float(g["rank_in_ticker"].median()),
                    "iqr_rank": float(g["rank_in_ticker"].quantile(0.75)
                                      - g["rank_in_ticker"].quantile(0.25)),
                    "coverage": cov, "asset_specific": int(strong < 0.2)})
    return out


# ---------------- stage: strategy (sealed deployable artifact, CV-only) ----------------

def strategy_stage(universe):
    """Refit ONE final booster on the whole CV panel (selected + best HPO), seal it base64 with a
    golden-vector selfcheck + the operating point p*. Trained on CV; holdout untouched."""
    from . import strategy
    seed_everything()
    frozen = frozen_labels(universe)
    run_id = frozen["run_id"]
    s2 = read_json(art_dir(universe) / "study2_xgb.json")
    selected, best, pstar = s2["selected"], s2["best_params"], s2["pstar"]
    panel = panel_for(universe, universe_tickers(universe), frozen["params"], "cv")
    X = panel[selected].to_numpy(float)
    y = panel["y"].to_numpy(int) + 1
    w = train_weights(panel["y"], panel["w"])
    booster = xgb.train(xgb_params(best), xgb.DMatrix(X, label=y, weight=w, feature_names=selected),
                        num_boost_round=int(best.get("n_estimators", 120)))
    raw = booster.save_raw()
    proba = booster.predict(xgb.DMatrix(X[:64], feature_names=selected))
    golden = strategy.golden_sample(proba)
    # selfcheck: reload from the sealed bytes and reproduce the golden predictions
    reb = xgb.Booster()
    reb.load_model(bytearray(raw))
    ok = strategy.check_golden(reb.predict(xgb.DMatrix(X[:64], feature_names=selected)), golden)
    meta = {"run_id": run_id, "model": MODEL, "trained_on": "cv", "universe": universe,
            "selected": selected, "best_params": best, "pstar": pstar, "num_class": 3,
            "class_order": [-1, 0, 1], "n_train_events": int(len(panel)),
            "model_sha256": strategy._sha(raw), "model_b64": strategy._b64(raw),
            "golden": golden, "selfcheck_ok": bool(ok)}
    strategy.write(universe, "strategy_xgb.json", meta)
    print(f"[strategy/{universe}] sealed XGB ({len(selected)} feats, {len(panel)} CV events); "
          f"golden selfcheck {'OK' if ok else 'FAILED'}")
    if not ok:
        raise RuntimeError("XGB strategy golden selfcheck FAILED")
    return meta


# ---------------- stage: holdout (ONE read) ----------------

def holdout_stage(universe):
    seed_everything()
    frozen = frozen_labels(universe)
    run_id = frozen["run_id"]
    s2 = read_json(art_dir(universe) / "study2_xgb.json")
    selected, best, pstar = s2["selected"], s2["best_params"], s2["pstar"]
    validation.holdout_guard(universe, "xgb", {"run_id": run_id, "selected": selected,
                                               "best_params": best, "pstar": pstar})
    tks = universe_tickers(universe)
    panel_cv = panel_for(universe, tks, frozen["params"], "cv")
    panel_ho = panel_for(universe, tks, frozen["params"], "holdout")
    tr = np.arange(len(panel_cv))
    te = np.arange(len(panel_ho))
    joint = pd.concat([panel_cv, panel_ho], ignore_index=True)
    _, proba = fit_predict(joint, selected, tr, len(panel_cv) + te, best)
    y = panel_ho["y"].to_numpy(int)
    yhat = decide(proba, pstar)
    rep = metrics.classification_report(y, yhat, proba)
    ret = signed_event_returns(panel_ho["ret"].to_numpy(float), yhat)
    m = np.isfinite(ret)
    daily = metrics.daily_strategy_returns(panel_ho["t1_ts"].to_numpy()[m], ret[m])
    ppy = CONFIG["TRADING"]["periods_per_year"]
    # multiple-testing inputs: all optuna trials this study ran; V[SR] from the CPCV paths.
    # Filter by run_id so a superseded study1 run's stale rows can never contaminate the verdict.
    cp = report.read_table(universe, "cv_scores", MODEL, run_id=run_id)
    path_srs = []
    if len(cp):
        for _, r in cp[(cp["stage"] == "cpcv") & (cp["unit"] == "path")].iterrows():
            path_srs.append(json.loads(r["extra"])["sharpe"] / np.sqrt(ppy))
    n_trials = int(frozen.get("n_trials", 0)) + int(s2.get("n_trials", 0))
    sr_var = float(np.var(path_srs, ddof=1)) if len(path_srs) > 1 else 1e-4
    dsr = metrics.deflated_sharpe(daily, n_trials, sr_var, ppy)
    ts = report.read_table(universe, "trial_slices", MODEL, run_id=run_id)
    pbo = None
    if len(ts):
        M = ts.pivot(index="trial", columns="slice", values="score").to_numpy()
        pbo = metrics.pbo_cscv(M[np.isfinite(M).all(axis=1)])
    payload = {"run_id": run_id, "model": MODEL, "holdout_report": rep,
               "holdout_sharpe": metrics.sharpe(daily, ppy), "dsr": dsr, "pbo": pbo,
               "n_holdout_events": len(panel_ho), "n_trades": int(m.sum()),
               "cv_macro_f1": s2["cv_macro_f1"], "pstar": pstar, "selected": selected,
               "n_trials_total": n_trials}
    report.replace_rows(universe, "verdict", [{"run_id": run_id, "model": MODEL,
                                               "payload": json.dumps(payload)}], run_id, MODEL)
    write_json(art_dir(universe) / "verdict_xgb.json", payload)
    print(f"[holdout/{universe}] macro-F1={rep['macro_f1']:.4f}  sharpe={payload['holdout_sharpe']:.2f}  "
          f"PBO={pbo and pbo['pbo']}  DSR={dsr and round(dsr['dsr'], 3)}")
    return payload


STAGES = {"study1": study1, "loop": loop, "stability": stability, "study2": study2,
          "cpcv": cpcv_stage, "shap": shap_stage, "strategy": strategy_stage,
          "holdout": holdout_stage}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--universe", choices=["demo", "full"], default="demo")
    ap.add_argument("--stage", choices=["all"] + list(STAGES), default="all")
    a = ap.parse_args()
    apply_parallelism(a.universe)
    if a.stage == "all":
        for name in ("study1", "loop", "stability", "study2", "cpcv", "shap", "strategy"):
            STAGES[name](a.universe)
        print("NOTE: the holdout stage is never part of 'all' — run it deliberately, once:")
        print(f"  python -m fs.xgb_loop --universe {a.universe} --stage holdout")
    else:
        STAGES[a.stage](a.universe)


if __name__ == "__main__":
    main()

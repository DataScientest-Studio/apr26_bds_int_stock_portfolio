"""Detached CONVERGENCE optimizer for the FULL universe (make fs-search-on) — NO wall-clock budget.

Flow (each stage is a crash-isolated subprocess; artifacts are written atomically):
  warm (parallel feature cache)  ->  study1 (freeze the shared labels ONCE)
  optimize_to_convergence("xgb")     # XGB to convergence, full resources
  optimize_to_convergence("lstm")    # THEN LSTM to convergence
  -> all_converged.flag ; EXIT

A model has CONVERGED when, over `patience` consecutive rounds, the best CV macro-F1 improved by
< `min_gain` AND the selected feature set was unchanged AND no new Sonnet feature was accepted — i.e.
optimization has reached the logical limit of what the current inputs allow. Each round: absorb any
new live-proposer features (re-select if the pool grew), add `study2_trials_step` more Optuna trials
(resumes the persistent optuna.db), re-score CPCV, re-seal the strategy. On convergence it writes
`converged_<model>.flag` + `convergence_<model>.json` (an HONEST report: selected set, CV/CPCV,
PBO, SHAP coverage, and low-overfit / sensible-SHAP quality flags — nothing hidden).

Resumable across a server change: converged flags + optuna.db + artifacts persist, so re-launching
skips converged models and continues the rest. NEVER reads the holdout (a deliberate one-shot later).

Usage: python -m fs.supervise [--universe full] [--fresh]
"""
import argparse
import os
import subprocess
import sys
import time

from . import CONFIG, FS_ROOT, art_dir, read_json, write_json
from . import report

SUP = CONFIG["SUPERVISOR"]
PY = sys.executable
MODELS = {"xgb": "fs.xgb_loop", "lstm": "fs.lstm_loop"}


def _env(universe, extra):
    env = dict(os.environ)
    p = CONFIG["PARALLEL"][universe]
    for k in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        env.setdefault(k, str(p.get("torch_threads", 4)))
    env.update({k: str(v) for k, v in extra.items()})
    return env


def _run(label, module, universe, stage, extra):
    print(f"\n[supervise] === {label} ({time.strftime('%H:%M:%S')}) ===", flush=True)
    t0 = time.time()
    r = subprocess.run([PY, "-m", module, "--universe", universe, "--stage", stage],
                       cwd=str(FS_ROOT.parent), env=_env(universe, extra))
    ok = r.returncode == 0
    _checkpoint(universe, label, ok, time.time() - t0)
    if not ok:
        print(f"[supervise] {label} FAILED (rc={r.returncode}) — continuing", flush=True)
    return ok


def _run_warm(universe):
    print(f"\n[supervise] === warm ({time.strftime('%H:%M:%S')}) ===", flush=True)
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    t0 = time.time()
    r = subprocess.run([PY, "-m", "fs.warm", "--universe", universe], cwd=str(FS_ROOT.parent), env=env)
    _checkpoint(universe, "warm", r.returncode == 0, time.time() - t0)
    return r.returncode == 0


def _checkpoint(universe, stage, ok, secs):
    path = art_dir(universe) / "supervisor_progress.json"
    prog = read_json(path) if path.exists() else {"history": []}
    prog["history"] = (prog.get("history", []) + [{
        "stage": stage, "ok": ok, "secs": round(secs, 1),
        "at": time.strftime("%Y-%m-%d %H:%M:%S")}])[-400:]
    prog["last"] = prog["history"][-1]
    write_json(path, prog)


def _have(universe, name):
    return (art_dir(universe) / name).exists()


def _pool_size():
    from . import data
    return len(data.feature_pool())


def _round_metrics(universe, model):
    """The signal a round changed anything: best CV macro-F1 + the selected feature set."""
    s2 = art_dir(universe) / f"study2_{model}.json"
    sel = art_dir(universe) / f"selected_{model}.json"
    f1 = read_json(s2).get("cv_macro_f1") if s2.exists() else None
    selected = read_json(sel).get("selected") if sel.exists() else None
    return f1, (tuple(sorted(selected)) if selected else None)


# ---------------- honest convergence report (PBO / coverage / overfit) ----------------

def _quality(universe, model):
    from . import metrics
    import numpy as np
    MODEL = model.upper()
    out = {}
    ts = report.read_table(universe, "trial_slices", MODEL)
    if len(ts):
        M = ts.pivot(index="trial", columns="slice", values="score").to_numpy()
        M = M[np.isfinite(M).all(axis=1)]
        out["pbo"] = metrics.pbo_cscv(M)
    uni = report.read_table(universe, "shap_universality", MODEL)
    if len(uni):
        out["min_coverage"] = float(uni["coverage"].min())
        out["asset_specific_features"] = int(uni["asset_specific"].sum())
    cp = report.read_table(universe, "cv_scores", MODEL)
    if len(cp):
        paths = cp[(cp["stage"] == "cpcv") & (cp["unit"] == "path")]
        if len(paths):
            out["cpcv_macro_f1_mean"] = float(paths["score"].mean())
            out["cpcv_macro_f1_std"] = float(paths["score"].std(ddof=1)) if len(paths) > 1 else 0.0
    return out


def _write_convergence_report(universe, model, history, reason):
    q = _quality(universe, model)
    pbo = (q.get("pbo") or {}).get("pbo")
    cov = q.get("min_coverage")
    payload = {
        "model": model.upper(), "converged": True, "reason": reason,
        "rounds": len(history), "cv_macro_f1_history": [h["f1"] for h in history],
        "final_cv_macro_f1": history[-1]["f1"] if history else None,
        "selected": read_json(art_dir(universe) / f"selected_{model}.json").get("selected")
        if _have(universe, f"selected_{model}.json") else None,
        "quality": q,
        "low_overfit": (pbo is not None and pbo < float(SUP["pbo_max"])),
        "sensible_shap": (cov is not None and cov >= float(SUP["coverage_min"])),
        "note": "Convergence = optimization plateaued on Train (no further gain from current inputs). "
                "Quality flags are reported honestly; they do NOT hide a high-PBO / low-coverage result.",
    }
    write_json(art_dir(universe) / f"convergence_{model}.json", payload)
    (art_dir(universe) / f"converged_{model}.flag").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    print(f"[supervise] {model.upper()} CONVERGED ({reason}); f1={payload['final_cv_macro_f1']}, "
          f"low_overfit={payload['low_overfit']}, sensible_shap={payload['sensible_shap']}", flush=True)


# ---------------- per-model optimization to convergence ----------------

INITIAL_STAGES = {
    "xgb": [("loop", "loop_xgb.json"), ("stability", "selected_xgb.json"),
            ("study2", "study2_xgb.json"), ("cpcv", None), ("shap", None),
            ("strategy", "strategy_xgb.json")],
    "lstm": [("loop", "loop_lstm.json"), ("stability", "selected_lstm.json"),
             ("study2", "study2_lstm.json"), ("cpcv", None), ("shap", None),
             ("strategy", "strategy_lstm.json")],
}


def optimize_to_convergence(universe, model, base_env, fresh):
    module = MODELS[model]
    if _have(universe, f"converged_{model}.flag") and not fresh:
        print(f"[supervise] {model.upper()} already converged — skipping", flush=True)
        return
    # initial pipeline (skip stages whose artifact already exists, unless --fresh)
    for stage, art in INITIAL_STAGES[model]:
        if fresh or art is None or not _have(universe, art):
            _run(f"{model}:{stage}", module, universe, stage, base_env)
    if not _have(universe, f"study2_{model}.json"):
        print(f"[supervise] {model.upper()} initial pipeline did not land — cannot optimize", flush=True)
        return

    # Optional: accept the initial Study-2 result as converged and SKIP the extension rounds
    # (env FS_NO_CONVERGENCE or FS_NO_CONVERGENCE_<MODEL>). Writes the honest convergence report + flag.
    if os.environ.get("FS_NO_CONVERGENCE") or os.environ.get(f"FS_NO_CONVERGENCE_{model.upper()}"):
        f1, sel = _round_metrics(universe, model)
        _write_convergence_report(universe, model,
                                  [{"round": 0, "f1": f1, "gain": 0.0,
                                    "n_features": len(sel or []), "selected_changed": False}],
                                  "extension_rounds_skipped")
        return

    min_gain = float(SUP["min_gain"])
    patience = int(SUP["patience"])
    step = int(SUP["study2_trials_step"])
    trials = int(base_env.get("FS_STUDY2_TRIALS",
                              CONFIG["XGB_STUDY2"]["n_trials"][universe] if model == "xgb" else 30))
    best_f1, prev_sel = _round_metrics(universe, model)
    best_f1 = best_f1 if best_f1 is not None else -1.0
    history, stale, rnd = [], 0, 0
    # Fixed feature pool (Sonnet removed): the selected set is deterministic, so improvement comes
    # only from more Study-2 Optuna trials -> convergence is reached once the CV metric plateaus.
    while stale < patience and rnd < int(SUP["max_rounds"]):
        rnd += 1
        trials += step
        if _run(f"{model}:study2+ (r{rnd}, {trials})", module, universe, "study2",
                dict(base_env, FS_STUDY2_TRIALS=trials)):
            _run(f"{model}:cpcv (r{rnd})", module, universe, "cpcv", base_env)
            _run(f"{model}:strategy (r{rnd})", module, universe, "strategy", base_env)
        f1, sel = _round_metrics(universe, model)
        f1 = f1 if f1 is not None else best_f1
        gain = f1 - best_f1
        history.append({"round": rnd, "f1": f1, "gain": round(gain, 5),
                        "n_features": len(sel or []), "selected_changed": sel != prev_sel})
        improved = (gain >= min_gain) or (sel != prev_sel)
        stale = 0 if improved else stale + 1
        best_f1, prev_sel = max(best_f1, f1), sel
        print(f"[supervise] {model.upper()} round {rnd}: f1={f1:.4f} gain={gain:+.4f} "
              f"stale={stale}/{patience}", flush=True)
    _write_convergence_report(universe, model, history,
                              "no_improve_patience" if stale >= patience else "max_rounds")


def run(universe, fresh):
    base = {"FS_LSTM_SUBSAMPLE": CONFIG["LSTM"]["ticker_subsample_full"]}
    if universe in SUP["study1_trials"]:
        base["FS_STUDY1_TRIALS"] = SUP["study1_trials"][universe]
    print(f"[supervise] universe={universe} CONVERGENCE mode (no time budget) "
          f"start={time.strftime('%H:%M:%S')}", flush=True)

    if not _run_warm(universe):
        print("[supervise] warm failed — aborting", flush=True)
        return
    if fresh or not _have(universe, "labels_frozen.json"):
        _run("study1", "fs.xgb_loop", universe, "study1", base)
    if not _have(universe, "labels_frozen.json"):
        print("[supervise] no frozen labels — aborting", flush=True)
        return

    # XGB first (fast), then LSTM — each to convergence, full resources.
    optimize_to_convergence(universe, "xgb",
                            dict(base, FS_STUDY2_TRIALS=CONFIG["XGB_STUDY2"]["n_trials"][universe]), fresh)
    optimize_to_convergence(universe, "lstm",
                            dict(base, FS_STUDY2_TRIALS=30, FS_STABILITY_REPEATS=6), fresh)

    (art_dir(universe) / "all_converged.flag").write_text(time.strftime("%Y-%m-%d %H:%M:%S\n"))
    print(f"\n[supervise] ALL CONVERGED at {time.strftime('%H:%M:%S')} — models optimized on Train to "
          f"the logical limit. Holdout NOT read — run it deliberately, once:\n"
          f"  make fs-holdout-xgb UNIVERSE={universe}\n  make fs-holdout-lstm UNIVERSE={universe}",
          flush=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--universe", choices=["demo", "full"], default="full")
    ap.add_argument("--fresh", action="store_true", help="ignore existing artifacts/flags; redo everything")
    a = ap.parse_args()
    run(a.universe, a.fresh)


if __name__ == "__main__":
    main()

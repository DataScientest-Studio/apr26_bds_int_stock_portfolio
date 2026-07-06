"""WO-FS-LSTM-v1 — the LSTM channel-selection loop (docs/LSTM-ZLECENIE-LOOP.md).

Consumes the SAME frozen labels as the XGB loop (Study 1 — one label truth) and starts from the
XGB ranking (top-k) plus the forced cross-TF mean-reversion channel. Sequences are L×F windows of
1h bars ending at t0 (1d/1w channels are piecewise-constant between higher-TF closes — the ffill
from the last CLOSED bar comes from the causal join in fs.data). Purge = L + H via t_start.

Scaling contract (WO §1, the classic leak source): the z-score scaler of every fold is fit on
that fold's TRAIN REGION bars only (CV bars outside the test block widened by L on the left and
the embargo on the right); parameters are persisted per fold to artifacts/<u>/scalers/.

Loop protocol (economy, WO §4.2): 2 seeds × few epochs during elimination; the finalist and every
verdict stage (study2/cpcv/holdout) run the full protocol (≥3 seeds, early stopping, std reported).

Stages: loop | stability | study2 | cpcv | shap | holdout
Usage: python -m fs.lstm_loop --universe demo|full --stage all|...
"""
import argparse
import json
import os

os.environ.setdefault("OMP_NUM_THREADS", "2")  # before numpy/torch import (repo gotcha)

import numpy as np
import pandas as pd

from . import CONFIG, SEED, art_dir, read_json, seed_everything, write_json
from . import data, labels, metrics, report, validation
from .features import MR_CHANNEL
from .xgb_loop import (apply_parallelism, build_panel, feature_set_key, decide, env_int, frozen_labels,
                       signed_event_returns, suggest, train_weights, universality_audit,
                       universe_tickers)

MODEL = "LSTM"
LC = CONFIG["LSTM"]
_TORCH_THREADS = int(CONFIG["TORCH_THREADS"])
_BATCH = int(LC["batch"])


def apply_lstm_parallelism(universe, single=False):
    """Full-resources use: raise torch's CPU thread count (capped at os.cpu_count()-1, overridable via
    FS_TORCH_THREADS) so each training uses the box, plus a larger batch; set BLAS env caps to match.
    A smaller server auto-adapts via the cap.

    Two stage shapes need OPPOSITE thread counts (see BEST_PRACTICE_FOR_ML_LOOPS_ON_THIS_SERVER.md
    sec.4/8): fan-out stages (cpcv/loop/study2) run many worker processes, so each worker takes FEW
    threads (`torch_threads`); a SINGLE-training stage (strategy/holdout) is one heavy fit and must take
    the whole box (`torch_threads_single` ~ cores-1) -- else it crawls on 2 cores while the rest idle."""
    global _TORCH_THREADS, _BATCH
    p = CONFIG.get("PARALLEL", {}).get(universe, {})
    key = "torch_threads_single" if single else "torch_threads"
    want = int(p.get(key, p.get("torch_threads", CONFIG["TORCH_THREADS"])))
    _TORCH_THREADS = env_int("FS_TORCH_THREADS", min(want, max(1, (os.cpu_count() or 2) - 1)))
    _BATCH = int(p.get("batch", LC["batch"]))
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[v] = str(_TORCH_THREADS)
    print(f"[parallelism] lstm torch_threads={_TORCH_THREADS} (single={single}) batch={_BATCH}", flush=True)


def lstm_subsample(universe):
    if universe != "full":
        return None
    return env_int("FS_LSTM_SUBSAMPLE", LC["ticker_subsample_full"])


# ---------------- scaling contract ----------------
#
# The z-score scaler of every fold is fit on that fold's TRAIN-REGION bars ONLY (WO-LSTM §1.2-1.3).
# "Train region" = bars inside the CV window [cv_start, cv_end] (so warmup 2016 and the 2024→2026
# holdout are never in the statistics) MINUS the fold's test region. The test region is excluded by
# REAL bar timestamps: each test sequence spans bars [t0−L+1 .. t0] and its label reaches t1, so a
# test group excludes [close_ts(t0−L+1) .. t1_ts + embargo]. For CPCV the test groups can be
# non-adjacent, so we pass ONE interval PER test group instead of a single min/max span — otherwise
# the gap between two far-apart test groups (the legitimate middle train groups) would be dropped.

def cv_bounds_ts():
    s = CONFIG["SPLITS"]
    return (pd.Timestamp(s["cv_start"], tz="UTC"),
            pd.Timestamp(s["cv_end"], tz="UTC") + pd.Timedelta(days=1))


def scaler_exclude_intervals(events, idxs, tstart, group_of=None, test_groups=None):
    """Intervals of bar close_ts to keep OUT of a fold's scaler. tstart[i] = close_ts of the first
    input bar of event i (from lstm_t_start). Each interval = [min first-input-bar, max t1 + embargo]
    over the events of one test block; per contiguous test group so non-adjacent CPCV groups leave
    the intervening train groups intact."""
    emb = pd.Timedelta(int(validation.embargo_ns()), unit="ns")
    idxs = np.asarray(idxs)
    t1 = pd.to_datetime(events["t1_ts"], utc=True).reset_index(drop=True)  # tz-aware
    ts = tstart.reset_index(drop=True)                                     # tz-aware
    groups = [idxs] if test_groups is None else [idxs[group_of[idxs] == g] for g in test_groups]
    out = []
    for gi in groups:
        if len(gi):
            out.append((ts.iloc[gi].min(), t1.iloc[gi].max() + emb))
    return out


def pooled_scaler_stats(frames, names, cv_bounds, exclude_intervals=()):
    """Universal-model scaler: μ/σ pooled over every ticker's bars inside cv_bounds and outside all
    exclude_intervals (finite values only, σ floor 1e-8, deterministic ticker order)."""
    lo_cv, hi_cv = cv_bounds
    acc = {n: [0.0, 0.0, 0] for n in names}
    for t in sorted(frames):
        bars, feats = frames[t]
        ct = bars["close_ts"]
        mask = ((ct >= lo_cv) & (ct <= hi_cv)).to_numpy()
        for elo, ehi in exclude_intervals:
            mask &= ~((ct >= elo) & (ct <= ehi)).to_numpy()
        for n in names:
            x = feats[n].to_numpy(float)[mask]
            x = x[np.isfinite(x)]
            acc[n][0] += float(x.sum())
            acc[n][1] += float((x ** 2).sum())
            acc[n][2] += len(x)
    out = {}
    for n, (s, s2, k) in acc.items():
        mu = s / k if k else 0.0
        var = max(s2 / k - mu ** 2, 0.0) if k else 1.0
        out[n] = {"mean": mu, "std": max(var ** 0.5, 1e-8)}
    return out


def fold_scaler_stats(bars, feats, names, before_ts=None, exclude=None):
    """Single-ticker scaler used only by the leak gate test (tests.py): μ/σ over one ticker's bars
    strictly before before_ts, or outside exclude=(lo,hi)."""
    mask = np.ones(len(bars), bool)
    ct = bars["close_ts"]
    if before_ts is not None:
        mask &= (ct < before_ts).to_numpy()
    if exclude is not None:
        mask &= ~((ct >= exclude[0]) & (ct <= exclude[1])).to_numpy()
    stats = {}
    for n in names:
        x = feats[n].to_numpy(float)[mask]
        x = x[np.isfinite(x)]
        stats[n] = {"mean": float(x.mean()) if len(x) else 0.0,
                    "std": max(float(x.std()), 1e-8) if len(x) else 1.0}
    return stats


# ---------------- sequence dataset ----------------

def eligible_events(panel, frames, channels, seq_len_max):
    """Freeze the event set on the SUPERSET of candidate channels at L_max: window exists and is
    finite. Every subset / every Study-2 L is then scored on identical events (repo lesson)."""
    keep = np.zeros(len(panel), bool)
    fin = {t: np.isfinite(frames[t][1][channels].to_numpy(float)).all(axis=1)
           for t in frames}
    for i, (t, t0) in enumerate(zip(panel["ticker"], panel["t0_idx"])):
        t0 = int(t0)
        if t0 >= seq_len_max - 1 and fin[t][t0 - seq_len_max + 1:t0 + 1].all():
            keep[i] = True
    out = panel[keep].reset_index(drop=True)
    return labels.assign_uniqueness(out)


def build_X(events, frames_norm, channels, seq_len):
    X = np.empty((len(events), seq_len, len(channels)), np.float32)
    for i, (t, t0) in enumerate(zip(events["ticker"], events["t0_idx"])):
        t0 = int(t0)
        X[i] = frames_norm[t][t0 - seq_len + 1:t0 + 1]
    return X


def normalize_frames(frames, channels, stats):
    return {t: ((feats[channels].to_numpy(float)
                 - np.array([stats[c]["mean"] for c in channels]))
                / np.array([stats[c]["std"] for c in channels])).astype(np.float32)
            for t, (bars, feats) in frames.items()}


# ---------------- model ----------------

def _torch():
    import torch
    torch.set_num_threads(_TORCH_THREADS)
    torch.use_deterministic_algorithms(True)
    return torch


def make_model(torch, n_channels, arch):
    class LSTM3(torch.nn.Module):
        def __init__(self):
            super().__init__()
            nl = int(arch["num_layers"])
            self.lstm = torch.nn.LSTM(n_channels, int(arch["hidden"]), num_layers=nl,
                                      batch_first=True,
                                      dropout=float(arch["dropout"]) if nl > 1 else 0.0)
            self.drop = torch.nn.Dropout(float(arch["dropout"]))
            self.head = torch.nn.Linear(int(arch["hidden"]), 3)

        def forward(self, x):
            out, _ = self.lstm(x)
            return self.head(self.drop(out[:, -1]))
    return LSTM3()


def train_model(X, y, w, Xva, yva, arch, epochs, seed, patience=None):
    """Weighted 3-class CE, Adam, early stopping on val macro-F1 (patience), best state restored.
    Deterministic per seed (torch deterministic algorithms + seeded batch order)."""
    torch = _torch()
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = make_model(torch, X.shape[2], arch)
    opt = torch.optim.Adam(model.parameters(), lr=float(arch["lr"]),
                           weight_decay=float(arch["weight_decay"]))
    Xt = torch.from_numpy(X)
    yt = torch.from_numpy((y + 1).astype(np.int64))
    wt = torch.from_numpy(w.astype(np.float32))
    B = int(arch["batch"])
    best_f1, best_state, best_epoch, since = -np.inf, None, 0, 0
    for ep in range(int(epochs)):
        model.train()
        order = rng.permutation(len(Xt))
        for i in range(0, len(order), B):
            b = order[i:i + B]
            opt.zero_grad()
            logits = model(Xt[b])
            loss = (torch.nn.functional.cross_entropy(logits, yt[b], reduction="none")
                    * wt[b]).mean()
            loss.backward()
            opt.step()
        if Xva is not None and patience is not None:
            f1 = metrics.macro_f1(yva, decide(predict(model, Xva)))
            if f1 > best_f1:
                best_f1, best_epoch, since = f1, ep, 0
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            else:
                since += 1
                if since >= patience:
                    break
    if best_state is not None:
        model.load_state_dict(best_state)
    model.eval()
    return model, best_epoch


def predict(model, X, batch=4096):
    torch = _torch()
    out = []
    with torch.no_grad():
        for i in range(0, len(X), batch):
            logits = model(torch.from_numpy(X[i:i + batch]))
            out.append(torch.softmax(logits, dim=1).numpy())
    return np.concatenate(out) if out else np.empty((0, 3))


# ---------------- OOF over purged folds ----------------

def lstm_t_start(events, frames, seq_len):
    """t_start timestamps for purge = L + H: the close_ts of bar t0 − (L−1) per event."""
    vals = np.empty(len(events), np.int64)
    for i, (t, t0) in enumerate(zip(events["ticker"], events["t0_idx"])):
        bars = frames[t][0]
        j = max(int(t0) - int(seq_len) + 1, 0)
        vals[i] = bars["close_ts"].iloc[j].value  # tz-aware -> UTC epoch ns
    return pd.Series(pd.to_datetime(vals, utc=True))


def lstm_folds(events, frames, seq_len, k=None):
    return validation.purged_kfold(events["t0_ts"], events["t1_ts"],
                                   t_start_ts=lstm_t_start(events, frames, seq_len), k=k)


def _lstm_train_worker(args):
    """Train ONE (fold, seed) LSTM in a worker process and predict its test tensor. torch threads are
    fixed (=_TORCH_THREADS) so the trained weights are byte-identical to the serial path — running the
    many independent (fold, seed) trainings concurrently just fills the cores one RNN can't. Returns
    (proba_te, state_dict_bytes|None)."""
    import io
    Xtr, ytr, wtr, Xte, arch, epochs, seed, patience, n_va, keep = args
    if patience is not None and n_va and n_va < len(Xtr) // 2:
        m, _ = train_model(Xtr[:-n_va], ytr[:-n_va], wtr[:-n_va],
                           Xtr[-n_va:], ytr[-n_va:], arch, epochs, seed, patience)
    else:
        m, _ = train_model(Xtr, ytr, wtr, None, None, arch, epochs, seed)
    p = predict(m, Xte)
    if keep:
        import torch
        buf = io.BytesIO()
        torch.save(m.state_dict(), buf)
        return p, buf.getvalue()
    return p, None


def oof_lstm(events, frames, channels, folds, arch, epochs, seeds, patience=None,
             keep_models=False, save_scalers_to=None):
    """Purged-fold OOF with the WO scaling contract; probabilities averaged over seeds. The (fold,
    seed) trainings run IN PARALLEL processes (byte-identical to serial). Returns fold-level macro-F1,
    per-seed F1 std, and the fold models (rebuilt from the workers' state dicts when keep_models)."""
    from .xgb_loop import _PANEL_WORKERS, _panel_pool
    seq_len = int(arch["seq_len"])
    tstart = lstm_t_start(events, frames, seq_len)  # close_ts of each event's first input bar
    cvb = cv_bounds_ts()
    fold_data, tasks = [], []
    for fi, (tr, te) in enumerate(folds):
        stats = pooled_scaler_stats(frames, channels, cvb,
                                    scaler_exclude_intervals(events, te, tstart))
        if save_scalers_to:
            write_json(save_scalers_to / f"fold{fi}.json", stats)
        norm = normalize_frames(frames, channels, stats)
        Xtr = build_X(events.iloc[tr], norm, channels, seq_len)
        Xte = build_X(events.iloc[te], norm, channels, seq_len)
        ytr = events.iloc[tr]["y"].to_numpy(int)
        yte = events.iloc[te]["y"].to_numpy(int)
        wtr = train_weights(ytr, events.iloc[tr]["w"].to_numpy(float))
        n_va = max(int(0.15 * len(tr)), 50) if patience is not None else 0
        fold_data.append((te, yte, norm))
        for sd in seeds:
            tasks.append((Xtr, ytr, wtr, Xte, arch, epochs, sd, patience, n_va, keep_models))
    if _PANEL_WORKERS > 1 and len(tasks) > 1:
        results = list(_panel_pool().map(_lstm_train_worker, tasks))
    else:
        results = [_lstm_train_worker(t) for t in tasks]

    proba = np.full((len(events), 3), np.nan)
    fold_f1, fold_ll, per_seed_f1, models = [], [], [], []
    ns = len(seeds)
    for fi, (te, yte, norm) in enumerate(fold_data):
        chunk = results[fi * ns:(fi + 1) * ns]
        ps = [p for p, _ in chunk]
        per_seed_f1.append([metrics.macro_f1(yte, decide(p)) for p in ps])
        p_mean = np.mean(ps, axis=0)
        proba[te] = p_mean
        fold_f1.append(metrics.macro_f1(yte, decide(p_mean)))
        fold_ll.append(metrics.fold_log_loss(yte, p_mean))
        if keep_models:
            import io
            import torch
            fold_models = []
            for _, sb in chunk:
                mm = make_model(torch, len(channels), arch)
                mm.load_state_dict(torch.load(io.BytesIO(sb)))
                mm.eval()
                fold_models.append(mm)
            models.append((fold_models, te, norm))
    seed_std = float(np.std(np.asarray(per_seed_f1).mean(axis=0), ddof=1)) if len(seeds) > 1 else 0.0
    return {"proba": proba, "fold_f1": fold_f1, "fold_ll": fold_ll, "models": models,
            "mean": float(np.mean(fold_f1)),
            "se": float(np.std(fold_f1, ddof=1) / np.sqrt(len(fold_f1))),
            "seed_std": seed_std}


# ---------------- channel importance ----------------

def channel_perm_importance(events, channels, res, arch, repeats, rng):
    """WO §4.3: shuffle ONE channel across sequences on each fold's OOF set (whole-window
    permutation), Δ macro-F1 averaged over folds × repeats × seed-averaged models."""
    seq_len = int(arch["seq_len"])
    deltas = {c: [] for c in channels}
    for (fold_models, te, norm), base in zip(res["models"], res["fold_f1"]):
        Xte = build_X(events.iloc[te], norm, channels, seq_len)
        yte = events.iloc[te]["y"].to_numpy(int)
        for ci, c in enumerate(channels):
            for _ in range(repeats):
                perm = rng.permutation(len(Xte))
                Xp = Xte.copy()
                Xp[:, :, ci] = Xte[perm][:, :, ci]
                p = np.mean([predict(m, Xp) for m in fold_models], axis=0)
                deltas[c].append(base - metrics.macro_f1(yte, decide(p)))
    return {c: float(np.mean(v)) for c, v in deltas.items()}


# ---------------- stage: loop ----------------

def start_channels(universe):
    rk = read_json(art_dir(universe) / "xgb_feature_ranking.json")
    top = rk["ranking"][:int(LC["start_top_k"])]
    if MR_CHANNEL not in top:
        top = top + [MR_CHANNEL]  # WO §4.1: the cross-TF mean-reversion representative is forced
    return top


def loop_arch():
    a = {k: LC[k] for k in ("seq_len", "hidden", "num_layers", "dropout", "lr", "weight_decay")}
    a["batch"] = _BATCH
    return a


def run_elimination(events, frames, channels, folds, arch, seeds, epochs, rng, record=None):
    traj = []
    active = list(channels)
    best, since = -np.inf, 0
    rnd = 0
    while True:
        res = oof_lstm(events, frames, active, folds, arch, epochs, seeds, keep_models=True)
        traj.append((list(active), res["mean"], res["se"], res["seed_std"]))
        perm = channel_perm_importance(events, active, res, arch, int(LC["perm_repeats"]), rng)
        cands = sorted(active, key=lambda c: perm[c])[:int(LC["ablation_candidates"])]
        # ablation (WO §4.3): retrain without each removal candidate, drop the least harmful
        abl = {}
        for c in cands:
            sub = [x for x in active if x != c]
            abl[c] = oof_lstm(events, frames, sub, folds, arch, epochs, seeds)["mean"]
        weakest = max(abl, key=abl.get)
        if record:
            record({"round": rnd, "n_features": len(active), "cv_mean": res["mean"],
                    "cv_se": res["se"], "removed": json.dumps([weakest]),
                    "features": json.dumps(active), "mda": json.dumps(perm),
                    "control": json.dumps({"ablation": abl, "seed_std": res["seed_std"]})})
        if res["mean"] > best:
            best, since = res["mean"], 0
        else:
            since += 1
        scores = [t[1] for t in traj]
        ses = [t[2] for t in traj]
        i_best = int(np.argmax(scores))
        if (res["mean"] < scores[i_best] - ses[i_best]
                or since >= int(LC["stop_no_improve_rounds"])
                or len(active) - 1 < int(LC["min_channels"])):
            break
        active.remove(weakest)
        rnd += 1
    ok = [i for i, t in enumerate(traj) if len(t[0]) <= int(LC["max_channels"])] or [len(traj) - 1]
    sub_i = metrics.one_se_choice([len(traj[i][0]) for i in ok], [traj[i][1] for i in ok],
                                  [traj[i][2] for i in ok])
    return traj, list(traj[ok[sub_i]][0])


def prepare(universe, subsample=None, window="cv"):
    """Frames + the frozen event set. Eligibility is ALWAYS on the SUPERSET (start channels) at
    L_max, so the loop, study2, cpcv, shap and holdout all score identical events."""
    frozen = frozen_labels(universe)
    tickers = universe_tickers(universe, subsample)
    frames = {t: data.bar_frame(t, universe) for t in tickers}
    panel = build_panel(frames, frozen["params"], window)
    chans = start_channels(universe)
    events = eligible_events(panel, frames, chans, int(LC["seq_len_max"]))
    return frozen, frames, events, chans


def loop(universe):
    seed_everything()
    sub = lstm_subsample(universe)
    frozen, frames, events, chans = prepare(universe, subsample=sub)
    folds = lstm_folds(events, frames, int(LC["seq_len"]))
    rng = np.random.default_rng(SEED)
    rows = []
    traj, chosen = run_elimination(events, frames, chans, folds, loop_arch(),
                                   LC["seeds"][:2], int(LC["epochs_economy"]), rng,
                                   record=rows.append)
    run_id = frozen["run_id"]
    for r in rows:
        r.update(run_id=run_id, model=MODEL)
    report.replace_rows(universe, "loop_rounds", rows, run_id, MODEL)
    write_json(art_dir(universe) / "loop_lstm.json",
               {"run_id": run_id, "start_channels": chans, "one_se_choice": chosen,
                "trajectory": [{"features": t[0], "mean": t[1], "se": t[2], "seed_std": t[3]}
                               for t in traj]})
    print(f"[loop/{universe}] rounds={len(traj)}  1-SE choice ({len(chosen)}): {chosen}")
    return chosen


def stability(universe):
    seed_everything()
    sub = lstm_subsample(universe)
    frozen, frames, events, chans = prepare(universe, subsample=sub)
    run_id = frozen["run_id"]
    rng = np.random.default_rng(SEED)
    R = env_int("FS_STABILITY_REPEATS", LC["stability_repeats"])
    counts = {c: 0 for c in chans}
    tickers = sorted(frames)
    for r in range(R):
        st = sorted(rng.choice(tickers, size=max(3, int(0.75 * len(tickers))), replace=False))
        ev = events[events["ticker"].isin(st)].reset_index(drop=True)
        ev = labels.assign_uniqueness(ev)
        fr = {t: frames[t] for t in st}
        folds = lstm_folds(ev, fr, int(LC["seq_len"]))
        _, chosen = run_elimination(ev, fr, chans, folds, loop_arch(),
                                    LC["seeds"][:1], max(int(LC["epochs_economy"]) - 3, 4), rng)
        for c in chosen:
            counts[c] += 1
        print(f"  repeat {r + 1}/{R}: |set|={len(chosen)}")
    pi = {c: counts[c] / R for c in chans}
    selected = [c for c in chans if pi[c] >= float(LC["stability_pi"])]
    if len(selected) > int(LC["max_channels"]):
        selected = sorted(selected, key=lambda c: -pi[c])[:int(LC["max_channels"])]
    if len(selected) < int(LC["min_channels"]):
        selected = sorted(chans, key=lambda c: -pi[c])[:int(LC["min_channels"])]
    report.replace_rows(universe, "stability",
                        [{"run_id": run_id, "model": MODEL, "feature": c, "pi": pi[c]}
                         for c in chans], run_id, MODEL)
    write_json(art_dir(universe) / "selected_lstm.json",
               {"run_id": run_id, "selected": selected, "pi": pi})
    print(f"[stability/{universe}] selected (pi>={LC['stability_pi']}): {selected}")
    return selected


# ---------------- stage: study2 (+ p*) ----------------

def study2(universe):
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    seed_everything()
    cfg = CONFIG["LSTM_STUDY2"]
    sub = lstm_subsample(universe)
    frozen, frames, events, _ = prepare(universe, subsample=sub)
    run_id = frozen["run_id"]
    selected = read_json(art_dir(universe) / "selected_lstm.json")["selected"]
    n_slices = int(CONFIG["PBO_SLICES"])

    def objective(trial):
        arch = suggest(trial, cfg["space"])
        folds = lstm_folds(events, frames, int(arch["seq_len"]))
        res = oof_lstm(events, frames, selected, folds, arch,
                       int(LC["epochs_economy"]) + 4, LC["seeds"][:2],
                       patience=int(LC["patience"]))
        for i, ll in enumerate(res["fold_ll"]):
            trial.report(-ll, step=i)  # log-loss pruning; negated (study maximizes)
            if trial.should_prune():
                raise optuna.TrialPruned()
        from .xgb_loop import slice_scores
        trial.set_user_attr("slices", slice_scores(events, res["proba"], n_slices))
        trial.set_user_attr("seed_std", res["seed_std"])
        return res["mean"]

    study = optuna.create_study(
        study_name=f"study2_lstm_{universe}_{feature_set_key(selected)}", direction="maximize",
        storage=f"sqlite:///{art_dir(universe) / 'optuna.db'}", load_if_exists=True,
        sampler=optuna.samplers.TPESampler(seed=SEED),
        pruner=optuna.pruners.MedianPruner(n_warmup_steps=int(cfg["pruner_warmup"])))
    n_trials = env_int("FS_STUDY2_TRIALS", cfg["n_trials"][universe])
    done = len([t for t in study.trials if t.state.is_finished()])
    if done < n_trials:
        study.optimize(objective, n_trials=n_trials - done)

    report.replace_rows(universe, "trial_slices",
                        [{"run_id": run_id, "model": MODEL, "trial": t.number, "slice": i,
                          "score": s}
                         for t in study.trials if t.user_attrs.get("slices")
                         for i, s in enumerate(t.user_attrs["slices"])], run_id, MODEL)

    best = dict(study.best_trial.params)
    folds = lstm_folds(events, frames, int(best["seq_len"]))
    scal_dir = art_dir(universe) / "scalers" / "lstm_best"
    res = oof_lstm(events, frames, selected, folds, best, int(LC["epochs_full"]),
                   LC["seeds"], patience=int(LC["patience"]), save_scalers_to=scal_dir)
    grid = np.arange(CONFIG["PSTAR"]["low"], CONFIG["PSTAR"]["high"] + 1e-9, CONFIG["PSTAR"]["step"])
    ok = np.isfinite(res["proba"]).all(axis=1)
    y_oof = events["y"].to_numpy(int)[ok]
    pstar, pf1 = None, -np.inf
    for p in grid:
        f1 = metrics.macro_f1(y_oof, decide(res["proba"][ok], float(p)))
        if f1 > pf1:
            pstar, pf1 = float(p), f1
    payload = {"run_id": run_id, "selected": selected, "best_params": best,
               "cv_macro_f1": res["mean"], "cv_se": res["se"], "seed_std": res["seed_std"],
               "pstar": pstar, "pstar_macro_f1": pf1, "n_trials": len(study.trials)}
    write_json(art_dir(universe) / "study2_lstm.json", payload)
    report.replace_rows(universe, "cv_scores",
                        [{"run_id": run_id, "model": MODEL, "stage": "study2_best",
                          "unit": "fold", "unit_id": str(i), "score": s, "extra": None}
                         for i, s in enumerate(res["fold_f1"])], run_id, MODEL, stage="study2_best")
    print(f"[study2/{universe}] best={best}  CV={res['mean']:.4f}±{res['se']:.4f} "
          f"seed_std={res['seed_std']:.4f}  p*={pstar} (F1={pf1:.4f})")
    return payload


# ---------------- stage: cpcv ----------------

def cpcv_stage(universe):
    seed_everything()
    sub = lstm_subsample(universe)
    frozen, frames, events, _ = prepare(universe, subsample=sub)
    run_id = frozen["run_id"]
    s2 = read_json(art_dir(universe) / "study2_lstm.json")
    selected, best, pstar = s2["selected"], s2["best_params"], s2["pstar"]
    seq_len = int(best["seq_len"])
    tstart = lstm_t_start(events, frames, seq_len)
    splits, group, ng = validation.cpcv_splits(events["t0_ts"], events["t1_ts"], t_start_ts=tstart)
    cvb = cv_bounds_ts()
    from .xgb_loop import _PANEL_WORKERS, _panel_pool
    # each (split, seed) refit is independent -> dispatch them all in parallel (byte-identical)
    tasks, task_split = [], []
    for i, sp in enumerate(splits):
        te = sp["test_idx"]
        # per-test-group intervals so non-adjacent CPCV groups keep the intervening train groups
        excl = scaler_exclude_intervals(events, te, tstart, group_of=group,
                                        test_groups=sp["test_groups"])
        stats = pooled_scaler_stats(frames, selected, cvb, excl)
        norm = normalize_frames(frames, selected, stats)
        Xtr = build_X(events.iloc[sp["train_idx"]], norm, selected, seq_len)
        Xte = build_X(events.iloc[te], norm, selected, seq_len)
        ytr = events.iloc[sp["train_idx"]]["y"].to_numpy(int)
        wtr = train_weights(ytr, events.iloc[sp["train_idx"]]["w"].to_numpy(float))
        for sd in LC["seeds"]:
            tasks.append((Xtr, ytr, wtr, Xte, best, int(LC["epochs_full"]), sd, None, 0, False))
            task_split.append(i)
    if _PANEL_WORKERS > 1 and len(tasks) > 1:
        res_all = list(_panel_pool().map(_lstm_train_worker, tasks))
    else:
        res_all = [_lstm_train_worker(t) for t in tasks]
    ns = len(LC["seeds"])
    split_proba, rows = {}, []
    for i, sp in enumerate(splits):
        ps = [p for p, _ in res_all[i * ns:(i + 1) * ns]]
        p = np.mean(ps, axis=0)
        split_proba[i] = p
        f1 = metrics.macro_f1(events.iloc[sp["test_idx"]]["y"].to_numpy(int), decide(p, pstar))
        rows.append({"run_id": run_id, "model": MODEL, "stage": "cpcv", "unit": "split",
                     "unit_id": str(sp["test_groups"]), "score": f1, "extra": None})
    paths = validation.cpcv_paths(splits, ng)
    summaries = []
    for pi_, path in enumerate(paths):
        proba = np.full((len(events), 3), np.nan)
        for g, si in path.items():
            sp = splits[si]
            msk = group[sp["test_idx"]] == g
            proba[sp["test_idx"][msk]] = split_proba[si][msk]
        ok = np.isfinite(proba).all(axis=1)
        yhat = decide(proba[ok], pstar)
        f1 = metrics.macro_f1(events["y"].to_numpy(int)[ok], yhat)
        ret = signed_event_returns(events["ret"].to_numpy(float)[ok], yhat)
        mt = np.isfinite(ret)
        daily = metrics.daily_strategy_returns(events["t1_ts"].to_numpy()[ok][mt], ret[mt])
        sr = metrics.sharpe(daily, CONFIG["TRADING"]["periods_per_year"])
        rows.append({"run_id": run_id, "model": MODEL, "stage": "cpcv", "unit": "path",
                     "unit_id": str(pi_), "score": f1,
                     "extra": json.dumps({"sharpe": sr, "n_trades": int(mt.sum()),
                                          "daily_returns": [round(float(x), 8) for x in daily]})})
        summaries.append({"path": pi_, "macro_f1": f1, "sharpe": sr})
    report.replace_rows(universe, "cv_scores", rows, run_id, MODEL, stage="cpcv")
    print(f"[cpcv/{universe}] paths: {summaries}")
    return summaries


# ---------------- stage: shap (gradientshap if available, else perm — same schema) ----------------

def shap_stage(universe):
    seed_everything()
    sub = lstm_subsample(universe)
    frozen, frames, events, _ = prepare(universe, subsample=sub)
    run_id = frozen["run_id"]
    s2 = read_json(art_dir(universe) / "study2_lstm.json")
    selected, best = s2["selected"], s2["best_params"]
    folds = lstm_folds(events, frames, int(best["seq_len"]))
    res = oof_lstm(events, frames, selected, folds, best, int(LC["epochs_economy"]) + 4,
                   LC["seeds"][:2], keep_models=True)
    try:
        import shap  # noqa: F401
        method = "gradientshap"
    except ImportError:
        method = "perm"  # WO §5 sanctioned fallback (shap needs numba, which caps numpy < 2.5)
    rng = np.random.default_rng(SEED)
    rows = []
    per_ticker = {t: {c: [] for c in selected} for t in events["ticker"].unique()}
    for (fold_models, te, norm) in res["models"]:
        ev_te = events.iloc[te].reset_index(drop=True)
        Xte = build_X(ev_te, norm, selected, int(best["seq_len"]))
        if method == "gradientshap":
            _grad_shap(fold_models, Xte, ev_te, selected, per_ticker, rng)
        else:
            _perm_shap(fold_models, Xte, ev_te, selected, per_ticker, rng)
    for t, vals in sorted(per_ticker.items()):
        mabs = np.array([np.mean(vals[c]) if vals[c] else np.nan for c in selected])
        if not np.isfinite(mabs).all():
            continue
        mabs = np.abs(mabs)
        share = mabs / max(mabs.sum(), 1e-12)
        order = np.argsort(-mabs)
        rank = np.empty(len(selected), int)
        rank[order] = np.arange(1, len(selected) + 1)
        for j, c in enumerate(selected):
            rows.append({"run_id": run_id, "model": MODEL, "method": method, "ticker": t,
                         "feature": c, "mean_abs_shap": float(mabs[j]),
                         "shap_share": float(share[j]), "rank_in_ticker": int(rank[j])})
    report.replace_rows(universe, "feature_importance_shap", rows, run_id, MODEL)
    uni = universality_audit(rows, run_id, MODEL)
    report.replace_rows(universe, "shap_universality", uni, run_id, MODEL)
    print(f"[shap/{universe}] method={method}  {len(rows)} rows")
    return rows


def _grad_shap(fold_models, Xte, ev_te, selected, per_ticker, rng):
    """|SHAP| summed over window steps -> per channel, sampled <=256 sequences per ticker (WO §5)."""
    import shap
    import torch
    cap = int(LC["shap_max_sequences_per_ticker"])
    for t, idx in ev_te.groupby("ticker").groups.items():
        idx = np.asarray(idx)
        if len(idx) > cap:
            idx = rng.choice(idx, size=cap, replace=False)
        bg_idx = rng.choice(len(Xte), size=min(128, len(Xte)), replace=False)
        for m in fold_models:
            ex = shap.GradientExplainer(m, torch.from_numpy(Xte[bg_idx]))
            sv = np.abs(np.asarray(ex.shap_values(torch.from_numpy(Xte[idx]))))
            per_ch = sv.sum(axis=-3 if sv.ndim == 4 else 1).mean(axis=0)  # sum steps, mean samples
            vals = per_ch.mean(axis=-1) if per_ch.ndim == 2 else per_ch   # mean over classes
            for j, c in enumerate(selected):
                per_ticker[t][c].append(float(vals[j]))


def _perm_shap(fold_models, Xte, ev_te, selected, per_ticker, rng, repeats=5):
    """Fallback per WO §5: per-ticker Δ macro-F1 after shuffling one channel."""
    for t, idx in ev_te.groupby("ticker").groups.items():
        idx = np.asarray(idx)
        if len(idx) < 10:
            continue
        Xt = Xte[idx]
        yt = ev_te.iloc[idx]["y"].to_numpy(int)
        base_p = np.mean([predict(m, Xt) for m in fold_models], axis=0)
        base = metrics.macro_f1(yt, decide(base_p))
        for ci, c in enumerate(selected):
            ds = []
            for _ in range(repeats):
                perm = rng.permutation(len(Xt))
                Xp = Xt.copy()
                Xp[:, :, ci] = Xt[perm][:, :, ci]
                p = np.mean([predict(m, Xp) for m in fold_models], axis=0)
                ds.append(base - metrics.macro_f1(yt, decide(p)))
            per_ticker[t][c].append(float(np.mean(ds)))


# ---------------- stage: strategy (sealed deployable artifact, CV-only) ----------------

def strategy_stage(universe):
    """Refit the finalist LSTM ensemble (all seeds, full epochs) on the whole CV panel with the
    frozen full-Train scaler, seal each seed's state_dict base64 + the scaler + p* + a golden-vector
    selfcheck. Trained on CV; holdout untouched."""
    import io

    import torch

    from . import strategy
    seed_everything()
    apply_lstm_parallelism(universe, single=True)  # single heavy fit -> take the whole box (sec.4/8)
    frozen, frames, events_cv, _ = prepare(universe)
    run_id = frozen["run_id"]
    s2 = read_json(art_dir(universe) / "study2_lstm.json")
    selected, best, pstar = s2["selected"], s2["best_params"], s2["pstar"]
    events_cv = eligible_events(events_cv, frames, selected, int(LC["seq_len_max"]))
    seq_len = int(best["seq_len"])
    stats = pooled_scaler_stats(frames, selected, cv_bounds_ts())
    norm = normalize_frames(frames, selected, stats)
    X = build_X(events_cv, norm, selected, seq_len)
    y = events_cv["y"].to_numpy(int)
    w = train_weights(y, events_cv["w"].to_numpy(float))
    blobs, probas = [], []
    for sd in LC["seeds"]:
        m, _ = train_model(X, y, w, None, None, best, int(LC["epochs_full"]), sd)
        buf = io.BytesIO()
        torch.save(m.state_dict(), buf)
        blobs.append(strategy._b64(buf.getvalue()))
        probas.append(predict(m, X[:64]))
    proba = np.mean(probas, axis=0)
    golden = strategy.golden_sample(proba)
    # selfcheck: rebuild the ensemble from the sealed state_dicts and reproduce the golden preds
    reb = []
    for b in blobs:
        mm = make_model(torch, len(selected), best)
        mm.load_state_dict(torch.load(io.BytesIO(strategy._unb64(b))))
        mm.eval()
        reb.append(mm)
    ok = strategy.check_golden(np.mean([predict(mm, X[:64]) for mm in reb], axis=0), golden)
    meta = {"run_id": run_id, "model": MODEL, "trained_on": "cv", "universe": universe,
            "selected": selected, "best_params": best, "pstar": pstar,
            "seq_len": seq_len, "seeds": LC["seeds"], "class_order": [-1, 0, 1],
            "scaler": stats, "n_train_events": int(len(events_cv)),
            "state_dicts_b64": blobs, "golden": golden, "selfcheck_ok": bool(ok)}
    strategy.write(universe, "strategy_lstm.json", meta)
    print(f"[strategy/{universe}] sealed LSTM ({len(selected)} chans, {len(LC['seeds'])} seeds, "
          f"{len(events_cv)} CV events); golden selfcheck {'OK' if ok else 'FAILED'}")
    if not ok:
        raise RuntimeError("LSTM strategy golden selfcheck FAILED")
    return meta


# ---------------- stage: holdout (ONE read) ----------------

def holdout_stage(universe):
    seed_everything()
    frozen = frozen_labels(universe)
    run_id = frozen["run_id"]
    s2 = read_json(art_dir(universe) / "study2_lstm.json")
    selected, best, pstar = s2["selected"], s2["best_params"], s2["pstar"]
    validation.holdout_guard(universe, "lstm", {"run_id": run_id, "selected": selected,
                                                "best_params": best, "pstar": pstar})
    # the finalist trains on ALL tickers (WO §4.7 'pełny trening'), regardless of the economy
    # subsample the loop/HPO stages used
    frozen, frames, events_cv, chans = prepare(universe)
    panel_ho = build_panel(frames, frozen["params"], "holdout")
    events_ho = eligible_events(panel_ho, frames, chans, int(LC["seq_len_max"]))
    seq_len = int(best["seq_len"])
    # frozen full-Train scaler = CV-window bars only (no holdout, no 2016 warmup); the finalist
    # trains at FULL epochs (WO §4.7 'pełny trening'), matching Study 2's finalist OOF.
    stats = pooled_scaler_stats(frames, selected, cv_bounds_ts())
    write_json(art_dir(universe) / "scalers" / "lstm_holdout.json", stats)
    norm = normalize_frames(frames, selected, stats)
    Xtr = build_X(events_cv, norm, selected, seq_len)
    Xte = build_X(events_ho, norm, selected, seq_len)
    ytr = events_cv["y"].to_numpy(int)
    wtr = train_weights(ytr, events_cv["w"].to_numpy(float))
    ps = []
    for sd in LC["seeds"]:
        m, _ = train_model(Xtr, ytr, wtr, None, None, best, int(LC["epochs_full"]), sd)
        ps.append(predict(m, Xte))
    proba = np.mean(ps, axis=0)
    y = events_ho["y"].to_numpy(int)
    yhat = decide(proba, pstar)
    rep = metrics.classification_report(y, yhat, proba)
    seed_f1_std = float(np.std([metrics.macro_f1(y, decide(p, pstar)) for p in ps], ddof=1))
    ret = signed_event_returns(events_ho["ret"].to_numpy(float), yhat)
    mt = np.isfinite(ret)
    daily = metrics.daily_strategy_returns(events_ho["t1_ts"].to_numpy()[mt], ret[mt])
    ppy = CONFIG["TRADING"]["periods_per_year"]
    cp = report.read_table(universe, "cv_scores", MODEL, run_id=run_id)
    path_srs = [json.loads(r["extra"])["sharpe"] / np.sqrt(ppy)
                for _, r in cp[(cp["stage"] == "cpcv") & (cp["unit"] == "path")].iterrows()] \
        if len(cp) else []
    n_trials = int(frozen.get("n_trials", 0)) + int(s2.get("n_trials", 0))
    sr_var = float(np.var(path_srs, ddof=1)) if len(path_srs) > 1 else 1e-4
    dsr = metrics.deflated_sharpe(daily, n_trials, sr_var, ppy)
    ts = report.read_table(universe, "trial_slices", MODEL, run_id=run_id)
    pbo = None
    if len(ts):
        M = ts.pivot(index="trial", columns="slice", values="score").to_numpy()
        pbo = metrics.pbo_cscv(M[np.isfinite(M).all(axis=1)])
    payload = {"run_id": run_id, "model": MODEL, "holdout_report": rep,
               "holdout_seed_f1_std": seed_f1_std,
               "holdout_sharpe": metrics.sharpe(daily, ppy), "dsr": dsr, "pbo": pbo,
               "n_holdout_events": len(events_ho), "n_trades": int(mt.sum()),
               "cv_macro_f1": s2["cv_macro_f1"], "pstar": pstar, "selected": selected,
               "n_trials_total": n_trials}
    report.replace_rows(universe, "verdict", [{"run_id": run_id, "model": MODEL,
                                               "payload": json.dumps(payload)}], run_id, MODEL)
    write_json(art_dir(universe) / "verdict_lstm.json", payload)
    print(f"[holdout/{universe}] macro-F1={rep['macro_f1']:.4f} (seed std {seed_f1_std:.4f})  "
          f"sharpe={payload['holdout_sharpe']:.2f}  PBO={pbo and pbo['pbo']}  "
          f"DSR={dsr and round(dsr['dsr'], 3)}")
    return payload


STAGES = {"loop": loop, "stability": stability, "study2": study2,
          "cpcv": cpcv_stage, "shap": shap_stage, "strategy": strategy_stage,
          "holdout": holdout_stage}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--universe", choices=["demo", "full"], default="demo")
    ap.add_argument("--stage", choices=["all"] + list(STAGES), default="all")
    a = ap.parse_args()
    apply_parallelism(a.universe)
    apply_lstm_parallelism(a.universe, single=(a.stage in ("strategy", "holdout")))
    if a.stage == "all":
        for name in ("loop", "stability", "study2", "cpcv", "shap", "strategy"):
            STAGES[name](a.universe)
        print("NOTE: the holdout stage is never part of 'all' — run it deliberately, once:")
        print(f"  python -m fs.lstm_loop --universe {a.universe} --stage holdout")
    else:
        STAGES[a.stage](a.universe)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""D7-D8: the LSTM classifier, deterministic CPU training, Optuna HPO, Kelly calibration.

Architecture: one LSTM layer over the (SEQ_LEN × n_features) z-scored window, dropout on the
last hidden state, a linear head → logit of Y=1 (Triple-Barrier win). Loss = BCE-with-logits
weighted by pos_weight (class balance) × label-uniqueness weight. Everything is deterministic:
seeds are re-planted before every fold/refit, torch runs 2 CPU threads with deterministic
algorithms, batching order comes from a seeded numpy Generator — a rerun reproduces
best_params and the OOS row exactly.
"""
import math
import random

import numpy as np
import torch
import torch.nn as nn

import pipeline as P

SEED = int(P.CONFIG["RANDOM_SEED"])
TR = P.CONFIG["TRAIN"]
HPO = P.CONFIG["HPO"]


def seed_everything(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(int(TR["torch_threads"]))
    return seed


class LSTMClassifier(nn.Module):
    """LSTM over (B, SEQ_LEN, F) windows -> logit of Y=1. num_layers in {1,2}; inter-layer LSTM
    dropout applies only when num_layers>1 (torch ignores it for a single layer). num_layers=1
    reproduces the original 1-layer architecture exactly."""

    def __init__(self, n_features, hidden, dropout, num_layers=1):
        super().__init__()
        num_layers = int(num_layers)
        self.lstm = nn.LSTM(n_features, hidden, num_layers=num_layers, batch_first=True,
                            dropout=float(dropout) if num_layers > 1 else 0.0)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.lstm(x)
        return self.head(self.drop(out[:, -1, :])).squeeze(-1)


def _pos_weight(y):
    pos = max(1, int(y.sum()))
    neg = max(1, len(y) - pos)
    return torch.tensor(neg / pos, dtype=torch.float32)


def _epoch(model, opt, loss_fn, X, y, w, batch, rng):
    model.train()
    order = rng.permutation(len(X))
    for i in range(0, len(order), batch):
        b = order[i:i + batch]
        opt.zero_grad()
        loss = (loss_fn(model(X[b]), y[b]) * w[b]).mean()
        loss.backward()
        opt.step()


@torch.no_grad()
def predict_proba(model, X):
    model.eval()
    out = []
    for i in range(0, len(X), 1024):
        out.append(torch.sigmoid(model(X[i:i + 1024])))
    return torch.cat(out).numpy() if out else np.empty(0)


def _tensors(Xtr, ytr, wtr):
    return (torch.from_numpy(np.ascontiguousarray(Xtr)),
            torch.from_numpy(np.asarray(ytr, np.float32)),
            torch.from_numpy(np.asarray(wtr, np.float32)))


def train_model(Xtr, ytr, wtr, hidden, lr, dropout, epochs=None, Xva=None, yva=None, seed=SEED,
                weight_decay=0.0, num_layers=1):
    """Deterministic training. With (Xva, yva): early stopping on validation AUC-PR
    (patience/min_delta from config) and the best state is restored — returns
    (model, best_ap, best_epoch). Without: fixed `epochs`, returns (model, None, epochs).
    `seed` plants both the torch init and the batch-shuffle RNG; it defaults to the global
    SEED so every existing caller is byte-identical, and the feature-search evaluator passes
    distinct seeds to average out weight-init luck (a harder overfit gate). `weight_decay`
    (Adam L2) and `num_layers` regularize / size the net; the defaults (0.0, 1) reproduce the
    original unregularized 1-layer model exactly."""
    seed_everything(seed)
    Xt, yt, wt = _tensors(Xtr, ytr, wtr)
    model = LSTMClassifier(Xt.shape[-1], int(hidden), float(dropout), int(num_layers))
    opt = torch.optim.Adam(model.parameters(), lr=float(lr), weight_decay=float(weight_decay))
    loss_fn = nn.BCEWithLogitsLoss(reduction="none", pos_weight=_pos_weight(np.asarray(ytr)))
    rng = np.random.default_rng(seed)
    if Xva is None:
        for _ in range(int(epochs)):
            _epoch(model, opt, loss_fn, Xt, yt, wt, int(TR["batch_size"]), rng)
        return model, None, int(epochs)
    Xv = torch.from_numpy(np.ascontiguousarray(Xva))
    best_ap, best_epoch, best_state, since = -1.0, 0, None, 0
    for ep in range(1, int(TR["max_epochs"]) + 1):
        _epoch(model, opt, loss_fn, Xt, yt, wt, int(TR["batch_size"]), rng)
        ap = P.average_precision(yva, predict_proba(model, Xv))
        if ap > best_ap + float(TR["min_delta"]):
            best_ap, best_epoch, since = ap, ep, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            since += 1
            if since >= int(TR["patience"]):
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    return model, float(best_ap), int(best_epoch)


def hpo(df, events, y, w, folds_data, bounds):
    """D7: seeded Optuna study that selects the LSTM architecture by TRADEABLE OOF LOG-GROWTH,
    not by AUC-PR — so the searched hyper-parameters are chosen for profitability, the fix for
    "Optuna calibrates the wrong objective". Per trial, per fold: train (early stopping on val
    AUC-PR, a smooth stop signal over the whole val set), predict out-of-fold, then score the
    fold by the BEST out-of-fold log-growth over a COARSE (θ, λ) grid via run_engine — the exact
    OOF→engine machinery D8 uses, so model selection and the trading objective are aligned. The
    objective is the mean fold log-growth; the fine (θ, λ, direction) point is chosen at D8. The
    search also spans weight_decay (Adam L2) and num_layers for regularization/capacity — the
    levers that most reduce the Train→OOS gap. Each fold's OOF stays strictly inside
    [min(val t0), max(val t0)+H], pre-OOS by the purge invariant. The winning trial's mean AUC-PR
    is still reported (cv_auc_pr) for continuity. folds_data = [(tr, va, X_fold)] with fold-causal
    normalization. Returns (best_params, mean_best_epochs, best_cv_auc_pr)."""
    import optuna
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    H, E0 = P.CONFIG["H"], P.CONFIG["INITIAL_CAPITAL_USD"]
    thetas = [float(t) for t in HPO["hpo_theta_grid"]]
    lambdas = [float(x) for x in HPO["hpo_lambda_grid"]]
    t0s = [e["t0"] for e in events]
    # ENFORCE (not just assume) the one-way OOS boundary: every CV val fold's log-growth is scored
    # over [min val t0, max val t0 + H], which must stay strictly inside Train — the profit HPO can
    # never see an OOS bar. Mirrors the D8 calibration assert; fails closed if the purge is ever wrong.
    oos0 = bounds["oos_start_idx"]
    assert all(max(t0s[j] for j in va) + H < oos0 for _, va, _ in folds_data if len(va)), \
        "hpo: a CV val fold's label horizon reaches OOS (purge invariant violated)"

    def fold_best_log_growth(scored, lo, hi):
        best = None
        for th in thetas:
            for lam in lambdas:
                g = math.log(max(P.run_engine(df, scored, lo, hi + H, th,
                                              kelly_fraction=lam)[0]["end_capital"], P.EPS) / E0)
                best = g if best is None else max(best, g)
        return best if best is not None else 0.0

    def objective(trial):
        hidden = trial.suggest_categorical("hidden", HPO["hidden_choices"])
        lr = trial.suggest_float("lr", HPO["lr_low"], HPO["lr_high"], log=True)
        dropout = trial.suggest_float("dropout", HPO["dropout_low"], HPO["dropout_high"])
        weight_decay = trial.suggest_float("weight_decay", HPO["weight_decay_low"],
                                           HPO["weight_decay_high"], log=True)
        num_layers = trial.suggest_categorical("num_layers", HPO["num_layers_choices"])
        gs, aps, eps_ = [], [], []
        for step, (tr, va, Xf) in enumerate(folds_data):
            if len(np.unique(y[tr])) < 2 or len(np.unique(y[va])) < 2:
                continue
            model, ap, best_ep = train_model(Xf[tr], y[tr], w[tr], hidden, lr, dropout,
                                             Xva=Xf[va], yva=y[va],
                                             weight_decay=weight_decay, num_layers=num_layers)
            oof = predict_proba(model, torch.from_numpy(np.ascontiguousarray(Xf[va])))
            scored = [(events[j], float(oof[k])) for k, j in enumerate(va)]
            vt0 = [t0s[j] for j in va]
            gs.append(fold_best_log_growth(scored, min(vt0), max(vt0)))
            aps.append(ap)
            eps_.append(max(1, best_ep))
            trial.report(float(np.mean(gs)), step)
            if trial.should_prune():
                raise optuna.TrialPruned()
        if not gs:
            return -1e9
        trial.set_user_attr("best_epochs", eps_)
        trial.set_user_attr("cv_auc_pr", float(np.mean(aps)))
        return float(np.mean(gs))

    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.TPESampler(seed=SEED),
                                pruner=optuna.pruners.MedianPruner(
                                    n_warmup_steps=int(HPO["pruner_warmup_steps"])))
    study.optimize(objective, n_trials=int(HPO["n_trials"]), show_progress_bar=False)
    best = study.best_trial
    epochs = best.user_attrs.get("best_epochs") or [int(TR["max_epochs"]) // 2]
    cv_ap = float(best.user_attrs.get("cv_auc_pr", 0.0))
    return dict(best.params), int(round(float(np.mean(epochs)))), cv_ap


def _dir_filter(scored, mode):
    """long_only acts on the up-signals only (direction == +1); both keeps every signal.
    Restricting which signals we ACT on is a Train-only operating choice — the model was
    trained on both sides and only outputs a win-probability."""
    if mode == "long_only":
        return [(ev, p) for ev, p in scored if ev["direction"] == 1]
    return scored


def calibrate_gate_kelly(df, events, y, w, folds_data, best_params, refit_epochs, bounds):
    """D8: choose the per-asset operating point (entry threshold θ, Kelly fraction λ,
    direction_mode) JOINTLY on Train out-of-fold log-growth. Per fold: train with the best
    params for the fixed refit epoch count (no validation peeking) on the fold's CAUSALLY
    normalized tensor and predict out-of-fold; then replay each fold through run_engine over
    the whole (θ, λ, direction) grid — the OOF predictions are computed once and reused, so
    the grid is nearly free. Full label horizon (end = last val t0 + H, provably pre-OOS by
    the purge invariant). Ties (equal OOF log-growth) resolve to the most conservative point:
    smaller λ, then higher θ, then both-sided. Returns a dict with θ, λ, direction_mode."""
    H = P.CONFIG["H"]
    gc = P.CONFIG["GATE_CALIBRATION"]
    E0 = P.CONFIG["INITIAL_CAPITAL_USD"]
    thetas = [float(t) for t in gc["theta_grid"]]
    lambdas = [float(x) for x in np.geomspace(gc["lambda_low"], gc["lambda_high"], int(gc["lambda_points"]))]
    dir_modes = list(gc["direction_modes"])
    t0s = [e["t0"] for e in events]
    fold_data = []
    for tr, va, Xf in folds_data:
        if len(np.unique(y[tr])) < 2:
            continue
        model, _, _ = train_model(Xf[tr], y[tr], w[tr], best_params["hidden"],
                                  best_params["lr"], best_params["dropout"], epochs=refit_epochs,
                                  weight_decay=best_params.get("weight_decay", 0.0),
                                  num_layers=best_params.get("num_layers", 1))
        oof = predict_proba(model, torch.from_numpy(np.ascontiguousarray(Xf[va])))
        scored = [(events[j], float(oof[k])) for k, j in enumerate(va)]
        vt0 = [t0s[j] for j in va]
        fold_data.append((scored, min(vt0), max(vt0)))
    default = {"theta_entry": max(thetas), "kelly_fraction": float(min(lambdas)),
               "direction_mode": "both", "oof_log_growth": 0.0}
    if not fold_data:
        return default
    assert all(hi + H < bounds["oos_start_idx"] for _, _, hi in fold_data), \
        "gate calibration must not reach OOS (even with the full label horizon)"
    grid = []
    for mode in dir_modes:
        filtered = [(_dir_filter(sc, mode), lo, hi) for sc, lo, hi in fold_data]
        for theta in thetas:
            for lam in lambdas:
                g = sum(math.log(max(P.run_engine(df, sc, lo, hi + H, theta,
                                                  kelly_fraction=lam)[0]["end_capital"], P.EPS) / E0)
                        for sc, lo, hi in filtered)
                grid.append((g, mode, theta, lam))
    gmax = max(g for g, *_ in grid)
    tied = [(mode, theta, lam) for g, mode, theta, lam in grid if g >= gmax - 1e-9]
    # most conservative among ties: smaller λ, then higher θ, then both over long_only
    tied.sort(key=lambda x: (x[2], -x[1], 0 if x[0] == "both" else 1))
    mode, theta, lam = tied[0]
    return {"theta_entry": float(theta), "kelly_fraction": float(lam),
            "direction_mode": mode, "oof_log_growth": float(gmax)}

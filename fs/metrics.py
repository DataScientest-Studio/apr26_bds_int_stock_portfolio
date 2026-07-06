"""Metrics per WO §6: macro-F1 decisive; per-class precision/recall, PR-AUC (OvR macro), MCC and
log-loss as controls; PBO (CSCV, Bailey et al. 2014) and DSR (deflated Sharpe, Bailey & López de
Prado 2014) for the final CPCV/holdout verdict. sklearn is sanctioned by the WO stack line.
"""
import math
from itertools import combinations

import numpy as np
from scipy.stats import norm
from sklearn.metrics import (average_precision_score, f1_score, log_loss,
                             matthews_corrcoef, precision_score, recall_score)

from . import CLASSES

LABELS = list(CLASSES)  # [-1, 0, 1]; model class index = y + 1


def macro_f1(y, yhat):
    return float(f1_score(y, yhat, labels=LABELS, average="macro", zero_division=0))


def classification_report(y, yhat, proba=None):
    """proba: (n, 3) softmax/softprob columns ordered by CLASSES."""
    rep = {
        "macro_f1": macro_f1(y, yhat),
        "mcc": float(matthews_corrcoef(y, yhat)) if len(np.unique(y)) > 1 else 0.0,
        "precision": {str(c): float(p) for c, p in zip(
            LABELS, precision_score(y, yhat, labels=LABELS, average=None, zero_division=0))},
        "recall": {str(c): float(r) for c, r in zip(
            LABELS, recall_score(y, yhat, labels=LABELS, average=None, zero_division=0))},
        "n": int(len(y)),
        "class_frac": {str(c): float(np.mean(np.asarray(y) == c)) for c in LABELS},
    }
    if proba is not None:
        onehot = np.stack([(np.asarray(y) == c).astype(float) for c in LABELS], axis=1)
        rep["pr_auc_macro"] = float(np.mean([
            average_precision_score(onehot[:, k], proba[:, k]) if onehot[:, k].any() else 0.0
            for k in range(len(LABELS))]))
        rep["log_loss"] = float(log_loss(np.asarray(y) + 1, proba, labels=[0, 1, 2]))
    return rep


def fold_log_loss(y, proba):
    return float(log_loss(np.asarray(y) + 1, proba, labels=[0, 1, 2]))


def one_se_choice(sizes, scores, ses):
    """WO stop rule §4.6: among trajectory points, take the SMALLEST feature set whose score is
    within 1 SE of the best score. Returns the chosen trajectory index."""
    scores = np.asarray(scores, float)
    best = int(np.argmax(scores))
    floor = scores[best] - float(ses[best])
    ok = [i for i in range(len(scores)) if scores[i] >= floor]
    return min(ok, key=lambda i: (sizes[i], -scores[i]))


# ---------------- PBO (CSCV) ----------------

def pbo_cscv(M):
    """Probability of Backtest Overfitting via CSCV. M: (n_trials, n_slices) matrix of a
    performance metric (higher = better), n_slices even. For every half/half combination of
    slice columns: pick the best trial in-sample, find its RELATIVE RANK out-of-sample;
    PBO = fraction of combinations where that rank is below the median (logit λ <= 0)."""
    M = np.asarray(M, float)
    n, s = M.shape
    if n < 2 or s < 2 or s % 2 != 0:
        return None
    lambdas = []
    for ins in combinations(range(s), s // 2):
        outs = [j for j in range(s) if j not in ins]
        is_mean = M[:, list(ins)].mean(axis=1)
        oos_mean = M[:, outs].mean(axis=1)
        star = int(np.argmax(is_mean))
        rank = (oos_mean < oos_mean[star]).sum() + 0.5 * (oos_mean == oos_mean[star]).sum()
        omega = rank / n  # relative OOS rank of the IS-best trial, in (0, 1)
        omega = min(max(omega, 1e-9), 1 - 1e-9)
        lambdas.append(math.log(omega / (1 - omega)))
    lambdas = np.asarray(lambdas)
    return {"pbo": float(np.mean(lambdas <= 0)), "n_combinations": int(len(lambdas)),
            "lambda_mean": float(lambdas.mean())}


# ---------------- Sharpe + DSR ----------------

def sharpe(returns, periods_per_year):
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    if len(r) < 2 or r.std(ddof=1) == 0:
        return 0.0
    return float(r.mean() / r.std(ddof=1) * math.sqrt(periods_per_year))


def deflated_sharpe(returns, n_trials, sr_variance, periods_per_year):
    """DSR = Φ(((SR − SR0)·sqrt(T−1)) / sqrt(1 − γ3·SR + (γ4−1)/4·SR²)) with SR0 the expected
    max Sharpe under n_trials independent trials of variance sr_variance (all per-period units).
    Returns the probability that the observed SR beats the multiple-testing noise floor."""
    r = np.asarray(returns, float)
    r = r[np.isfinite(r)]
    T = len(r)
    if T < 10 or r.std(ddof=1) == 0:
        return None
    sr = float(r.mean() / r.std(ddof=1))  # per-period SR
    g3 = float(((r - r.mean()) ** 3).mean() / r.std(ddof=0) ** 3)
    g4 = float(((r - r.mean()) ** 4).mean() / r.std(ddof=0) ** 4)
    em = 0.5772156649015329
    n = max(int(n_trials), 2)
    sr0 = math.sqrt(max(sr_variance, 1e-12)) * (
        (1 - em) * norm.ppf(1 - 1.0 / n) + em * norm.ppf(1 - 1.0 / (n * math.e)))
    denom = 1 - g3 * sr + (g4 - 1) / 4.0 * sr ** 2
    if denom <= 0:
        return None
    z = (sr - sr0) * math.sqrt(T - 1) / math.sqrt(denom)
    return {"dsr": float(norm.cdf(z)), "sr_period": sr,
            "sr_annualized": sr * math.sqrt(periods_per_year),
            "sr0_period": float(sr0), "n_trials": n, "T": T,
            "skew": g3, "kurtosis": g4}


def daily_strategy_returns(exit_ts, signed_ret):
    """Bucket per-event signed log returns by EXIT day -> the daily return series the Sharpe/DSR
    run on (documented simplification: no position netting, unit size per event)."""
    import pandas as pd
    s = pd.Series(np.asarray(signed_ret, float),
                  index=pd.to_datetime(pd.Series(exit_ts), utc=True).dt.date)
    return s.groupby(level=0).sum().to_numpy()

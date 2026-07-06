"""Labels per WO-FS-XGB §2 — one truth for BOTH models.

Event sampling: symmetric CUSUM filter on 1h close log-returns with a volatility-scaled threshold
h_t = cusum_mult · σ_t (σ = EWMA std of returns, span from Study 1). Label: side-free, pure-price
3-class Triple Barrier — first touch of +pt·σ_t0 / −sl·σ_t0 on the CLOSE path within h_bars, else
class 0 at the vertical barrier. No costs, no fills: this is a label, not a trade. Sample weights:
López de Prado average uniqueness (mean 1/concurrency over [t0, t1]), computed AFTER the final
event filter (port of lstm/pipeline.py:293-328).
"""
import numpy as np
import pandas as pd


def ewma_vol(close, span):
    """Per-bar EWMA std of 1-bar log returns (the σ_t used by both the CUSUM threshold and the
    barrier widths). Causal: value at t uses returns up to and including t."""
    c = np.asarray(close, float)
    lr = pd.Series(np.concatenate([[np.nan], np.log(c[1:] / c[:-1])]))
    return lr.ewm(span=int(span), adjust=False, min_periods=int(span)).std().to_numpy()


def cusum_events(close, sigma, cusum_mult):
    """Symmetric CUSUM on log returns: event at bar t when the running positive (negative) sum
    exceeds +h_t (−h_t); both sums reset on any event. Bars with non-finite σ are skipped (warmup).
    Returns an int array of event bar indices t0 (decision at close[t0])."""
    c = np.asarray(close, float)
    lr = np.concatenate([[np.nan], np.log(c[1:] / c[:-1])])
    h = float(cusum_mult) * np.asarray(sigma, float)
    s_pos = 0.0
    s_neg = 0.0
    out = []
    for t in range(1, len(c)):
        r, ht = lr[t], h[t]
        if not (np.isfinite(r) and np.isfinite(ht) and ht > 0):
            continue
        s_pos = max(0.0, s_pos + r)
        s_neg = min(0.0, s_neg + r)
        if s_pos > ht or s_neg < -ht:
            out.append(t)
            s_pos = 0.0
            s_neg = 0.0
    return np.asarray(out, dtype=int)


def triple_barrier(close, t0s, sigma, pt, sl, h_bars):
    """First-touch 3-class labels on the close path. For each event t0: scan j = t0+1 .. t0+h_bars;
    cumulative log return r_j = log(close_j / close_t0); y=+1 if r_j >= +pt·σ_t0 first, y=−1 if
    r_j <= −sl·σ_t0 first, else y=0 at the vertical barrier. Events whose full horizon does not fit
    in the data are dropped (no truncated labels). Returns (t0_kept, y, t1_idx, ret_at_exit)."""
    c = np.asarray(close, float)
    sig = np.asarray(sigma, float)
    H = int(h_bars)
    kept, ys, t1s, rets = [], [], [], []
    logc = np.log(c)
    for t0 in np.asarray(t0s, int):
        s0 = sig[t0]
        if not (np.isfinite(s0) and s0 > 0) or t0 + H >= len(c):
            continue
        up, dn = float(pt) * s0, -float(sl) * s0
        y, t1 = 0, t0 + H
        path = logc[t0 + 1:t0 + H + 1] - logc[t0]
        hit_up = np.nonzero(path >= up)[0]
        hit_dn = np.nonzero(path <= dn)[0]
        i_up = hit_up[0] if len(hit_up) else np.inf
        i_dn = hit_dn[0] if len(hit_dn) else np.inf
        if i_up < i_dn:
            y, t1 = 1, t0 + 1 + int(i_up)
        elif i_dn < i_up:
            y, t1 = -1, t0 + 1 + int(i_dn)
        elif np.isfinite(i_up):  # same bar touches both (rare on close path): ambiguous -> 0
            y, t1 = 0, t0 + 1 + int(i_up)
        kept.append(t0)
        ys.append(y)
        t1s.append(t1)
        rets.append(float(path[t1 - t0 - 1]))
    return (np.asarray(kept, int), np.asarray(ys, int),
            np.asarray(t1s, int), np.asarray(rets, float))


def uniqueness_weights(t0s, t1s):
    """Average-uniqueness sample weights: mean(1/concurrency) over each event's [t0, t1] span
    (López de Prado; port of lstm/pipeline.py _uniqueness_weights)."""
    t0s = np.asarray(t0s, int)
    t1s = np.asarray(t1s, int)
    if len(t0s) == 0:
        return np.empty(0, float)
    lo, hi = int(t0s.min()), int(t1s.max())
    conc = np.zeros(hi - lo + 2)
    for a, b in zip(t0s, t1s):
        conc[a - lo:b - lo + 1] += 1
    return np.asarray([float(np.mean(1.0 / np.maximum(1.0, conc[a - lo:b - lo + 1])))
                       for a, b in zip(t0s, t1s)], float)


def build_events(bars, feats, params, ticker):
    """CUSUM events + 3-class TB labels + the feature row at t0, one ticker. Returns a DataFrame:
    [ticker, t0_idx, t0_ts, t1_idx, t1_ts, y, ret] + feature columns. Uniqueness weights are NOT
    assigned here — call assign_uniqueness on the FINAL event set (after window/eligibility
    filters), so concurrency is measured over exactly the samples the model trains on.
    Feature NaNs are KEPT (XGBoost treats them natively; the LSTM applies its own finiteness rule)."""
    close = bars["close"].to_numpy(float)
    sigma = ewma_vol(close, params["ewma_span"])
    t0s = cusum_events(close, sigma, params["cusum_mult"])
    t0k, y, t1, ret = triple_barrier(close, t0s, sigma, params["pt"], params["sl"], params["h_bars"])
    if len(t0k) == 0:
        return pd.DataFrame()
    ev = pd.DataFrame({"ticker": ticker, "t0_idx": t0k, "t1_idx": t1, "y": y, "ret": ret})
    ev["t0_ts"] = bars["close_ts"].to_numpy()[t0k]
    ev["t1_ts"] = bars["close_ts"].to_numpy()[t1]
    X = feats.iloc[t0k].reset_index(drop=True)
    return pd.concat([ev.reset_index(drop=True), X], axis=1)


def assign_uniqueness(panel):
    """Per-ticker average-uniqueness weights over the FINAL panel (call after every filter)."""
    panel = panel.copy()
    panel["w"] = 1.0
    for _, idx in panel.groupby("ticker").groups.items():
        sub = panel.loc[idx]
        panel.loc[idx, "w"] = uniqueness_weights(sub["t0_idx"].to_numpy(), sub["t1_idx"].to_numpy())
    return panel

"""Feature pool per WO-FS-XGB §1 — ≤4 indicators per timeframe (one per observation category)
plus the cross-TF mean-reversion set. Everything stationary / bounded / signed; raw prices never
leave this module. Indicator kernels adapted from xgb/src/pipeline.py (the audited v2 set).

Columns prefixed "__" are internal helpers consumed by cross_tf() / labels and are dropped from
the public pool. FEATURES_VERSION keys the per-ticker parquet cache — bump on any formula change.
"""
import numpy as np
import pandas as pd

EPS = 1e-9
FEATURES_VERSION = "wofs-features-v1"
SESSION_TIMEZONE = "America/New_York"

POOL_1H = ["rsi_1h", "vol_z_1h", "day_range_pos_1h"]
POOL_1D = ["adx_signed_1d", "rsi_1d", "atr_pct_1d", "dist_pivot_1d"]
POOL_1W = ["ma_slope_1w", "vol_regime_1w", "dist_swing_high_1w", "dist_swing_low_1w"]
POOL_XTF = ["zscore_1h_ma1d", "zscore_1h_ma1w", "rsi_spread_1h_1d",
            "vol_ratio_1h_1d", "alignment_score", "divergence_flag"]
POOL = POOL_1H + POOL_1D + POOL_1W + POOL_XTF

# the WO-LSTM §4.1 mandated cross-TF mean-reversion representative (forced into the LSTM start set)
MR_CHANNEL = "zscore_1h_ma1d"


# ---------------- kernels (adapted from xgb/src/pipeline.py:148-188) ----------------

def wilder_atr(high, low, close, window=14):
    high, low, close = map(np.asarray, (high, low, close))
    prev = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev), np.abs(low - prev)])
    atr = np.full(len(tr), np.nan)
    if len(tr) >= window:
        atr[window - 1] = tr[:window].mean()
        for i in range(window, len(tr)):
            atr[i] = (atr[i - 1] * (window - 1) + tr[i]) / window
    return atr


def rsi(close, window=14):
    delta = pd.Series(np.asarray(close, float)).diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    out = 100.0 - 100.0 / (1.0 + rs)
    out = out.mask((avg_loss == 0.0) & (avg_gain > 0.0), 100.0)
    out = out.mask((avg_loss == 0.0) & (avg_gain == 0.0), 50.0)
    return out.to_numpy() / 100.0  # 0..1 per the WO encoding


def safe_div(num, den, default=np.nan):
    num = np.asarray(num, float)
    den = np.asarray(den, float)
    out = np.full(len(num), default, float)
    m = np.isfinite(num) & np.isfinite(den) & (np.abs(den) > EPS)
    out[m] = num[m] / den[m]
    return out


def zscore(x, window):
    s = pd.Series(np.asarray(x, float))
    mu = s.rolling(window).mean()
    sd = s.rolling(window).std(ddof=0)
    z = (s - mu) / sd.where(sd > EPS)
    return z.clip(-5, 5).to_numpy()


def adx_signed(high, low, close, window=14):
    """Wilder ADX scaled to 0..1, signed by the dominant directional index (+DI vs −DI):
    one bounded 'trend strength with sign' feature (WO 1d Trend category)."""
    high, low, close = map(lambda a: np.asarray(a, float), (high, low, close))
    up = np.concatenate([[0.0], np.diff(high)])
    dn = np.concatenate([[0.0], -np.diff(low)])
    plus_dm = np.where((up > dn) & (up > 0), up, 0.0)
    minus_dm = np.where((dn > up) & (dn > 0), dn, 0.0)
    prev = np.concatenate([[close[0]], close[:-1]])
    tr = np.maximum.reduce([high - low, np.abs(high - prev), np.abs(low - prev)])
    alpha = 1.0 / window
    def _wilder(x):
        return pd.Series(x).ewm(alpha=alpha, adjust=False, min_periods=window).mean().to_numpy()
    atr_s = _wilder(tr)
    pdi = 100.0 * safe_div(_wilder(plus_dm), atr_s)
    mdi = 100.0 * safe_div(_wilder(minus_dm), atr_s)
    dx = 100.0 * safe_div(np.abs(pdi - mdi), pdi + mdi)
    adx = _wilder(dx)
    return np.sign(pdi - mdi) * adx / 100.0


def _logret(close):
    c = np.asarray(close, float)
    return np.concatenate([[np.nan], np.log(c[1:] / c[:-1])])


# ---------------- per-timeframe frames ----------------

def features_1h(bars):
    """bars: 1h frame [timestamp(open, UTC tz-aware), open..volume]. All values causal at bar close."""
    c, h, l = (bars[k].to_numpy(float) for k in ("close", "high", "low"))
    out = pd.DataFrame(index=bars.index)
    out["rsi_1h"] = rsi(c, 14)
    rv = pd.Series(_logret(c)).rolling(20).std(ddof=0).to_numpy()
    out["vol_z_1h"] = zscore(rv, 100)
    # position of the close inside the session's RUNNING range (causal within the day), 0..1
    et_date = bars["timestamp"].dt.tz_convert(SESSION_TIMEZONE).dt.date
    g_hi = pd.Series(h).groupby(np.asarray(et_date)).cummax().to_numpy()
    g_lo = pd.Series(l).groupby(np.asarray(et_date)).cummin().to_numpy()
    rng = g_hi - g_lo
    out["day_range_pos_1h"] = np.where(rng > EPS, (c - g_lo) / np.where(rng > EPS, rng, 1.0), 0.5)
    # helpers for cross-TF / labels
    out["__rv20_1h"] = rv
    out["__sma20_1h"] = pd.Series(c).rolling(20).mean().to_numpy()
    out["__atr14_1h_abs"] = wilder_atr(h, l, c, 14)
    return out


def features_1d(bars_1d):
    """bars_1d: native daily frame [open..volume] (one row per session)."""
    c, h, l = (bars_1d[k].to_numpy(float) for k in ("close", "high", "low"))
    atr = wilder_atr(h, l, c, 14)
    out = pd.DataFrame(index=bars_1d.index)
    out["adx_signed_1d"] = adx_signed(h, l, c, 14)
    out["rsi_1d"] = rsi(c, 14)
    out["atr_pct_1d"] = safe_div(atr, c)
    # distance of the close to the previous session's pivot (H+L+C)/3, in ATR units
    pivot_prev = pd.Series((h + l + c) / 3.0).shift(1).to_numpy()
    out["dist_pivot_1d"] = np.clip(safe_div(c - pivot_prev, atr), -5, 5)
    out["__ma20_1d"] = pd.Series(c).rolling(20).mean().to_numpy()
    out["__atr14_1d_abs"] = atr
    out["__rv20_1d"] = pd.Series(_logret(c)).rolling(20).std(ddof=0).to_numpy()
    return out


def features_1w(bars_1w):
    """bars_1w: weekly frame aggregated from NATIVE daily bars (ISO week)."""
    c, h, l = (bars_1w[k].to_numpy(float) for k in ("close", "high", "low"))
    atr = wilder_atr(h, l, c, 10)
    lr = _logret(c)
    rv8 = pd.Series(lr).rolling(8).std(ddof=0).to_numpy()
    out = pd.DataFrame(index=bars_1w.index)
    # Trend: sign+strength of the 10w SMA slope, normalized by weekly vol
    sma10 = pd.Series(c).rolling(10).mean()
    slope = (sma10 / sma10.shift(1) - 1.0).to_numpy()
    out["ma_slope_1w"] = np.clip(safe_div(slope, rv8), -3, 3)
    # Volatility regime: expansion(+1) / contraction(−1) / neutral(0) with a 10% deadband
    rv4 = pd.Series(lr).rolling(4).std(ddof=0).to_numpy()
    rv12 = pd.Series(lr).rolling(12).std(ddof=0).to_numpy()
    ratio = safe_div(rv4, rv12)
    out["vol_regime_1w"] = np.where(~np.isfinite(ratio), np.nan,
                                    np.where(ratio > 1.1, 1.0, np.where(ratio < 0.9, -1.0, 0.0)))
    # Structure: distance to the 12w swing high / low, in weekly ATR units
    hi12 = pd.Series(h).rolling(12).max().to_numpy()
    lo12 = pd.Series(l).rolling(12).min().to_numpy()
    out["dist_swing_high_1w"] = np.clip(safe_div(c - hi12, atr), -5, 5)
    out["dist_swing_low_1w"] = np.clip(safe_div(c - lo12, atr), -5, 5)
    out["__ma10_1w"] = sma10.to_numpy()
    out["__atr10_1w_abs"] = atr
    return out


# ---------------- cross-TF (computed on the joined per-1h-bar frame) ----------------

def _trend_sign(dist, atr_abs, deadband=0.1):
    s = np.where(dist > deadband * atr_abs, 1.0, np.where(dist < -deadband * atr_abs, -1.0, 0.0))
    return np.where(np.isfinite(dist) & np.isfinite(atr_abs), s, np.nan)


def cross_tf(frame, close_1h):
    """frame: per-1h-bar frame that already carries the (lagged, causal) 1d/1w feature columns
    and helpers. Adds the 6 cross-TF mean-reversion features of WO §1."""
    c = np.asarray(close_1h, float)
    out = pd.DataFrame(index=frame.index)
    out["zscore_1h_ma1d"] = np.clip(safe_div(c - frame["__ma20_1d"], frame["__atr14_1d_abs"]), -5, 5)
    out["zscore_1h_ma1w"] = np.clip(safe_div(c - frame["__ma10_1w"], frame["__atr10_1w_abs"]), -5, 5)
    out["rsi_spread_1h_1d"] = frame["rsi_1h"] - frame["rsi_1d"]
    # realized-vol ratio 1h vs 1d on comparable (annualized) scales: log for symmetry
    ann_1h = frame["__rv20_1h"] * np.sqrt(6.5 * 252.0)
    ann_1d = frame["__rv20_1d"] * np.sqrt(252.0)
    ratio = safe_div(ann_1h, ann_1d)
    ratio = np.where(np.isfinite(ratio) & (ratio > EPS), ratio, np.nan)
    out["vol_ratio_1h_1d"] = np.clip(np.log(ratio), -2, 2)
    s1h = _trend_sign(c - frame["__sma20_1h"].to_numpy(), frame["__atr14_1h_abs"].to_numpy())
    s1d = _trend_sign(c - frame["__ma20_1d"].to_numpy(), frame["__atr14_1d_abs"].to_numpy())
    s1w = _trend_sign(c - frame["__ma10_1w"].to_numpy(), frame["__atr10_1w_abs"].to_numpy())
    out["alignment_score"] = np.abs(s1h + s1d + s1w) / 3.0  # ∈ {0, ⅓, ⅔, 1}
    # momentum divergence between levels: RSI(1h) and RSI(1d) on opposite sides of 0.5
    r1h, r1d = frame["rsi_1h"].to_numpy(float), frame["rsi_1d"].to_numpy(float)
    div = (np.sign(r1h - 0.5) * np.sign(r1d - 0.5) < 0).astype(float)
    out["divergence_flag"] = np.where(np.isfinite(r1h) & np.isfinite(r1d), div, np.nan)
    return out

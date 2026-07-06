"""Data contract (WO-FS-XGB §1): 1h bars from the xgb store, NATIVE 1d bars from the lstm store
(no 1h→1d resampling), 1w aggregated from native 1d (ISO week — the only native-derived path
available). 1d/1w context reaches a 1h decision only via merge_asof(backward,
allow_exact_matches=False) on `available_at`, i.e. last CLOSED higher-TF bar with the explicit
one-TF-bar lag the WO mandates.

Conventions inherited from the audited v2 pipelines:
- store `timestamp` = interval OPEN (UTC); the decision clock of bar t is its CLOSE = open + 1h;
- `available_at` of a 1d bar = close of the last 1h bar of that session (so early closes are
  handled by the data itself, never by a calendar); a 1w bar inherits its last session's.
"""
import hashlib
import os

import numpy as np
import pandas as pd

from . import CONFIG, REPO, ART, FS_ROOT
from . import features as F
from . import dsl

BAR = pd.Timedelta(hours=1)
PROPOSED_PATH = FS_ROOT / "features_proposed.json"  # Sonnet-proposed causal features (validated)


def feature_pool():
    """The full candidate pool the selection loops start from = fixed WO §1 pool + every VALIDATED
    Sonnet-proposed feature (the registry only ever holds validated ones)."""
    return list(F.POOL) + dsl.proposed_names(PROPOSED_PATH)


def bars_1h_db(universe):
    env = os.environ.get("FS_BARS_1H")
    if env:
        return env
    p = REPO / CONFIG["STORES"]["bars_1h_full" if universe == "full" else "bars_1h_demo"]
    if universe == "full" and not p.exists():
        raise RuntimeError(f"full 1h store missing: {p} (local-only, see xgb/ make build-db)")
    return str(p)


def bars_1d_db():
    return str(REPO / CONFIG["STORES"]["bars_1d"])


def tickers(universe):
    import duckdb
    con = duckdb.connect(bars_1h_db(universe), read_only=True)
    t1h = {r[0] for r in con.execute("select distinct ticker from bars_1h").fetchall()}
    con.close()
    con = duckdb.connect(bars_1d_db(), read_only=True)
    t1d = {r[0] for r in con.execute("select distinct symbol from bars_1d").fetchall()}
    con.close()
    return sorted(t1h & t1d)


def load_1h(ticker, universe):
    """QC gate adapted from xgb/src/pipeline.py layer4_snapshot_to_parquet — fail-closed."""
    import duckdb
    con = duckdb.connect(bars_1h_db(universe), read_only=True)
    df = con.execute("select timestamp, open, high, low, close, volume from bars_1h "
                     "where ticker=? order by timestamp", [ticker]).fetchdf()
    con.close()
    if df.empty:
        raise RuntimeError(f"no 1h rows for {ticker}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = df.astype({c: float for c in ("open", "high", "low", "close", "volume")}).reset_index(drop=True)
    _qc(df, ticker, "1h")
    df["close_ts"] = df["timestamp"] + BAR
    return df


def load_1d(ticker):
    import duckdb
    con = duckdb.connect(bars_1d_db(), read_only=True)
    df = con.execute("select date, open, high, low, close, volume from bars_1d "
                     "where symbol=? order by date", [ticker]).fetchdf()
    con.close()
    if df.empty:
        raise RuntimeError(f"no 1d rows for {ticker}")
    df = df.astype({c: float for c in ("open", "high", "low", "close", "volume")}).reset_index(drop=True)
    _qc(df, ticker, "1d")
    return df


def _qc(df, ticker, tf):
    errs = []
    key = "timestamp" if "timestamp" in df else "date"
    if df[key].duplicated().any():
        errs.append("duplicate timestamps")
    if not df[key].is_monotonic_increasing:
        errs.append("timestamps not increasing")
    ohlc = df[["open", "high", "low", "close"]].to_numpy(float)
    if not np.isfinite(ohlc).all() or (ohlc <= 0).any():
        errs.append("non-finite or <=0 OHLC")
    h, l, o, c = (df[k].to_numpy(float) for k in ("high", "low", "open", "close"))
    if (h < l).any() or (h < np.maximum(o, c)).any() or (l > np.minimum(o, c)).any():
        errs.append("inconsistent OHLC bounds")
    if (df["volume"].to_numpy(float) < 0).any():
        errs.append("negative volume")
    if errs:
        raise RuntimeError(f"source QC FAILED {ticker} {tf}: " + "; ".join(errs))


def weekly_from_daily(df_1d):
    """ISO-week aggregation of NATIVE daily bars (open=first, high=max, low=min, close=last,
    volume=sum). `last_date` carries the session whose close makes the weekly bar available."""
    d = df_1d.copy()
    iso = pd.to_datetime(d["date"]).map(lambda x: "%d-%02d" % x.isocalendar()[:2])
    rows = []
    for _, g in d.groupby(np.asarray(iso), sort=True):
        rows.append({"date": g["date"].iloc[0], "last_date": g["date"].iloc[-1],
                     "open": float(g["open"].iloc[0]), "high": float(g["high"].max()),
                     "low": float(g["low"].min()), "close": float(g["close"].iloc[-1]),
                     "volume": float(g["volume"].sum())})
    return pd.DataFrame(rows)


def session_close_map(df_1h):
    """ET session date -> close_ts of the session's last 1h bar (= when the native 1d bar of that
    session is known). Derived from actual bars, so early closes are exact."""
    et_date = df_1h["timestamp"].dt.tz_convert(F.SESSION_TIMEZONE).dt.date
    return df_1h.groupby(np.asarray(et_date))["close_ts"].max()


def tf_hierarchy_check(n_1h, n_1d, n_1w):
    """WO §1: both adjacent TF ratios must be >= 3x."""
    r_dh, r_wd = n_1h / max(n_1d, 1), n_1d / max(n_1w, 1)
    if r_dh < 3 or r_wd < 3:
        raise RuntimeError(f"TF hierarchy violated: 1h/1d={r_dh:.1f}x 1d/1w={r_wd:.1f}x (both must be >=3)")
    return {"ratio_1h_1d": round(r_dh, 2), "ratio_1d_1w": round(r_wd, 2)}


def _join_context(decision_ts, df_ctx, cols):
    """merge_asof backward WITHOUT exact matches — the WO's explicit one-TF-bar lag: a bar whose
    available_at equals the decision instant is treated as not yet closed."""
    left = pd.DataFrame({"decision_ts": decision_ts})
    right = df_ctx[["available_at"] + cols].sort_values("available_at")
    out = pd.merge_asof(left, right, left_on="decision_ts", right_on="available_at",
                        direction="backward", allow_exact_matches=False)
    return out[cols].reset_index(drop=True)


def bar_frame(ticker, universe, use_cache=True, include_proposed=True):
    """The per-1h-bar frame both models consume: (bars, feats) row-aligned. feats = fixed WO §1 pool
    (fs.features.POOL) + every validated Sonnet-proposed feature, all causal at the bar's close.
    The base pool and each proposed feature are cached separately, so seeding a new proposal only
    computes that one column across tickers (no full-frame rebuild)."""
    cache = ART / "cache" / universe / f"{ticker}.parquet"
    if use_cache and cache.exists() and _cache_version(cache) == F.FEATURES_VERSION:
        cached = pd.read_parquet(cache)
        bars = cached[["timestamp", "open", "high", "low", "close", "volume", "close_ts"]].copy()
        feats = cached[F.POOL].copy()
        if include_proposed:
            feats = _with_proposed(ticker, universe, bars, feats, use_cache)
        return bars, feats
    bars = load_1h(ticker, universe)
    d1 = load_1d(ticker)
    w1 = weekly_from_daily(d1)
    tf_hierarchy_check(len(bars), len(d1), len(w1))

    f1h = F.features_1h(bars)
    f1d = F.features_1d(d1)
    f1w = F.features_1w(w1)

    scm = session_close_map(bars)  # ET date -> close_ts
    d_avail = pd.Series(pd.to_datetime(d1["date"]).dt.date).map(scm)
    f1d = f1d.assign(available_at=d_avail.to_numpy())
    f1d = f1d[pd.notna(f1d["available_at"])].reset_index(drop=True)
    w_avail = pd.Series(pd.to_datetime(w1["last_date"]).dt.date).map(scm)
    f1w = f1w.assign(available_at=w_avail.to_numpy())
    f1w = f1w[pd.notna(f1w["available_at"])].reset_index(drop=True)

    ctx_1d = _join_context(bars["close_ts"], f1d, [c for c in f1d.columns if c != "available_at"])
    ctx_1w = _join_context(bars["close_ts"], f1w, [c for c in f1w.columns if c != "available_at"])
    frame = pd.concat([f1h.reset_index(drop=True), ctx_1d, ctx_1w], axis=1)
    xtf = F.cross_tf(frame, bars["close"].to_numpy(float))
    feats = pd.concat([frame, xtf], axis=1)[F.POOL].astype(float)

    if use_cache:
        cache.parent.mkdir(parents=True, exist_ok=True)
        snap = pd.concat([bars.reset_index(drop=True), feats.reset_index(drop=True)], axis=1)
        _atomic_parquet(snap, cache)
        _write_cache_version(cache, F.FEATURES_VERSION)
    if include_proposed:
        feats = _with_proposed(ticker, universe, bars, feats, use_cache)
    return bars, feats


def _atomic_parquet(df, path):
    """Write parquet atomically with a PROCESS-UNIQUE temp name, so concurrent warm workers / the
    live proposer computing the same ticker never collide on a shared .tmp path."""
    tmp = path.with_suffix(f".{os.getpid()}.parquet.tmp")
    df.to_parquet(tmp, index=False)
    os.replace(tmp, path)


def _with_proposed(ticker, universe, bars, feats, use_cache):
    """Append every validated proposed feature (per-feature parquet cache keyed by expr hash)."""
    reg = dsl.proposed_registry(PROPOSED_PATH)
    names = [k for k in reg if not k.startswith("_")]
    if not names:
        return feats
    cols = {}
    for nm in names:
        expr = reg[nm]["expr"]
        ver = hashlib.sha256(expr.encode()).hexdigest()[:12]
        p = ART / "pcache" / universe / nm / f"{ticker}.parquet"
        if use_cache and p.exists() and _cache_version(p) == ver:
            cols[nm] = pd.read_parquet(p)[nm].to_numpy()
            continue
        try:
            vals = dsl.dsl_eval(expr, bars)
        except Exception:  # noqa: BLE001 — one bad ticker becomes all-NaN, never crashes the run
            vals = np.full(len(bars), np.nan)
        cols[nm] = vals
        if use_cache:
            p.parent.mkdir(parents=True, exist_ok=True)
            _atomic_parquet(pd.DataFrame({nm: vals}), p)
            _write_cache_version(p, ver)
    return pd.concat([feats.reset_index(drop=True),
                      pd.DataFrame(cols).reset_index(drop=True)], axis=1)


def _cache_version(cache):
    v = cache.with_suffix(".version")
    return v.read_text().strip() if v.exists() else None


def _write_cache_version(cache, version):
    cache.with_suffix(".version").write_text(version + "\n")


def universe_hash(names):
    return hashlib.sha256("|".join(names).encode()).hexdigest()[:12]

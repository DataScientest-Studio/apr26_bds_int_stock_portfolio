#!/usr/bin/env python3
"""Runtime implementation of the minimal per-asset pipeline.

Eligible 1h bars get their side from 1h momentum, X is built from simple
timeframe-namespaced features, and Y is a symmetric ATR Triple Barrier.
"""
import base64
import hashlib
import json
import math
import os
import random
from pathlib import Path

import numpy as np
import pandas as pd


def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


ROOT = Path(__file__).resolve().parent
PIPELINE_PARAMETERS = _load_json(ROOT / "config" / "pipeline_parameters.json")
FEATURE_NAMESPACES_PATH = ROOT / "config" / "feature_namespaces.json"
FEATURE_NAMESPACES = _load_json(FEATURE_NAMESPACES_PATH)
XGBOOST_OPTUNA_SEARCH_SPACE_PATH = ROOT / "config" / "xgboost_optuna_search_space.json"
XGBOOST_OPTUNA_SEARCH_SPACE = _load_json(XGBOOST_OPTUNA_SEARCH_SPACE_PATH)

OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]
SESSION_TIMEZONE = "America/New_York"
CONTEXT_TIMEFRAMES = ("1d", "1w")
_BAR_DURATION = pd.Timedelta(hours=1)
EPS = float(PIPELINE_PARAMETERS.get("EPS", 1e-9))
CV_FOLDS = int(XGBOOST_OPTUNA_SEARCH_SPACE["objective"]["cv_folds"])
MEDIAN_PRUNER_WARMUP = int(XGBOOST_OPTUNA_SEARCH_SPACE["objective"]["pruner_warmup"])


# ============================ time helpers ============================

def bar_open_timestamp(df, t):
    return pd.Timestamp(df["timestamp"].iloc[t])


def bar_close_timestamp_from_open(open_ts):
    return pd.Timestamp(open_ts) + _BAR_DURATION


def bar_close_timestamp(df, t):
    return bar_close_timestamp_from_open(bar_open_timestamp(df, t))


def decision_timestamp_of_event(df, t0):
    return bar_close_timestamp(df, t0)


# ============================ determinism + validation ============================

def seed_everything(seed=None):
    seed = PIPELINE_PARAMETERS["RANDOM_SEED"] if seed is None else seed
    random.seed(seed)
    np.random.seed(seed)
    return seed


def n_trials():
    return int(PIPELINE_PARAMETERS["N_TRIALS"])


def embargo_candles():
    return int(PIPELINE_PARAMETERS["EMBARGO_BARS"])


def validate_parameters(p=PIPELINE_PARAMETERS):
    errs = []
    enums = {"BARRIER_MODE": {"close"},
             "CAPITAL_MODE": {"all_in_compounding_per_asset", "kelly_fractional_compounding"},
             "ENTRY_FILL": {"next_bar_open"}, "EXIT_FILL": {"trigger_next_open"},
             "SCHEDULED_EXIT_FILL": {"scheduled_moc_close"},
             "POSITION_POLICY": {"one_open_position_per_asset"},
             "CORP_ACTIONS_POLICY": {"deferred", "A_adjusted", "B_raw_exclude"},
             "UNIVERSE_MODE": {"current_constituents_research", "point_in_time_constituents"},
             "OPTUNA_OBJECTIVE": {"auc_pr"}, "CV_SCHEME": {"purged_walk_forward"},
             "PF_ZERO_GROSS_LOSS_POLICY": {"not_rankable"},
             "SIGNAL_ZERO_POLICY": {"skip"}}
    for k, allowed in enums.items():
        if p.get(k) not in allowed:
            errs.append(f"{k}={p.get(k)!r} not in {sorted(allowed)}")
    if not (0 < p["THRESHOLD_ENTRY"] < 1):
        errs.append("THRESHOLD_ENTRY must be in (0,1)")
    for k in ("H", "N_TRIALS", "EMBARGO_BARS", "PURGE_CANDLES", "W_ATR", "W_VOL",
              "W_RSI", "W_BB", "W_SMA_FAST", "W_SMA_SLOW", "MACD_FAST", "MACD_SLOW", "MACD_SIGNAL"):
        if not (isinstance(p[k], int) and p[k] > 0):
            errs.append(f"{k} must be a positive int")
    if p["MACD_FAST"] >= p["MACD_SLOW"]:
        errs.append("MACD_FAST must be < MACD_SLOW")
    for k in ("COMMISSION_BPS", "SLIPPAGE_BPS", "SIMULTANEOUS_SETUP_TIE_EPS", "TB_ATR_MULTIPLIER", "BB_K"):
        if not (isinstance(p[k], (int, float)) and p[k] >= 0):
            errs.append(f"{k} must be >= 0")
    if p["TB_ATR_MULTIPLIER"] <= 0:
        errs.append("TB_ATR_MULTIPLIER must be > 0")
    if not (p["INITIAL_CAPITAL_USD"] > 0):
        errs.append("INITIAL_CAPITAL_USD must be > 0")
    if not (isinstance(p.get("KELLY_CAP"), (int, float)) and 0 < p["KELLY_CAP"] <= 1):
        errs.append("KELLY_CAP must be a number in (0, 1]")
    kc = p.get("KELLY_CALIBRATION", {})
    if not (isinstance(kc, dict) and 0 < kc.get("low", -1) <= kc.get("high", -1) <= 1
            and isinstance(kc.get("grid_points"), int) and kc["grid_points"] >= 2):
        errs.append("KELLY_CALIBRATION must be {0<low<=high<=1, grid_points int>=2}")
    for k in ("MIN_TRAIN_ACCEPTANCE_TRADES", "MIN_OOS_TRADES_FOR_INTERPRETATION"):
        if not (p[k] is None or (isinstance(p[k], int) and p[k] >= 1)):
            errs.append(f"{k} must be null or an integer >= 1")
    if p["PURGE_CANDLES"] != p["H"]:
        errs.append("PURGE_CANDLES must equal H")
    if p["ALLOW_PYRAMIDING"] or p["ALLOW_REVERSAL_WHILE_OPEN"]:
        errs.append("ALLOW_PYRAMIDING / ALLOW_REVERSAL_WHILE_OPEN must be false")
    if errs:
        raise RuntimeError("parameter schema validation failed: " + "; ".join(errs))
    return True


# ============================ indicators ============================

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


def rolling_mean_std(x, window):
    s = pd.Series(x)
    return s.rolling(window).mean().to_numpy(), s.rolling(window).std(ddof=0).to_numpy()


def _ema(values, span):
    return pd.Series(values).ewm(span=span, adjust=False, min_periods=span).mean().to_numpy()


def _rsi(close, window):
    delta = pd.Series(close).diff()
    gain = delta.clip(lower=0.0)
    loss = -delta.clip(upper=0.0)
    avg_gain = gain.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    avg_loss = loss.ewm(alpha=1.0 / window, adjust=False, min_periods=window).mean()
    rs = avg_gain / avg_loss.replace(0.0, np.nan)
    rsi = 100.0 - 100.0 / (1.0 + rs)
    rsi = rsi.mask((avg_loss == 0.0) & (avg_gain > 0.0), 100.0)
    rsi = rsi.mask((avg_loss == 0.0) & (avg_gain == 0.0), 50.0)
    return rsi.to_numpy()


def _safe_div(num, den, default=np.nan):
    num = np.asarray(num, dtype=float)
    den = np.asarray(den, dtype=float)
    out = np.full(len(num), default, dtype=float)
    mask = np.isfinite(num) & np.isfinite(den) & (np.abs(den) > EPS)
    out[mask] = num[mask] / den[mask]
    return out


# ============================ L4 — snapshot + timeframes ============================

def atomic_write(path, writer):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    writer(tmp)
    os.replace(tmp, path)


def layer4_snapshot_to_parquet(db_path, ticker, out_path):
    import duckdb
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute("select timestamp, open, high, low, close, volume from bars_1h where ticker=? order by timestamp",
                     [ticker]).fetchdf()
    con.close()
    if df.empty:
        raise RuntimeError(f"L4 no rows for {ticker}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    df = (df[OHLCV_COLUMNS]
          .astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
          .reset_index(drop=True))
    errs = []
    if int(df["timestamp"].isna().sum()):
        errs.append("unparseable timestamp(s)")
    if int(df["timestamp"].duplicated().sum()):
        errs.append("duplicate timestamp(s)")
    if not df["timestamp"].is_monotonic_increasing:
        errs.append("timestamps are not strictly increasing")
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ohlc = df[["open", "high", "low", "close"]].to_numpy()
    if not np.isfinite(ohlc).all() or (ohlc <= 0).any():
        errs.append("non-finite or <= 0 OHLC value(s)")
    if (h < l).any():
        errs.append("bar(s) with high < low")
    if (h < np.maximum(o, c)).any():
        errs.append("bar(s) with high < max(open, close)")
    if (l > np.minimum(o, c)).any():
        errs.append("bar(s) with low > min(open, close)")
    vol = df["volume"].to_numpy(float)
    if not np.isfinite(vol).all() or (vol < 0).any():
        errs.append("non-finite or negative volume")
    if errs:
        raise RuntimeError(f"L4 source QC FAILED for {ticker}: " + "; ".join(errs))
    atomic_write(out_path, lambda p: df.to_parquet(p, engine="pyarrow", compression="zstd", index=False))
    return df


def _utc_series(ts):
    ts = pd.to_datetime(ts)
    return ts.dt.tz_localize("UTC") if ts.dt.tz is None else ts.dt.tz_convert("UTC")


def aggregate_to_timeframe(df_1h, timeframe_id):
    if timeframe_id not in CONTEXT_TIMEFRAMES:
        raise ValueError(f"unsupported timeframe_id {timeframe_id!r}")
    cols = OHLCV_COLUMNS + ["close_ts", "available_at"]
    utc = _utc_series(df_1h["timestamp"]).reset_index(drop=True)
    et = utc.dt.tz_convert(SESSION_TIMEZONE)
    base = df_1h[["open", "high", "low", "close", "volume"]].reset_index(drop=True).astype(float)
    base["timestamp"] = utc.to_numpy()
    base["_date"] = [d.isoformat() for d in et.dt.date]
    daily = []
    for _, g in base.groupby("_date", sort=True):
        g = g.sort_values("timestamp")
        close_ts = bar_close_timestamp_from_open(g["timestamp"].iloc[-1])
        daily.append({"timestamp": g["timestamp"].iloc[0], "open": float(g["open"].iloc[0]),
                      "high": float(g["high"].max()), "low": float(g["low"].min()),
                      "close": float(g["close"].iloc[-1]), "volume": float(g["volume"].sum()),
                      "close_ts": close_ts, "available_at": close_ts, "_date": g["_date"].iloc[0]})
    df_1d = pd.DataFrame(daily)
    if timeframe_id == "1d":
        out = df_1d[cols].reset_index(drop=True) if len(df_1d) else pd.DataFrame(columns=cols)
        return out, {"n_sessions": len(df_1d)}
    if not len(df_1d):
        return pd.DataFrame(columns=cols), {"n_sessions": 0, "n_weeks": 0}
    df_1d = df_1d.copy()
    df_1d["_wk"] = df_1d["_date"].map(lambda d: "%d-%02d" % pd.Timestamp(d).isocalendar()[:2])
    weekly = []
    for _, wg in df_1d.groupby("_wk", sort=True):
        wg = wg.sort_values("timestamp")
        weekly.append({"timestamp": wg["timestamp"].iloc[0], "open": float(wg["open"].iloc[0]),
                       "high": float(wg["high"].max()), "low": float(wg["low"].min()),
                       "close": float(wg["close"].iloc[-1]), "volume": float(wg["volume"].sum()),
                       "close_ts": wg["close_ts"].iloc[-1], "available_at": wg["available_at"].iloc[-1]})
    df_1w = pd.DataFrame(weekly)
    out = df_1w[cols].reset_index(drop=True) if len(df_1w) else pd.DataFrame(columns=cols)
    return out, {"n_sessions": len(df_1d), "n_weeks": len(df_1w)}


def layer4_materialize_timeframes(df_1h, out_paths):
    out = {"audit": {}}
    for tf in CONTEXT_TIMEFRAMES:
        df_tf, audit = aggregate_to_timeframe(df_1h, tf)
        pure = df_tf[OHLCV_COLUMNS].copy()
        atomic_write(out_paths[tf], lambda p, d=pure: d.to_parquet(p, engine="pyarrow", compression="zstd", index=False))
        out[tf] = df_tf
        out["audit"][tf] = audit
    return out


# ============================ L5 — split ============================

def layer5_split(df):
    sp = PIPELINE_PARAMETERS["splits"]
    ts = df["timestamp"]

    def b(d):
        return pd.Timestamp(d, tz="UTC")

    warmup = (ts >= b(sp["warmup_start"])) & (ts <= b(sp["warmup_end"]) + pd.Timedelta(days=1))
    train = (ts >= b(sp["train_start"])) & (ts <= b(sp["train_end"]) + pd.Timedelta(days=1))
    oos = (ts >= b(sp["oos_start"])) & (ts <= b(sp["oos_end"]) + pd.Timedelta(days=1))
    tr_idx, oos_idx = np.where(train.to_numpy())[0], np.where(oos.to_numpy())[0]
    bounds = {"train_start_idx": int(tr_idx[0]), "train_end_idx": int(tr_idx[-1]),
              "oos_start_idx": int(oos_idx[0]), "oos_end_idx": int(oos_idx[-1])}
    return {"warmup": warmup.to_numpy(), "train": train.to_numpy(), "oos": oos.to_numpy()}, bounds


def purge_train_setups(events, bounds):
    H, emb, oos0 = PIPELINE_PARAMETERS["H"], embargo_candles(), bounds["oos_start_idx"]
    kept = [s for s in events if s["t0"] + H + emb <= oos0]
    assert all(s["t0"] + H < oos0 for s in kept), "purge boundary assertion failed: label crosses into OOS"
    return kept, len(events) - len(kept)


def make_segment_of_ts(params=PIPELINE_PARAMETERS):
    sp = params["splits"]

    def b(d):
        return pd.Timestamp(d, tz="UTC")

    bounds = [("warmup", b(sp["warmup_start"]), b(sp["warmup_end"]) + pd.Timedelta(days=1)),
              ("train", b(sp["train_start"]), b(sp["train_end"]) + pd.Timedelta(days=1)),
              ("oos", b(sp["oos_start"]), b(sp["oos_end"]) + pd.Timedelta(days=1))]

    def seg(ts):
        ts = pd.Timestamp(ts)
        ts = ts.tz_localize("UTC") if ts.tzinfo is None else ts.tz_convert("UTC")
        for name, lo, hi in bounds:
            if lo <= ts <= hi:
                return name
        return "none"
    return seg


# ============================ feature registry + manifest ============================

def _load_feature_registry(rel_path):
    return _load_json(ROOT / rel_path)


FEATURE_REGISTRIES = {ns: _load_feature_registry(cfg["registry"])
                      for ns, cfg in FEATURE_NAMESPACES["namespaces"].items()}
NAMESPACE_ORDER = list(FEATURE_NAMESPACES["namespace_order"])


def _registry_features(namespace):
    return list(FEATURE_REGISTRIES[namespace]["features"])


PER_ASSET_OVERRIDES_PATH = ROOT / "config" / "per_asset_feature_overrides.json"


def _load_per_asset_overrides():
    """Gitignored per-asset optional-feature allowlists written by the feature-search worker.
    Absent file == no overrides (the resolver path is then identical to the global default)."""
    if not PER_ASSET_OVERRIDES_PATH.exists():
        return {}
    return _load_json(PER_ASSET_OVERRIDES_PATH).get("asset_overrides", {})


def _override_selection(ticker, overrides, registries):
    """Validated optional-id set for `ticker`, or None. Fail-closed: the frozen 1h namespace
    (ids 1-99) may never appear in an override, nor may unknown/unimplemented ids."""
    if ticker is None:
        return None
    ov = overrides.get(str(ticker).upper())
    if ov is None:
        return None
    sel = {int(i) for i in ov["selected_optional_ids"]}
    if any(1 <= i <= 99 for i in sel):
        raise RuntimeError(f"per-asset override for {ticker} may not touch the frozen 1h namespace (ids 1-99)")
    known = {int(f["id"]) for reg in registries.values()
             for f in reg["features"] if bool(f.get("implemented", True))}
    unknown = sel - known
    if unknown:
        raise RuntimeError(f"per-asset override for {ticker} names unknown/unimplemented feature ids: {sorted(unknown)}")
    return sel


def resolve_feature_manifest(ticker=None, cfg=None, registries=None, overrides=None):
    cfg = FEATURE_NAMESPACES if cfg is None else cfg
    registries = FEATURE_REGISTRIES if registries is None else registries
    overrides = _load_per_asset_overrides() if overrides is None else overrides
    sel = _override_selection(ticker, overrides, registries)
    active = [ns for ns in cfg["namespace_order"] if cfg["namespaces"][ns].get("enabled", True)]
    blocks, ids, names = [], [], []
    for ns in active:
        feats = sorted(list(registries[ns]["features"]), key=lambda f: int(f["id"]))
        block_ids = [int(f["id"]) for f in feats if bool(f.get("implemented", True))]
        block_names = [f["name"] for f in feats if bool(f.get("implemented", True))]
        if sel is not None and ns != "1h":
            keep = [k for k, i in enumerate(block_ids) if i in sel]
            block_ids = [block_ids[k] for k in keep]
            block_names = [block_names[k] for k in keep]
            if not block_ids:
                continue
        blocks.append({"namespace": ns, "id_range": cfg["namespaces"][ns]["id_range"],
                       "feature_ids": block_ids, "feature_names": block_names,
                       "feature_count": len(block_ids)})
        ids.extend(block_ids)
        names.extend(block_names)
    source = "config/feature_namespaces.json"
    if sel is not None:
        source += f" + config/per_asset_feature_overrides.json[{str(ticker).upper()}]"
    return {"schema_version": cfg.get("schema_version", "simple_features.v1"),
            "ticker": ticker,
            "namespace_order": list(cfg["namespace_order"]),
            "active_namespaces": [b["namespace"] for b in blocks],
            "per_namespace": blocks,
            "effective_feature_ids": ids,
            "effective_feature_names": names,
            "effective_feature_count": len(names),
            "feature_selection_source": source}


DEFAULT_FEATURE_MANIFEST = resolve_feature_manifest(None)


def feature_names_of(manifest=None):
    return (manifest or DEFAULT_FEATURE_MANIFEST)["effective_feature_names"]


def output_b_columns(manifest):
    cols = [("asset_id", "str"), ("setup_id", "setup_id"),
            ("signal_open_timestamp", "ts"), ("decision_timestamp", "ts"), ("entry_fill_timestamp", "ts")]
    cols.extend((n, "float") for n in feature_names_of(manifest))
    cols.extend([("target_level", "float"), ("stop_level", "float"), ("barrier_width_pct", "float"),
                 ("local_market_exit_reason", "str"), ("local_per_unit_net_return", "float"),
                 ("Y_outcome", "int"), ("label_uniqueness_weight", "float")])
    return cols


def _base_feature_frame(df, namespace):
    suffix = "" if namespace == "1h" else f"_{namespace}"
    c = df["close"].to_numpy(float)
    h = df["high"].to_numpy(float)
    l = df["low"].to_numpy(float)
    v = df["volume"].to_numpy(float)
    idx = df.index
    close_s = pd.Series(c, index=idx)
    vol_s = pd.Series(v, index=idx)
    log1 = np.log(close_s / close_s.shift(1)).to_numpy()
    log5 = np.log(close_s / close_s.shift(5)).to_numpy()
    log20 = np.log(close_s / close_s.shift(20)).to_numpy()
    sma20 = close_s.rolling(PIPELINE_PARAMETERS["W_SMA_FAST"]).mean()
    sma50 = close_s.rolling(PIPELINE_PARAMETERS["W_SMA_SLOW"]).mean()
    close_mean20 = sma20.to_numpy()
    close_std20 = close_s.rolling(20).std(ddof=0).to_numpy()
    vol_mean20 = vol_s.rolling(PIPELINE_PARAMETERS["W_VOL"]).mean().to_numpy()
    vol_std20 = vol_s.rolling(PIPELINE_PARAMETERS["W_VOL"]).std(ddof=0).to_numpy()
    atr = wilder_atr(h, l, c, PIPELINE_PARAMETERS["W_ATR"])
    rsi = _rsi(c, PIPELINE_PARAMETERS["W_RSI"])
    bb_mid = sma20.to_numpy()
    bb_std = close_s.rolling(PIPELINE_PARAMETERS["W_BB"]).std(ddof=0).to_numpy()
    bb_upper = bb_mid + PIPELINE_PARAMETERS["BB_K"] * bb_std
    bb_lower = bb_mid - PIPELINE_PARAMETERS["BB_K"] * bb_std
    bb_width = bb_upper - bb_lower
    macd_line = _ema(c, PIPELINE_PARAMETERS["MACD_FAST"]) - _ema(c, PIPELINE_PARAMETERS["MACD_SLOW"])
    macd_signal = pd.Series(macd_line).ewm(span=PIPELINE_PARAMETERS["MACD_SIGNAL"], adjust=False,
                                           min_periods=PIPELINE_PARAMETERS["MACD_SIGNAL"]).mean().to_numpy()
    macd_hist = macd_line - macd_signal
    realized_vol = pd.Series(log1).rolling(20).std(ddof=0).to_numpy() * math.sqrt(20.0)
    frame = pd.DataFrame(index=idx)
    frame[f"direction{suffix}"] = np.sign(log5)
    frame[f"log_return_1{suffix}"] = log1
    frame[f"log_return_5{suffix}"] = log5
    frame[f"log_return_20{suffix}"] = log20
    frame[f"close_z_score_20{suffix}"] = np.where(close_std20 == 0.0, 0.0, (c - close_mean20) / close_std20)
    frame[f"dist_to_sma_20{suffix}"] = c / sma20.to_numpy() - 1.0
    frame[f"dist_to_sma_50{suffix}"] = c / sma50.to_numpy() - 1.0
    frame[f"sma_20_sma_50_ratio{suffix}"] = sma20.to_numpy() / sma50.to_numpy() - 1.0
    frame[f"volume_z_score_20{suffix}"] = np.where(vol_std20 == 0.0, 0.0, (v - vol_mean20) / vol_std20)
    frame[f"atr_pct_14{suffix}"] = 100.0 * atr / c
    frame[f"realized_volatility_20{suffix}"] = realized_vol
    frame[f"rsi_14{suffix}"] = rsi
    frame[f"bollinger_percent_b_20_2{suffix}"] = np.where(bb_width == 0.0, 0.5, (c - bb_lower) / bb_width)
    frame[f"bollinger_bandwidth_20_2{suffix}"] = bb_width / bb_mid
    frame[f"macd_line_12_26_9{suffix}"] = macd_line
    frame[f"macd_signal_12_26_9{suffix}"] = macd_signal
    frame[f"macd_hist_12_26_9{suffix}"] = macd_hist
    frame[f"__atr_14_abs{suffix}"] = atr
    return frame


def _project_context(base_decisions, df_tf, namespace):
    feats = _base_feature_frame(df_tf, namespace)
    names = [f["name"] for f in _registry_features(namespace)]
    if df_tf is None or not len(df_tf):
        return pd.DataFrame({n: np.nan for n in names}, index=base_decisions.index)
    right = feats[names].copy()
    right["available_at"] = pd.to_datetime(df_tf["available_at"]).reset_index(drop=True)
    left = pd.DataFrame({"decision_timestamp": base_decisions}).reset_index(names="row_id")
    merged = pd.merge_asof(left.sort_values("decision_timestamp"),
                           right.sort_values("available_at"),
                           left_on="decision_timestamp", right_on="available_at",
                           direction="backward").sort_values("row_id")
    return merged[names].reset_index(drop=True)


def _multi_tf_features(features):
    out = pd.DataFrame(index=features.index)

    def sign_col(name):
        return np.sign(features[name].to_numpy(float))

    momentum = np.vstack([sign_col("log_return_5"), sign_col("log_return_5_1d"), sign_col("log_return_5_1w")])
    macd = np.vstack([sign_col("macd_hist_12_26_9"), sign_col("macd_hist_12_26_9_1d"),
                      sign_col("macd_hist_12_26_9_1w")])
    sma = np.vstack([sign_col("dist_to_sma_20"), sign_col("dist_to_sma_20_1d"), sign_col("dist_to_sma_20_1w")])
    out["momentum_alignment_multi"] = np.nanmean(momentum, axis=0)
    out["rsi_spread_1h_1d"] = (features["rsi_14"] - features["rsi_14_1d"]) / 100.0
    out["volatility_ratio_1h_1d"] = _safe_div(features["atr_pct_14"], features["atr_pct_14_1d"])
    out["macd_hist_alignment_multi"] = np.nanmean(macd, axis=0)
    out["price_vs_sma_alignment_multi"] = np.nanmean(sma, axis=0)
    return out


def build_feature_context(df, manifest=None):
    manifest = manifest or DEFAULT_FEATURE_MANIFEST
    decisions = pd.Series([decision_timestamp_of_event(df, i) for i in range(len(df))])
    f1h = _base_feature_frame(df, "1h")
    df_1d, audit_1d = aggregate_to_timeframe(df, "1d")
    df_1w, audit_1w = aggregate_to_timeframe(df, "1w")
    f1d = _project_context(decisions, df_1d, "1d")
    f1w = _project_context(decisions, df_1w, "1w")
    combined = pd.concat([f1h.reset_index(drop=True), f1d, f1w], axis=1)
    combined = pd.concat([combined, _multi_tf_features(combined)], axis=1)
    return {"features": combined, "timeframes": {"1d": df_1d, "1w": df_1w},
            "audit": {"1d": audit_1d, "1w": audit_1w}, "manifest": manifest}


def mandatory_core_feature_names(manifest):
    for block in manifest["per_namespace"]:
        if block["namespace"] == "1h":
            return list(block["feature_names"])
    raise RuntimeError("resolved manifest has no 1h namespace")


def core_feature_eligibility(values, manifest):
    arr = np.asarray([values[n] for n in mandatory_core_feature_names(manifest)], dtype=float)
    if np.isnan(arr).any():
        return "nan"
    if np.isinf(arr).any():
        return "inf"
    return None


# ============================ L6 — candidates, features, Triple Barrier ============================

def generate_candidate_events(df, scan_mask, feature_context=None):
    ctx = feature_context or build_feature_context(df)
    feats = ctx["features"]
    atr = feats["__atr_14_abs"].to_numpy(float)
    momentum = feats[PIPELINE_PARAMETERS["SIGNAL_MOMENTUM_FEATURE"]].to_numpy(float)
    idx = np.where(scan_mask)[0]
    events = []
    for t0 in idx:
        if t0 + 1 >= len(df):
            continue
        mom = momentum[t0]
        width = atr[t0] * PIPELINE_PARAMETERS["TB_ATR_MULTIPLIER"]
        if not (math.isfinite(mom) and math.isfinite(width) and width > EPS):
            continue
        direction = 1 if mom > 0 else (-1 if mom < 0 else 0)
        if direction == 0:
            continue
        events.append({"direction": int(direction), "t0": int(t0), "atr_t0": float(atr[t0]),
                       "barrier_width": float(width)})
    return events, {"candidates": len(events)}


def simulate_trade(df, event, end_idx):
    H = PIPELINE_PARAMETERS["H"]
    fee = PIPELINE_PARAMETERS["COMMISSION_BPS"] * 1e-4
    slip = PIPELINE_PARAMETERS["SLIPPAGE_BPS"] * 1e-4
    s = event["direction"]
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    t0, t_fill = event["t0"], event["t0"] + 1
    if t_fill > end_idx:
        return {"skip": "GAP_INVALIDATED_SKIP"}
    entry_fill = o[t_fill] * (1 + s * slip)
    width = float(event["barrier_width"])
    if not (math.isfinite(width) and width > EPS):
        return {"skip": "INVALID_BARRIER_SKIP"}
    tp = entry_fill + s * width
    sl = entry_fill - s * width
    t_deadline = t0 + H
    t_sched = min(t_deadline, end_idx)
    exit_idx = exit_fill = reason = kind = trig = None
    for t in range(t_fill, t_sched):
        target_hit = s * (c[t] - tp) >= 0
        stop_hit = s * (c[t] - sl) <= 0
        if target_hit or stop_hit:
            if t + 1 > end_idx:
                break
            exit_idx, kind, trig = t + 1, "condition", t
            exit_fill = o[t + 1] * (1 - s * slip)
            reason = "TARGET_TRIGGER" if target_hit and not stop_hit else "STOP_TRIGGER"
            break
    if exit_idx is None:
        exit_idx, kind, trig = t_sched, "scheduled", t_sched
        exit_fill = c[t_sched] * (1 - s * slip)
        reason = "OOS_END_FORCED_EXIT" if t_sched == end_idx else "TIME_BARRIER"
    per_unit = (s * (exit_fill - entry_fill) - fee * (entry_fill + exit_fill)) / (entry_fill * (1 + fee))
    return {"skip": None, "t_fill": t_fill, "entry_fill": float(entry_fill), "exit_idx": int(exit_idx),
            "exit_fill": float(exit_fill), "market_exit_reason": reason, "exit_kind": kind,
            "trigger_idx": int(trig), "local_per_unit_net_return": float(per_unit),
            "target_level": float(tp), "stop_level": float(sl), "barrier_width": float(width)}


def _uniqueness_weights(actionable):
    if not actionable:
        return {}
    lo = min(a["t_fill"] for a in actionable)
    hi = max(a["t_end"] for a in actionable)
    conc = np.zeros(hi - lo + 2)
    for a in actionable:
        conc[a["t_fill"] - lo:a["t_end"] - lo + 1] += 1
    return {a["setup_id"]: float(np.mean(1.0 / np.maximum(1.0, conc[a["t_fill"] - lo:a["t_end"] - lo + 1])))
            for a in actionable}


def _event_features(feature_context, event, manifest):
    row = feature_context["features"].iloc[event["t0"]]
    return {n: float(row[n]) for n in feature_names_of(manifest)}


def layer6_output_b(df, events, ticker, end_idx, manifest=None, feature_context=None):
    manifest = manifest or resolve_feature_manifest(ticker)
    feature_context = feature_context or build_feature_context(df, manifest)
    eligibility = {"core_nan_excluded": 0, "core_inf_excluded": 0}
    rows, actionable = [], []
    for ev in events:
        sid = f"{ticker}:{ev['t0']}:{ev['direction']}"
        feats = _event_features(feature_context, ev, manifest)
        reason = core_feature_eligibility(feats, manifest)
        if reason is not None:
            eligibility[f"core_{reason}_excluded"] += 1
            continue
        sim = simulate_trade(df, ev, end_idx)
        if sim["skip"] is not None:
            continue
        entry = sim["entry_fill"]
        rows.append({"asset_id": ticker, "setup_id": sid, "direction": ev["direction"],
                     "signal_open_timestamp": bar_open_timestamp(df, ev["t0"]),
                     "decision_timestamp": decision_timestamp_of_event(df, ev["t0"]),
                     "entry_fill_timestamp": bar_open_timestamp(df, sim["t_fill"]), **feats,
                     "target_level": sim["target_level"], "stop_level": sim["stop_level"],
                     "barrier_width_pct": 100.0 * sim["barrier_width"] / max(EPS, abs(entry)),
                     "local_market_exit_reason": sim["market_exit_reason"],
                     "local_per_unit_net_return": sim["local_per_unit_net_return"],
                     "Y_outcome": 1 if sim["local_per_unit_net_return"] > 0 else 0})
        actionable.append({"setup_id": sid, "t_fill": sim["t_fill"],
                           "t_end": min(ev["t0"] + PIPELINE_PARAMETERS["H"], end_idx)})
    weights = _uniqueness_weights(actionable)
    for r in rows:
        r["label_uniqueness_weight"] = weights.get(r["setup_id"], 1.0)
    cols = [c for c, _ in output_b_columns(manifest)]
    df_b = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)
    return df_b, eligibility


# ============================ L7 — Optuna ============================

def average_precision(y, score):
    y = np.asarray(y, int)
    score = np.asarray(score, float)
    pos = int(y.sum())
    if pos == 0:
        return 0.0
    order = np.argsort(-score, kind="mergesort")
    y, s = y[order], score[order]
    tp = np.cumsum(y)
    fp = np.cumsum(1 - y)
    grp = np.r_[np.where(np.diff(s) != 0)[0], len(s) - 1]
    recall = tp[grp] / pos
    precision = tp[grp] / np.maximum(1, tp[grp] + fp[grp])
    rprev = np.r_[0.0, recall[:-1]]
    return float(np.sum((recall - rprev) * precision))


def purged_wf_folds(t0s, train_start_idx, train_end_idx, k=CV_FOLDS):
    H, emb = PIPELINE_PARAMETERS["H"], embargo_candles()
    edges = np.linspace(train_start_idx, train_end_idx + 1, k + 2, dtype=int)
    folds = []
    for i in range(1, k + 1):
        val_lo, val_hi = int(edges[i]), int(edges[i + 1])
        val = [j for j, t0 in enumerate(t0s) if val_lo <= t0 < val_hi]
        cutoff = val_lo - emb
        tr = [j for j, t0 in enumerate(t0s) if t0 + H < cutoff]
        if len(val) >= 5 and len(tr) >= 10:
            folds.append((tr, val))
    return folds


def _xgb_train(X, y, w, params, seed, feature_names=None):
    import xgboost as xgb
    d = xgb.DMatrix(X, label=y, weight=w, feature_names=feature_names or feature_names_of())
    p = {"objective": "binary:logistic", "eval_metric": "aucpr", "seed": seed, "booster": "gbtree",
         "nthread": PIPELINE_PARAMETERS["XGBOOST_N_JOBS"], "max_depth": params["max_depth"], "eta": params["eta"],
         "subsample": params["subsample"], "colsample_bytree": params["colsample_bytree"],
         "min_child_weight": params["min_child_weight"], "lambda": params["reg_lambda"], "verbosity": 0}
    return xgb.train(p, d, num_boost_round=params["n_estimators"])


def layer7_optuna(df_b, bounds, seed, manifest=None, trials=None):
    import optuna
    import xgboost as xgb
    names = feature_names_of(manifest)
    trials = n_trials() if trials is None else int(trials)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    X = df_b[names].to_numpy(float)
    y = df_b["Y_outcome"].to_numpy(int)
    w = df_b["label_uniqueness_weight"].to_numpy(float)
    t0s = [int(sid.split(":")[1]) for sid in df_b["setup_id"]]
    folds = purged_wf_folds(t0s, bounds["train_start_idx"], bounds["train_end_idx"])
    if not folds or len(np.unique(y)) < 2:
        return dict(XGBOOST_OPTUNA_SEARCH_SPACE["fallback_params"]), 0.0, len(folds)

    def objective(trial):
        params = {}
        for sp in XGBOOST_OPTUNA_SEARCH_SPACE["parameters"]:
            nm = sp["name"]
            if sp["suggest"] == "int":
                params[nm] = trial.suggest_int(nm, sp["low"], sp["high"])
            else:
                params[nm] = trial.suggest_float(nm, sp["low"], sp["high"], log=bool(sp.get("log", False)))
        aps = []
        for step, (tr, va) in enumerate(folds):
            if len(np.unique(y[tr])) < 2:
                continue
            bst = _xgb_train(X[tr], y[tr], w[tr], params, seed, feature_names=names)
            p = bst.predict(xgb.DMatrix(X[va], feature_names=names))
            aps.append(average_precision(y[va], p))
            trial.report(float(np.mean(aps)), step)
            if trial.should_prune():
                raise optuna.TrialPruned()
        return float(np.mean(aps)) if aps else 0.0

    study = optuna.create_study(direction=XGBOOST_OPTUNA_SEARCH_SPACE["objective"]["direction"],
                                sampler=optuna.samplers.TPESampler(seed=seed),
                                pruner=optuna.pruners.MedianPruner(n_warmup_steps=MEDIAN_PRUNER_WARMUP))
    study.optimize(objective, n_trials=trials, show_progress_bar=False)
    best = dict(study.best_params)
    return best, float(study.best_value), len(folds)


def calibrate_kelly(df, df_b, train_events, bounds, best_params, seed, manifest=None):
    import optuna
    import xgboost as xgb
    kc = PIPELINE_PARAMETERS["KELLY_CALIBRATION"]
    E0, thr = PIPELINE_PARAMETERS["INITIAL_CAPITAL_USD"], PIPELINE_PARAMETERS["THRESHOLD_ENTRY"]
    grid = [float(x) for x in np.linspace(kc["low"], kc["high"], int(kc["grid_points"]))]
    names = feature_names_of(manifest)
    X = df_b[names].to_numpy(float)
    y = df_b["Y_outcome"].to_numpy(int)
    w = df_b["label_uniqueness_weight"].to_numpy(float)
    t0s = [int(sid.split(":")[1]) for sid in df_b["setup_id"]]
    folds = purged_wf_folds(t0s, bounds["train_start_idx"], bounds["train_end_idx"])
    if not folds:
        return float(kc["low"])
    ticker = str(df_b["asset_id"].iloc[0])
    by_sid = {f"{ticker}:{s['t0']}:{s['direction']}": s for s in train_events}
    fold_data = []
    for tr, va in folds:
        if len(np.unique(y[tr])) < 2:
            continue
        bst = _xgb_train(X[tr], y[tr], w[tr], best_params, seed, feature_names=names)
        oof = bst.predict(xgb.DMatrix(X[va], feature_names=names))
        scored = [(by_sid[df_b["setup_id"].iloc[j]], float(oof[k])) for k, j in enumerate(va)]
        vt0 = [t0s[j] for j in va]
        fold_data.append((scored, min(vt0), max(vt0)))
    if not fold_data:
        return float(kc["low"])
    assert all(hi < bounds["oos_start_idx"] for _, _, hi in fold_data), "Kelly calibration must not reach OOS"

    def objective(trial):
        lam = trial.suggest_float("kelly_fraction", kc["low"], kc["high"])
        g = 0.0
        for scored, lo, hi in fold_data:
            summ, _, _ = run_engine(df, scored, lo, hi, thr, kelly_fraction=lam)
            g += math.log(max(summ["end_capital"], EPS) / E0)
        return g

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.GridSampler({"kelly_fraction": grid}))
    study.optimize(objective, n_trials=len(grid), show_progress_bar=False)
    bv = study.best_value
    tied = [t.params["kelly_fraction"] for t in study.trials if t.value is not None and t.value >= bv - 1e-12]
    return float(min(tied)) if tied else float(study.best_params["kelly_fraction"])


# ============================ L8 — model + strategy ============================

def layer8_train(df_b, best_params, seed, manifest=None):
    names = feature_names_of(manifest)
    X = df_b[names].to_numpy(float)
    y = df_b["Y_outcome"].to_numpy(int)
    w = df_b["label_uniqueness_weight"].to_numpy(float)
    return _xgb_train(X, y, w, best_params, seed, feature_names=names)


def strategy_meta(booster, df_b, ticker, best_params, lineage, train_window, manifest=None):
    import xgboost as xgb
    manifest = manifest or resolve_feature_manifest(ticker)
    names = manifest["effective_feature_names"]
    raw = bytes(booster.save_raw())
    model_b64 = base64.b64encode(raw).decode("ascii")
    X = df_b[names].to_numpy(float)
    gv = X[:3] if len(X) >= 3 else X
    gp = booster.predict(xgb.DMatrix(gv, feature_names=names)).tolist() if len(gv) else []
    return {"ticker": ticker, "MODEL_B64": model_b64, "MODEL_HASH": sha256_bytes(raw),
            "FEATURE_MANIFEST": names, "FEATURE_IDS": manifest["effective_feature_ids"],
            "FEATURE_NAMESPACES": manifest["per_namespace"],
            "THRESHOLD_ENTRY": PIPELINE_PARAMETERS["THRESHOLD_ENTRY"],
            "LABEL_CONTRACT": "TripleBarrier.ATR.v1", "best_params": best_params, "TRAIN_WINDOW": train_window,
            "EXECUTION_CONTRACT": {"entry_fill": PIPELINE_PARAMETERS["ENTRY_FILL"],
                                   "exit_fill": PIPELINE_PARAMETERS["EXIT_FILL"],
                                   "scheduled_exit_fill": PIPELINE_PARAMETERS["SCHEDULED_EXIT_FILL"],
                                   "commission_bps": PIPELINE_PARAMETERS["COMMISSION_BPS"],
                                   "slippage_bps": PIPELINE_PARAMETERS["SLIPPAGE_BPS"],
                                   "capital_mode": PIPELINE_PARAMETERS["CAPITAL_MODE"],
                                   "barrier_mode": PIPELINE_PARAMETERS["BARRIER_MODE"],
                                   "triple_barrier_width": f"ATR{PIPELINE_PARAMETERS['W_ATR']} * "
                                                           f"{PIPELINE_PARAMETERS['TB_ATR_MULTIPLIER']}",
                                   "kelly_cap": PIPELINE_PARAMETERS["KELLY_CAP"],
                                   "kelly_basis": "per_trade_fractional_kelly_symmetric_b1"},
            "golden_vectors": gv.tolist() if len(gv) else [], "golden_pred": gp, **lineage}


def predict_p(booster, X, feature_names=None):
    import xgboost as xgb
    names = feature_names or feature_names_of()
    return booster.predict(xgb.DMatrix(np.asarray(X, float).reshape(-1, len(names)), feature_names=names))


def accept_strategy(train_summary):
    min_tr = PIPELINE_PARAMETERS["MIN_TRAIN_ACCEPTANCE_TRADES"]
    pf = train_summary["profit_factor"]
    rankable = pf is not None and math.isfinite(pf)
    if min_tr is None:
        return {"accepted": True, "mode": "correctness_check", "rankable": rankable,
                "reason": "MIN_TRAIN_ACCEPTANCE_TRADES is null -> correctness-check acceptance"}
    if train_summary["trades"] < min_tr:
        return {"accepted": False, "mode": "rejected", "rankable": rankable,
                "reason": "below MIN_TRAIN_ACCEPTANCE_TRADES"}
    if not rankable:
        return {"accepted": False, "mode": "rejected", "rankable": False, "reason": "PF not rankable"}
    return {"accepted": True, "mode": "accepted", "rankable": True, "reason": "PF-rankable, meets min trades"}


def run_engine(df, scored, start_idx, end_idx, threshold, kelly_fraction=None):
    E0 = PIPELINE_PARAMETERS["INITIAL_CAPITAL_USD"]
    fee = PIPELINE_PARAMETERS["COMMISSION_BPS"] * 1e-4
    slip = PIPELINE_PARAMETERS["SLIPPAGE_BPS"] * 1e-4
    kelly_cap = PIPELINE_PARAMETERS["KELLY_CAP"]
    tie_eps = PIPELINE_PARAMETERS["SIMULTANEOUS_SETUP_TIE_EPS"]
    c = df["close"].to_numpy()
    groups = {}
    for ev, p in scored:
        if start_idx <= ev["t0"] <= end_idx:
            groups.setdefault(ev["t0"], []).append((ev, p))
    counters = dict(signals_total=sum(len(v) for v in groups.values()), threshold_rejects=0, not_selected=0,
                    simultaneous_tie_skip=0, gap_invalidated_skip=0,
                    invalid_barrier_skip=0, ignored_while_open=0, entered=0)
    E = E0
    equity_events = [{"event_type": "initial_capital", "bar_index": -1, "trade_id": 0, "equity": E0}]
    ledger, exposure_bars, flat_from, halted, tid = [], 0, start_idx, False, 0
    for t0 in sorted(groups):
        if halted:
            break
        if t0 < flat_from:
            counters["ignored_while_open"] += len(groups[t0])
            continue
        cands = sorted(groups[t0], key=lambda x: -x[1])
        passing = [(ev, p) for ev, p in cands if p >= threshold]
        counters["threshold_rejects"] += len(cands) - len(passing)
        if not passing:
            continue
        if len(passing) >= 2 and abs(passing[0][1] - passing[1][1]) <= tie_eps:
            counters["simultaneous_tie_skip"] += len(passing)
            continue
        chosen, chosen_p = passing[0]
        counters["not_selected"] += len(passing) - 1
        sim = simulate_trade(df, chosen, end_idx)
        if sim["skip"] == "GAP_INVALIDATED_SKIP":
            counters["gap_invalidated_skip"] += 1
            continue
        if sim["skip"] == "INVALID_BARRIER_SKIP":
            counters["invalid_barrier_skip"] += 1
            continue
        s = chosen["direction"]
        entry_fill, exit_fill, exit_idx = sim["entry_fill"], sim["exit_fill"], sim["exit_idx"]
        f_size = 1.0 if kelly_fraction is None else min(max(kelly_fraction * (2.0 * chosen_p - 1.0), 0.0), kelly_cap)
        if f_size <= 0.0:
            counters["not_selected"] += 1
            continue
        q = f_size * E / (entry_fill * (1 + fee))
        entry_fee, exit_fee = q * entry_fill * fee, q * exit_fill * fee
        raw_net = s * q * (exit_fill - entry_fill) - entry_fee - exit_fee
        account_net = max(raw_net, -E)
        uncovered = max(-(E + raw_net), 0.0)
        E_before = E
        counters["entered"] += 1
        tid += 1
        equity_events.append({"event_type": "entry_fee_mark", "bar_index": int(sim["t_fill"]), "trade_id": tid,
                              "equity": max(0.0, E_before - entry_fee)})
        mark_end = exit_idx - 1 if sim["exit_kind"] == "condition" else exit_idx
        for t in range(sim["t_fill"], mark_end + 1):
            liq = c[t] * (1 - s * slip)
            equity_events.append({"event_type": "held_close_mark", "bar_index": int(t), "trade_id": tid,
                                  "equity": max(0.0, E_before + s * q * (liq - entry_fill) - entry_fee - q * liq * fee)})
        E = E + account_net
        cap_state = "ACTIVE"
        if E_before + raw_net <= 0:
            E, cap_state, halted = 0.0, "HALTED_CAPITAL_DEPLETED", True
        equity_events.append({"event_type": "exit_fill", "bar_index": int(exit_idx), "trade_id": tid, "equity": E})
        exposure_bars += (exit_idx - sim["t_fill"] + 1)
        flat_from = exit_idx if sim["exit_kind"] == "condition" else exit_idx + 1
        cond = sim["exit_kind"] == "condition"
        exit_fill_ts = bar_open_timestamp(df, exit_idx) if cond else bar_close_timestamp(df, exit_idx)
        ledger.append({"trade_id": tid, "direction": s,
                       "setup_t0_index": int(t0), "signal_bar_index": int(t0), "decision_bar_index": int(t0),
                       "entry_fill_index": int(sim["t_fill"]),
                       "exit_trigger_index": (int(sim["trigger_idx"]) if cond else -1),
                       "exit_fill_index": int(exit_idx),
                       "signal_open_timestamp": str(bar_open_timestamp(df, t0)),
                       "decision_timestamp": str(decision_timestamp_of_event(df, t0)),
                       "entry_fill_timestamp": str(bar_open_timestamp(df, sim["t_fill"])),
                       "exit_trigger_timestamp": (str(bar_close_timestamp(df, sim["trigger_idx"])) if cond else ""),
                       "exit_fill_timestamp": str(exit_fill_ts),
                       "entry_fill": entry_fill, "exit_fill": exit_fill,
                       "target_level": sim["target_level"], "stop_level": sim["stop_level"],
                       "barrier_width_pct": 100.0 * sim["barrier_width"] / max(EPS, abs(entry_fill)),
                       "model_prob": float(chosen_p), "kelly_fraction_applied": float(f_size),
                       "quantity": q, "market_exit_reason": sim["market_exit_reason"], "capital_state": cap_state,
                       "capital_before": E_before, "raw_net_pnl_usd": raw_net, "account_net_pnl_usd": account_net,
                       "uncovered_loss_usd": uncovered, "capital_after": E})
    total_bars = end_idx - start_idx + 1
    nets = np.array([t["account_net_pnl_usd"] for t in ledger]) if ledger else np.array([])
    gp = float(nets[nets > 0].sum()) if len(nets) else 0.0
    gl = float(-nets[nets < 0].sum()) if len(nets) else 0.0
    pf = None if (not len(nets) or gl == 0) else gp / gl
    eq = np.array([ev["equity"] for ev in equity_events])
    peak = np.maximum.accumulate(eq)
    mdd = float(np.max((peak - eq) / np.maximum(EPS, peak)) * 100) if len(eq) > 1 else 0.0
    wins, losses = int((nets > 0).sum()), int((nets < 0).sum())
    summary = {"start_capital": E0, "end_capital": float(E), "net_pnl_usd": float(E - E0),
               "return_pct": float((E / E0 - 1) * 100), "profit_factor": pf, "max_drawdown_pct": mdd,
               "win_rate_pct": (wins / len(nets) * 100) if len(nets) else 0.0, "trades": len(ledger),
               "wins": wins, "losses": losses,
               "time_in_market_pct": round(100.0 * exposure_bars / max(1, total_bars), 4),
               "forced_oos_exits": int(sum(1 for t in ledger if t["market_exit_reason"] == "OOS_END_FORCED_EXIT")),
               "capital_depleted": bool(halted),
               "uncovered_loss_total_usd": float(sum(t["uncovered_loss_usd"] for t in ledger)),
               "max_uncovered_loss_usd": float(max((t["uncovered_loss_usd"] for t in ledger), default=0.0)),
               **counters}
    return summary, ledger, equity_events


def hodl_fallback(df, start_idx, end_idx):
    """OOS verdict fallback when the model produced ZERO trades: one long buy-and-hold
    trade — buy at the first OOS bar's open, sell at the last OOS bar's close, the same
    fill/cost model as the engine (slippage both ways, commission both sides), all-in
    from INITIAL_CAPITAL_USD. Returns (summary, ledger, equity_events) in the exact
    run_engine shape. Honestly labeled: capital_mode=hodl_fallback_no_model_trades,
    exit reason HODL_FALLBACK_EXIT, summary flag hodl_fallback=True — the README and
    the dashboard row then describe a benchmark path, never model trades."""
    p = PIPELINE_PARAMETERS
    E0 = p["INITIAL_CAPITAL_USD"]
    fee = p["COMMISSION_BPS"] * 1e-4
    slip = p["SLIPPAGE_BPS"] * 1e-4
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    entry_fill = float(o[start_idx] * (1 + slip))
    exit_fill = float(c[end_idx] * (1 - slip))
    q = E0 / (entry_fill * (1 + fee))
    entry_fee, exit_fee = q * entry_fill * fee, q * exit_fill * fee
    net = q * (exit_fill - entry_fill) - entry_fee - exit_fee
    E = E0 + net
    equity_events = [{"event_type": "initial_capital", "bar_index": -1, "trade_id": 0, "equity": E0},
                     {"event_type": "entry_fee_mark", "bar_index": int(start_idx), "trade_id": 1,
                      "equity": max(0.0, E0 - entry_fee)}]
    for t in range(start_idx, end_idx + 1):
        liq = c[t] * (1 - slip)
        equity_events.append({"event_type": "held_close_mark", "bar_index": int(t), "trade_id": 1,
                              "equity": max(0.0, E0 + q * (liq - entry_fill) - entry_fee - q * liq * fee)})
    equity_events.append({"event_type": "exit_fill", "bar_index": int(end_idx), "trade_id": 1,
                          "equity": float(E)})
    nan = float("nan")
    ledger = [{"trade_id": 1, "direction": 1,
               "setup_t0_index": int(start_idx), "signal_bar_index": int(start_idx),
               "decision_bar_index": int(start_idx),
               "entry_fill_index": int(start_idx), "exit_trigger_index": -1,
               "exit_fill_index": int(end_idx),
               "signal_open_timestamp": str(bar_open_timestamp(df, start_idx)),
               "decision_timestamp": str(bar_open_timestamp(df, start_idx)),
               "entry_fill_timestamp": str(bar_open_timestamp(df, start_idx)),
               "exit_trigger_timestamp": "",
               "exit_fill_timestamp": str(bar_close_timestamp(df, end_idx)),
               "entry_fill": entry_fill, "exit_fill": exit_fill,
               "target_level": nan, "stop_level": nan, "barrier_width_pct": nan,
               "model_prob": nan, "kelly_fraction_applied": 1.0,
               "quantity": float(q), "market_exit_reason": "HODL_FALLBACK_EXIT",
               "capital_state": "ACTIVE", "capital_before": E0,
               "raw_net_pnl_usd": float(net), "account_net_pnl_usd": float(net),
               "uncovered_loss_usd": 0.0, "capital_after": float(E)}]
    eq = np.array([ev["equity"] for ev in equity_events])
    peak = np.maximum.accumulate(eq)
    mdd = float(np.max((peak - eq) / np.maximum(EPS, peak)) * 100)
    summary = {"start_capital": E0, "end_capital": float(E), "net_pnl_usd": float(net),
               "return_pct": float((E / E0 - 1) * 100),
               "profit_factor": None if net > 0 else 0.0,   # single trade: win => no gross loss
               "max_drawdown_pct": mdd,
               "win_rate_pct": 100.0 if net > 0 else 0.0, "trades": 1,
               "wins": int(net > 0), "losses": int(net <= 0),
               "time_in_market_pct": 100.0, "forced_oos_exits": 0,
               "capital_depleted": bool(E <= 0),
               "uncovered_loss_total_usd": 0.0, "max_uncovered_loss_usd": 0.0,
               "signals_total": 0, "threshold_rejects": 0, "not_selected": 0,
               "simultaneous_tie_skip": 0, "gap_invalidated_skip": 0,
               "invalid_barrier_skip": 0, "ignored_while_open": 0, "entered": 1,
               "capital_mode": "hodl_fallback_no_model_trades", "hodl_fallback": True}
    return summary, ledger, equity_events


# ============================ orchestration helpers ============================

def derive_output_b(df, ticker, manifest=None):
    manifest = manifest or resolve_feature_manifest(ticker)
    masks, bounds = layer5_split(df)
    feature_context = build_feature_context(df, manifest)
    events, candidate_audit = generate_candidate_events(df, masks["train"], feature_context)
    train_events, n_purged = purge_train_setups(events, bounds)
    df_b, eligibility_audit = layer6_output_b(df, train_events, ticker, bounds["oos_start_idx"] - 1,
                                                manifest, feature_context)
    audit = {"candidates": candidate_audit, "eligibility": eligibility_audit,
             "scoring": {"train_core_ineligible_skipped": None, "oos_core_ineligible_skipped": None}}
    return {"df": df, "masks": masks, "bounds": bounds, "train_events": train_events,
            "df_b": df_b, "audit": audit, "n_purged": n_purged,
            "manifest": manifest, "feature_context": feature_context}


def derive_output_b_from_parquet(parquet_path, ticker, manifest=None):
    return derive_output_b(pd.read_parquet(parquet_path), ticker, manifest)


def score_setups(booster, df, events, manifest=None, context_states=None, audit=None):
    if not events:
        return []
    manifest = manifest or DEFAULT_FEATURE_MANIFEST
    names = feature_names_of(manifest)
    feature_context = context_states or build_feature_context(df, manifest)
    eligible, X, skipped = [], [], 0
    for ev in events:
        feats = _event_features(feature_context, ev, manifest)
        if core_feature_eligibility(feats, manifest) is not None:
            skipped += 1
            continue
        eligible.append(ev)
        X.append([feats[k] for k in names])
    if audit is not None:
        audit["core_ineligible_skipped"] = skipped
    if not eligible:
        return []
    ps = predict_p(booster, X, feature_names=names)
    return list(zip(eligible, [float(p) for p in ps]))

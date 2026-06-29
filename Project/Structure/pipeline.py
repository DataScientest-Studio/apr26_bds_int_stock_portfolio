#!/usr/bin/env python3
"""Runtime implementation of the 1.6-4.2 per-Asset pipeline.

Faithful to Layers_Short_SOT/ENG/*: causal trend-line detector (2.1 + DET-09); index/time-based purge +
embargo (1.7); the FT1–FT8 8-X FEATURE_MANIFEST + per-Asset Feature (F9–F18) selection (2.3) resolving the
effective feature manifest + the single TB_v1.2 label (2.2) + the deterministic Output-B
serializer; Optuna TPE + MedianPruner maximizing AUC-PR over purged walk-forward CV by candle index (3.1,
N_TRIALS + k=4 folds); XGBoost meta-label + base64 strategy artifact with Train acceptance (3.2); and ONE
sequential event engine (run_engine) shared by Train acceptance and the OOS verdict (4.1) — all-in compounding
Risk-Box, the canonical per-candle clock (pre-submitted scheduled exit t_sched =
min(t_deadline, t_collapse, oos_end); audit precedence OOS_END > TIME_BARRIER > RISK_BOX_COLLAPSED), event-path
mark-to-market MDD, inclusive TIM, and the full Risk-Box trade ledger.

RESULT_STATUS is NON_INTERPRETABLE by contract while CORP_ACTIONS_POLICY = deferred and
MIN_OOS_TRADES_FOR_INTERPRETATION = null (every run is a correctness check, not an edge claim — no dev/prod mode).
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

# This minimal build drops the lib/determinism + contracts/temporal_contract packages. Only what the functional pipeline
# actually needs survives, inlined here: a tiny model-identity hash (the strategy artifact's MODEL_HASH), a plain JSON
# loader, and the bar/event wall-clock helpers. Bars are interval_start with a fixed 1h nominal duration, so
# bar_close = bar_open + 1h; the US-equities session timezone drives the 1d/1w roll-up day boundary.
def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def _load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


ROOT = Path(__file__).resolve().parent
PIPELINE_PARAMETERS = _load_json(ROOT / "config" / "pipeline_parameters.json")
# 3.1 XGBoost Optuna search space + objective — single SOT (config/xgboost_optuna_search_space.json).
XGBOOST_OPTUNA_SEARCH_SPACE_PATH = ROOT / "config" / "xgboost_optuna_search_space.json"
XGBOOST_OPTUNA_SEARCH_SPACE = _load_json(XGBOOST_OPTUNA_SEARCH_SPACE_PATH)
CONTEXT_TIMEFRAMES = ("1d", "1w")                      # coarse causal-context timeframes rolled up from 1h
OHLCV_COLUMNS = ["timestamp", "open", "high", "low", "close", "volume"]   # the pure-OHLCV parquet contract (1.6)
SESSION_TIMEZONE = "America/New_York"                  # US-equities session day boundary (used by the 1d/1w roll-up)
_BAR_DURATION = pd.Timedelta(hours=1)                  # 1h source bar nominal duration (interval_start -> close = open + 1h)


def bar_open_timestamp(df, t):
    """OPEN wall-clock of bar t (interval_start) — the fill clock for open-fill events (entry, condition exit)."""
    return pd.Timestamp(df["timestamp"].iloc[t])


def bar_close_timestamp_from_open(open_ts):
    """CLOSE wall-clock from a known bar OPEN = open + nominal 1h duration."""
    return pd.Timestamp(open_ts) + _BAR_DURATION


def bar_close_timestamp(df, t):
    """CLOSE wall-clock of bar t = open + 1h — the close-fill clock (scheduled/MOC/OOS exit) and the decision clock."""
    return bar_close_timestamp_from_open(bar_open_timestamp(df, t))


def decision_timestamp_of_setup(df, t0):
    """Point-in-time decision clock: the setup signal is known at the CLOSE of the 1h bar at t0 (= bar_close(t0))."""
    return bar_close_timestamp(df, t0)


CV_FOLDS = int(XGBOOST_OPTUNA_SEARCH_SPACE["objective"]["cv_folds"])              # 3.1 SOT: purged walk-forward CV (from registry)
MEDIAN_PRUNER_WARMUP = int(XGBOOST_OPTUNA_SEARCH_SPACE["objective"]["pruner_warmup"])  # 3.1 SOT: MedianPruner warmup (from registry)
EPS = float(PIPELINE_PARAMETERS.get("EPS", 1e-9))


# ============================ determinism + parameter validation ============================

def seed_everything(seed=None):
    seed = PIPELINE_PARAMETERS["RANDOM_SEED"] if seed is None else seed
    random.seed(seed)
    np.random.seed(seed)
    return seed


def n_trials():
    # production HPO budget = the config value ONLY (no env override; cycle_id binds parameters_sha256, not
    # an environment variable, so an override would desync lineage from the model). Tests pass `trials=` to l9.
    return int(PIPELINE_PARAMETERS["N_TRIALS"])


def embargo_candles():
    # EMBARGO_BARS is a plain observed-bar count (bar-index space; no "sessions × bars/session" pseudo-semantics
    # — a session is not always 7 bars: early closes are 4).
    return int(PIPELINE_PARAMETERS["EMBARGO_BARS"])


def validate_parameters(p=PIPELINE_PARAMETERS):
    """Fail-closed schema validation before 1.4/3.1/4.1 (00_parameters 'Schema validation (fail-closed)')."""
    errs = []
    enums = {"BARRIER_MODE": {"close"},
             "CAPITAL_MODE": {"all_in_compounding_per_asset", "kelly_fractional_compounding"},
             "ENTRY_FILL": {"next_bar_open"}, "EXIT_FILL": {"trigger_next_open"},
             "SCHEDULED_EXIT_FILL": {"scheduled_moc_close"}, "POSITION_POLICY": {"one_open_position_per_asset"},
             "CORP_ACTIONS_POLICY": {"deferred", "A_adjusted", "B_raw_exclude"},
             "UNIVERSE_MODE": {"current_constituents_research", "point_in_time_constituents"},
             "OPTUNA_OBJECTIVE": {"auc_pr"}, "CV_SCHEME": {"purged_walk_forward"},
             "PF_ZERO_GROSS_LOSS_POLICY": {"not_rankable"}}
    for k, allowed in enums.items():
        if p.get(k) not in allowed:
            errs.append(f"{k}={p.get(k)!r} not in {sorted(allowed)}")
    if not (0 < p["THRESHOLD_ENTRY"] < 1):
        errs.append("THRESHOLD_ENTRY must be in (0,1)")
    for k in ("H", "N_TRIALS", "EMBARGO_BARS", "PURGE_CANDLES", "W_ATR", "W_VOL", "MIN_TOUCHES"):
        if not (isinstance(p[k], int) and p[k] > 0):
            errs.append(f"{k} must be a positive int")
    for k in ("COMMISSION_BPS", "SLIPPAGE_BPS", "SIMULTANEOUS_SETUP_TIE_EPS"):
        if not (isinstance(p[k], (int, float)) and p[k] >= 0):
            errs.append(f"{k} must be >= 0")
    if not (p["INITIAL_CAPITAL_USD"] > 0):
        errs.append("INITIAL_CAPITAL_USD must be > 0")
    if not (isinstance(p.get("KELLY_CAP"), (int, float)) and 0 < p["KELLY_CAP"] <= 1):
        errs.append("KELLY_CAP must be a number in (0, 1] (no leverage)")
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
        errs.append("ALLOW_PYRAMIDING / ALLOW_REVERSAL_WHILE_OPEN must be false in v1")
    if errs:
        raise RuntimeError("parameter schema validation failed: " + "; ".join(errs))
    return True


# Output B base columns. The FT1–FT8 feature columns are physical base columns here; the per-Asset
# F feature columns (Feature ID >= 9, e.g. log_return_5) splice in ascending-ID order immediately
# BEFORE closed_through_line at runtime via output_b_columns(manifest) (2.3).
OUTPUT_B_BASE_COLUMNS = [
    ("asset_id", "str"), ("direction", "int"), ("setup_id", "setup_id"),
    # P0-1 unified event-time audit: signal_open (open of 1h t0) + decision (close of 1h t0 = the as-of clock) +
    # entry_fill (open of t0+1). All `ts`, none in ALL_FEATURE_NAMES, so none ever enters X.
    ("signal_open_timestamp", "ts"), ("decision_timestamp", "ts"),
    ("entry_fill_timestamp", "ts"), ("distance_to_trend_line", "float"), ("distance_to_opposing_line", "float"),
    ("risk_box_height_pct", "float"), ("bar_return_pct", "float"), ("body_to_range_ratio", "float"),
    ("volume_z_score", "float"), ("touch_count", "int"), ("closed_through_line", "int"),
    ("local_market_exit_reason", "str"), ("local_per_unit_net_return", "float"), ("Y_outcome", "int"),
    ("label_uniqueness_weight", "float"),
]
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


# ============================ 1.6 — snapshot -> clean parquet ============================

def layer1_6_snapshot_to_parquet(db_path, ticker, out_path):
    import duckdb
    con = duckdb.connect(str(db_path), read_only=True)
    df = con.execute("select timestamp, open, high, low, close, volume from bars_1h where ticker=? order by timestamp",
                     [ticker]).fetchdf()
    con.close()
    if df.empty:
        raise RuntimeError(f"1.6 no rows for {ticker}")
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)   # liora.duckdb stores UTC already; no ET localization
    df = (df[["timestamp", "open", "high", "low", "close", "volume"]]
          .astype({"open": float, "high": float, "low": float, "close": float, "volume": float}).reset_index(drop=True))
    # 1.6 source QC — FAIL CLOSED, never silently clean. Corrupt/incomplete source data must STOP the pipeline (the
    # source-ingest control plane is the only place that may repair it); 1.6 only ASSERTS the clean-OHLCV contract.
    # No dropna / drop_duplicates / re-sort: a NaT, duplicate, out-of-order, non-finite or <=0 bar is a contract violation.
    errs = []
    nat = int(df["timestamp"].isna().sum())
    if nat:
        errs.append(f"{nat} unparseable / DST-ambiguous timestamp(s)")
    dups = int(df["timestamp"].duplicated().sum())
    if dups:
        errs.append(f"{dups} duplicate timestamp(s)")
    if not df["timestamp"].is_monotonic_increasing:
        errs.append("timestamps are not strictly increasing")
    o, h, l, c = (df[x].to_numpy(float) for x in ("open", "high", "low", "close"))
    ohlc = df[["open", "high", "low", "close"]].to_numpy()
    if not np.isfinite(ohlc).all() or (ohlc <= 0).any():
        errs.append("non-finite or <= 0 OHLC value(s)")
    # full candle invariants (QC-01..07): a bar must satisfy high>=low and high>=max(open,close) and low<=min(open,close)
    if (h < l).any():
        errs.append(f"{int((h < l).sum())} bar(s) with high < low")
    if (h < np.maximum(o, c)).any():
        errs.append(f"{int((h < np.maximum(o, c)).sum())} bar(s) with high < max(open, close)")
    if (l > np.minimum(o, c)).any():
        errs.append(f"{int((l > np.minimum(o, c)).sum())} bar(s) with low > min(open, close)")
    vol = df["volume"].to_numpy(float)
    if not np.isfinite(vol).all() or (vol < 0).any():
        errs.append("non-finite or negative volume")
    if errs:
        raise RuntimeError(f"1.6 source QC FAILED for {ticker} (lossy cleaning is forbidden — fix upstream "
                           f"source-ingest, not the ML layer): " + "; ".join(errs))
    atomic_write(out_path, lambda p: df.to_parquet(p, engine="pyarrow", compression="zstd", index=False))
    return df


def atomic_write(path, writer):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    writer(tmp)
    os.replace(tmp, path)


# ============================ 1.6 — deterministic 1h -> 1d / 1w roll-up ============================
# 1d / 1w are rolled up ONLY from the same clean 1h parquet: group 1h candles by ET calendar day (-> 1d) and by ISO
# week, Monday-anchored Mon-Sun (-> 1w), then aggregate WHATEVER candles exist (O=first, H=max, L=min, C=last, V=sum).
# No calendar, no holiday list, no completeness gate: a half-day is just a smaller bar; a missing day is simply no bar.
# The parquet stays a pure-OHLCV uncut series (like 1h); the no-cross-segment rule (1.7) is enforced later at feature
# projection, NOT here. close_ts / available_at (the causal as-of key = last source bar's bar_close = open +
# nominal_duration from the temporal contract) ride in-memory, not persisted.

def _utc_series(ts):
    ts = pd.to_datetime(ts)
    return ts.dt.tz_localize("UTC") if ts.dt.tz is None else ts.dt.tz_convert("UTC")


def aggregate_to_timeframe(df_1h, timeframe_id):
    """Plain OHLCV roll-up of the clean 1h parquet to '1d' or '1w'. Returns (df_tf, audit). df_tf carries the pure
    OHLCV columns + the derived causal keys close_ts / available_at. 1d = all 1h candles of an ET calendar day;
    1w = all daily bars of an ISO week (Monday-anchored, Mon-Sun). O=first, H=max, L=min, C=last, V=sum over whatever
    candles/days exist (a half-day -> a smaller bar; a missing day -> no bar). available_at = the last source bar's
    bar_close = open + nominal_duration (the temporal contract; bar_close_timestamp_from_open), never a literal +1h."""
    if timeframe_id not in CONTEXT_TIMEFRAMES:
        raise ValueError(f"aggregate_to_timeframe: unsupported timeframe_id {timeframe_id!r}")
    cols = OHLCV_COLUMNS + ["close_ts", "available_at"]
    utc = _utc_series(df_1h["timestamp"]).reset_index(drop=True)
    et = utc.dt.tz_convert(SESSION_TIMEZONE)
    base = df_1h[["open", "high", "low", "close", "volume"]].reset_index(drop=True).astype(float)
    base["timestamp"] = utc.to_numpy()
    base["_date"] = [d.isoformat() for d in et.dt.date]        # ET calendar day (string key, stable/orderable)
    daily = []
    for _, g in base.groupby("_date", sort=True):
        g = g.sort_values("timestamp")
        close_ts = bar_close_timestamp_from_open(g["timestamp"].iloc[-1])   # complete after its last source bar (contract duration)
        daily.append({"timestamp": g["timestamp"].iloc[0], "open": float(g["open"].iloc[0]),
                      "high": float(g["high"].max()), "low": float(g["low"].min()),
                      "close": float(g["close"].iloc[-1]), "volume": float(g["volume"].sum()),
                      "close_ts": close_ts, "available_at": close_ts, "_date": g["_date"].iloc[0]})
    df_1d = pd.DataFrame(daily)
    if timeframe_id == "1d":
        out = df_1d[cols].reset_index(drop=True) if len(df_1d) else pd.DataFrame(columns=cols)
        return out, {"n_sessions": len(df_1d)}

    # ---- weekly: group the daily bars by ISO week (Monday anchor, Mon-Sun), aggregate whatever days exist ----
    if not len(df_1d):
        return pd.DataFrame(columns=cols), {"n_sessions": 0, "n_weeks": 0}
    df_1d = df_1d.copy()
    df_1d["_wk"] = df_1d["_date"].map(lambda d: "%d-%02d" % pd.Timestamp(d).isocalendar()[:2])   # "isoyear-isoweek" (sorts chronologically)
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


def layer1_6_materialize_timeframes(df_1h, out_paths):
    """Write <T>_ohlcv_1d.parquet + <T>_ohlcv_1w.parquet (each pure OHLCV — close_ts/available_at are derived,
    NOT persisted, so the 1.6 'clean OHLCV, zero derived columns' contract holds for all three timeframes).
    Returns {'1d': df_1d, '1w': df_1w, 'audit': {...}} (the in-memory frames keep close_ts/available_at)."""
    out = {"audit": {}}
    for tf in CONTEXT_TIMEFRAMES:
        df_tf, audit = aggregate_to_timeframe(df_1h, tf)
        pure = df_tf[OHLCV_COLUMNS].copy()
        atomic_write(out_paths[tf], lambda p, d=pure: d.to_parquet(p, engine="pyarrow", compression="zstd", index=False))
        out[tf] = df_tf
        out["audit"][tf] = audit
    return out


# ============================ 1.7 — time split (+ boundary indices) ============================

def layer1_7_split(df):
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


def purge_train_setups(setups, bounds):
    """Remove training setups whose label window [t0, t0+H] (plus embargo) reaches the Train->OOS boundary
    (index-based; the label must not cross into OOS). Returns (kept, n_purged)."""
    H, emb, oos0 = PIPELINE_PARAMETERS["H"], embargo_candles(), bounds["oos_start_idx"]
    kept = [s for s in setups if s["t0"] + H + emb <= oos0]
    # boundary assertion: no kept label window crosses into OOS
    assert all(s["t0"] + H < oos0 for s in kept), "purge boundary assertion failed: label crosses into OOS"
    return kept, len(setups) - len(kept)


def make_segment_of_ts(params=PIPELINE_PARAMETERS):
    """Closure mapping a UTC timestamp -> its time segment {'warmup','train','oos','none'} using the EXACT 1.7
    split boundaries (layer1_7_split). Used by coarse_context_states to DROP a 1d/1w bar that STRADDLES a
    segment boundary (a single bar must not mix segments). The as-of projection itself is causal-only and is
    NOT same-segment-restricted (project_context_asof)."""
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


# ============================ 2.1 — trend-line detector ============================

def _pivots(values, k, kind):
    out = []
    n = len(values)
    for p in range(k, n - k):
        win = values[p - k:p + k + 1]
        if kind == "high" and values[p] == win.max() and win.argmax() == k:
            out.append(p)
        elif kind == "low" and values[p] == win.min() and win.argmin() == k:
            out.append(p)
    return out


def _fit_line(idx, price):
    a, b = np.polyfit(np.asarray(idx, float), np.asarray(price, float), 1)
    return float(a), float(b)


def layer2_1_detect(df, scan_mask):
    H, det = PIPELINE_PARAMETERS["H"], PIPELINE_PARAMETERS["detector"]
    k, lookback, cooldown = det["pivot_k"], det["lookback_candles"], det["cooldown_candles"]
    tol, min_touches = PIPELINE_PARAMETERS["TOUCH_TOL"], PIPELINE_PARAMETERS["MIN_TOUCHES"]
    high, low, close = df["high"].to_numpy(), df["low"].to_numpy(), df["close"].to_numpy()
    atr = wilder_atr(high, low, close, PIPELINE_PARAMETERS["W_ATR"])
    n = len(df)
    ph = [(p + k, p) for p in _pivots(high, k, "high")]
    pl = [(p + k, p) for p in _pivots(low, k, "low")]
    scan_idx = np.where(scan_mask)[0]
    if len(scan_idx) == 0:
        return [], {"det09_rejected": 0, "candidates": 0}
    lo_t0, hi_t0 = int(scan_idx[0]), int(scan_idx[-1])
    setups, det09, cands = [], 0, 0
    cooldown_until = {1: -1, -1: -1}
    for direction in (1, -1):
        trade_piv = ph if direction == 1 else pl
        opp_piv = pl if direction == 1 else ph
        trade_price = high if direction == 1 else low
        opp_price = low if direction == 1 else high
        for t0 in range(max(lo_t0, lookback + k + 1), hi_t0 + 1):
            # only the entry-fill bar t0+1 must exist; the time barrier t0+H may run past the window
            # (the engine forces the final OOS MOC -> OOS_END_FORCED_EXIT). Do NOT drop OOS-tail setups.
            if t0 < 1 or t0 + 1 >= n or t0 <= cooldown_until[direction]:
                continue
            tp = [p for (c_idx, p) in trade_piv if c_idx <= t0 and t0 - lookback <= p <= t0]
            if len(tp) < min_touches:
                continue
            a_t, b_t = _fit_line(tp, trade_price[tp])
            Lt = lambda x: a_t * x + b_t
            touch = [p for p in tp if abs(trade_price[p] - Lt(p)) <= tol * max(EPS, atr[p] if not np.isnan(atr[p]) else EPS)]
            if len(touch) < min_touches:
                continue
            if not (direction * (close[t0] - Lt(t0)) > 0 and direction * (close[t0 - 1] - Lt(t0 - 1)) <= 0):
                continue
            cands += 1
            op = [p for (c_idx, p) in opp_piv if c_idx <= t0 and t0 - lookback <= p <= t0]
            if len(op) < min_touches:
                det09 += 1
                continue
            a_o, b_o = _fit_line(op, opp_price[op])
            R0 = direction * ((a_t * t0 + b_t) - (a_o * t0 + b_o))
            atr0 = atr[t0]
            if atr0 is None or np.isnan(atr0) or atr0 <= 0:
                det09 += 1
                continue
            if R0 <= 0:
                det09 += 1
                continue
            Lt0 = a_t * t0 + b_t
            setups.append({"direction": int(direction), "t0": int(t0), "a_t": a_t, "b_t": b_t,
                           "a_o": a_o, "b_o": b_o, "L_trend_t0": float(Lt0), "L_opp_t0": float(a_o * t0 + b_o),
                           "R0": float(R0), "take_profit_level": float(Lt0 + direction * R0),
                           "atr_t0": float(atr0), "touch_count": int(len(touch)),
                           "time_barrier_candle": int(t0 + H)})
            cooldown_until[direction] = t0 + cooldown
    setups.sort(key=lambda s: (s["t0"], s["direction"]))
    return setups, {"det09_rejected": int(det09), "candidates": int(cands)}


# ============================ shared trade resolver (2.2 label + engine) ============================

def simulate_trade(df, setup, end_idx):
    """Causal Risk-Box trade from t_fill=t0+1 to a pre-submitted scheduled exit. Shared by the 2.2 label and
    the 3.2/4.1 engine. Returns the realized fill path (no fill uses information from its own close)."""
    H, fee, slip = PIPELINE_PARAMETERS["H"], PIPELINE_PARAMETERS["COMMISSION_BPS"] * 1e-4, PIPELINE_PARAMETERS["SLIPPAGE_BPS"] * 1e-4
    s = setup["direction"]
    o, c = df["open"].to_numpy(), df["close"].to_numpy()
    t0, t_fill = setup["t0"], setup["t0"] + 1
    if t_fill > end_idx:
        return {"skip": "GAP_INVALIDATED_SKIP"}
    Lt = lambda x: setup["a_t"] * x + setup["b_t"]
    Lo = lambda x: setup["a_o"] * x + setup["b_o"]
    tp = setup["take_profit_level"]
    entry_fill = o[t_fill] * (1 + s * slip)
    if s * (entry_fill - Lt(t_fill)) <= 0 or s * (entry_fill - Lo(t_fill)) <= 0:
        return {"skip": "GAP_INVALIDATED_SKIP"}
    if s * (tp - entry_fill) <= 0:
        return {"skip": "GAP_TP_SKIP"}
    t_deadline = t0 + H
    t_collapse = None
    for t in range(t_fill, min(t_deadline, end_idx) + 1):
        if s * (Lo(t) - tp) >= 0:
            t_collapse = t
            break
    t_sched = min(t_deadline, end_idx, t_collapse if t_collapse is not None else 10 ** 18)
    exit_idx = exit_fill = reason = kind = trig = None
    for t in range(t_fill, t_sched):
        target_hit = s * (c[t] - tp) >= 0
        safety_hit = s * (c[t] - Lo(t)) <= 0
        if target_hit or safety_hit:
            if t + 1 > end_idx:
                break
            exit_idx, kind, trig = t + 1, "condition", t
            exit_fill = o[t + 1] * (1 - s * slip)
            reason = "TARGET_TRIGGER" if target_hit and not safety_hit else "SAFETY_TRIGGER"
            break
    if exit_idx is None:
        exit_idx, kind, trig = t_sched, "scheduled", t_sched
        exit_fill = c[t_sched] * (1 - s * slip)
        reason = ("OOS_END_FORCED_EXIT" if t_sched == end_idx else
                  "TIME_BARRIER" if t_sched == t_deadline else "RISK_BOX_COLLAPSED")
    per_unit = (s * (exit_fill - entry_fill) - fee * (entry_fill + exit_fill)) / (entry_fill * (1 + fee))
    return {"skip": None, "t_fill": t_fill, "entry_fill": float(entry_fill), "exit_idx": int(exit_idx),
            "exit_fill": float(exit_fill), "market_exit_reason": reason, "exit_kind": kind,
            "trigger_idx": int(trig), "local_per_unit_net_return": float(per_unit),
            "safety_at_entry": float(Lo(t_fill)), "safety_at_trigger": float(Lo(trig))}


# ============================ 2.2 — features + TB_v1.2 label -> Output B ============================

FEATURE_MANIFEST = ["distance_to_trend_line", "distance_to_opposing_line", "risk_box_height_pct",
                    "bar_return_pct", "body_to_range_ratio", "volume_z_score", "touch_count", "direction"]


# ===================== 2.3 — per-Asset feature selection (FT1–FT8 + F) =====================
# FT1–FT8 = Feature IDs 1..8 == FEATURE_MANIFEST (frozen order). Features F = Feature IDs >= 9,
# selected per Asset through config/per_asset_feature_selection.json. resolve_feature_manifest() returns ONE resolved
# manifest object per Asset, threaded 2.2->4.1, hashed into lineage, and snapshotted into the Optuna JSON.
# SOT: Layers_Short_SOT/ENG/Layer2_3_add_features_to_standard_trendlines_features_eng.md.

PER_ASSET_FEATURE_SELECTION_PATH = ROOT / "config" / "per_asset_feature_selection.json"
PER_ASSET_FEATURE_SELECTION = _load_json(PER_ASSET_FEATURE_SELECTION_PATH)

def _load_feature_registry(rel_path):
    """Load a per-timeframe machine registry (Features/features_<tf>/feature_registry.json). Runtime reads ONLY this
    JSON (feature ids / names / reducers / dependency edges), never the Markdown docs."""
    return _load_json(ROOT / rel_path)


# Per-timeframe feature registries (1h source + 1d/1w context), keyed by timeframe_id; order = timeframe_order.
FEATURE_REGISTRIES = {tf: _load_feature_registry(p)
                      for tf, p in PER_ASSET_FEATURE_SELECTION["feature_registry_sources"].items()}
TIMEFRAME_ORDER = list(PER_ASSET_FEATURE_SELECTION["timeframe_order"])
# 2.3.4 between_timeframes — the cross-timeframe alignment registry (Feature IDs 900..999). It is NOT a timeframe
# (no 4th OHLCV, no detector / roll-up): a SEPARATE derived block, deliberately kept OUT of FEATURE_REGISTRIES so the
# per-timeframe contract (exactly 8 standard FT named FEATURE_MANIFEST+suffix) is untouched. None until the cross_timeframe
# config block is present (back-compatible).
_CROSS_TF_CFG = PER_ASSET_FEATURE_SELECTION.get("cross_timeframe")
BETWEEN_TF_REGISTRY = _load_feature_registry(_CROSS_TF_CFG["feature_registry_source"]) if _CROSS_TF_CFG else None

# FT1–FT8 (the 1h standard trendline features) are physical Output-B base columns; every other timeframe's FT/F,
# the 1h additional F and the 2.3.4 cross-TF FT/F splice in before closed_through_line (output_b_columns).
BASE_FEATURE_NAMES = set(FEATURE_MANIFEST)
# Every name that can ever appear as an Output-B MODEL-feature column (all FT + all F across the 3 timeframe
# registries + the 2.3.4 cross-timeframe registry).
ALL_FEATURE_NAMES = set()
for _reg in FEATURE_REGISTRIES.values():
    ALL_FEATURE_NAMES |= {f["name"] for f in _reg["standard_trendline_features"]}
    ALL_FEATURE_NAMES |= {f["name"] for f in _reg["additional_features"]}
# 2.3.4 cross-timeframe model-feature names (FT900..FT908 + F909..F999) — model features (enter X, NaN-allowed like the
# coarse 1d/1w context); their names must avoid the banned calendar/availability tokens (test_mtf_contract).
BETWEEN_TF_FEATURE_NAMES = set()
if BETWEEN_TF_REGISTRY is not None:
    BETWEEN_TF_FEATURE_NAMES = ({f["name"] for f in BETWEEN_TF_REGISTRY["standard_trendline_features"]}
                               | {f["name"] for f in BETWEEN_TF_REGISTRY["additional_features"]})
    ALL_FEATURE_NAMES |= BETWEEN_TF_FEATURE_NAMES
# (timeframe, feature_id) -> column name, so 2.3.4 dependency EDGES resolve to row keys with NO hardcoded ids in code.
_FEATURE_NAME_BY_TF_ID = {tf: {int(f["id"]): f["name"]
                               for f in reg["standard_trendline_features"] + reg["additional_features"]}
                          for tf, reg in FEATURE_REGISTRIES.items()}
# (timeframe, feature_id) -> full base feature def, so the hidden_compute closure can recurse into a dependency's own deps.
_BASE_FEATURE_DEF_BY_TF_ID = {tf: {int(f["id"]): f for f in reg["standard_trendline_features"] + reg["additional_features"]}
                             for tf, reg in FEATURE_REGISTRIES.items()}
# 2.3.4 cross-TF feature definitions (reducer + reducer_params + dependency edges), keyed by feature name.
BETWEEN_TF_FEATURE_DEFS = ({f["name"]: f for f in BETWEEN_TF_REGISTRY["standard_trendline_features"] + BETWEEN_TF_REGISTRY["additional_features"]}
                           if BETWEEN_TF_REGISTRY is not None else {})
# The set of between/derived feature IDs — used by the hidden_compute closure to fail closed on a cross->cross dependency.
BETWEEN_TF_ID_SET = {int(f["id"]) for f in BETWEEN_TF_FEATURE_DEFS.values()}
# 2.3.4 cross-timeframe audit columns (after closed_through_line). Audit-only — EXCLUDED from ALL_FEATURE_NAMES (never X);
# they record per-row source availability so the per-feature >= min_available_sources rule (and the implicit native-missing signal
# the booster may learn) can be verified. _count = #available source TFs; _mask = "1h,1d" etc.; _available = 1 iff the rule held.
BETWEEN_TF_AUDIT_COLUMNS = [("between_timeframes_available_count", "int"),
                           ("between_timeframes_available_mask", "str"),
                           ("between_timeframes_available", "int")]


def _resolve_cross_timeframe(ticker, cfg, per_tf, between_registry):
    """2.3.4 resolve -> the cross-timeframe alignment block, or None when the stage is unconfigured / disabled.
    Fail-closed: a selected F must be implemented + in band [id_base+9, id_base+99]; enabling the block REQUIRES
    >= 1 coarse timeframe (1d/1w) enabled in this same selection (else the cross-TF features are all-NaN dead weight).
    The block is SEPARATE from per_timeframe (it is not a timeframe); its feature_names append AFTER the per-timeframe
    blocks in the effective manifest."""
    ccfg = cfg.get("cross_timeframe")
    if ccfg is None or between_registry is None:
        return None
    overrides = cfg.get("asset_overrides", {})
    sel = overrides.get(ticker, {}).get("between_timeframes") if ticker is not None else None
    if sel is None:
        sel = cfg.get("defaults", {}).get("between_timeframes", {})
    if not sel.get("enabled", False):
        return None
    errs = []
    selected_tfs = [b["timeframe"] for b in per_tf]
    if not any(t in CONTEXT_TIMEFRAMES for t in selected_tfs):
        errs.append("between_timeframes requires >= 1 coarse timeframe (1d/1w) enabled in the same selection")
    base = int(between_registry["id_base"])
    std = between_registry["standard_trendline_features"]
    cat = {int(f["id"]): f for f in between_registry["additional_features"]}
    add, seen = [int(i) for i in sel.get("additional_feature_ids", [])], set()
    for i in add:
        if not (base + 9 <= i <= base + 99):
            errs.append(f"between_timeframes: Feature ID {i} not in additional band [{base+9},{base+99}]")
        if i in seen:
            errs.append(f"between_timeframes: duplicate Feature ID {i}")
        seen.add(i)
        if i not in cat:
            errs.append(f"between_timeframes: Feature ID {i} absent from registry")
        elif not bool(cat[i].get("implemented", False)):
            errs.append(f"between_timeframes: Feature ID {i} is implemented=false")
    if errs:
        raise RuntimeError(f"feature_selection resolve failed for ticker={ticker!r}: " + "; ".join(errs))
    valid = [i for i in sorted(add) if i in cat and bool(cat[i].get("implemented", False))]
    source_tfs = list(ccfg.get("source_timeframes", []))
    return {"stage": "2.3.4", "enabled": True, "id_base": base, "standard_count": len(std),
            "source_timeframes": source_tfs,
            "selected_source_timeframes": [t for t in selected_tfs if t in source_tfs],
            "max_source_age_hours": dict(ccfg.get("max_source_age_hours", {})),
            "feature_ids": [int(f["id"]) for f in std] + valid,
            "feature_names": [f["name"] for f in std] + [cat[i]["name"] for i in valid]}


def resolve_feature_manifest(ticker=None, cfg=None, registries=None, between_registry=None):
    """2.3 resolve -> effective_feature_manifest_v3 (one object per Asset). For each ENABLED timeframe in
    timeframe_order: all 8 standard trendline features + the selected additional features (implemented=true).
    Then the 2.3.4 between_timeframes block (cross-timeframe alignment FT900..FT908 + selected F), when enabled.
    Model-input X order = timeframe order (then Feature-ID within a timeframe), then the cross_timeframe block.
    ticker=None resolves the global default (no override lookup). Fail-closed on any invalid selection. Default ->
    exactly [FT1..FT8, F9] (1h only; 1d/1w/between_timeframes disabled), byte-identical model input to the pre-MTF baseline."""
    cfg = PER_ASSET_FEATURE_SELECTION if cfg is None else cfg
    registries = FEATURE_REGISTRIES if registries is None else registries
    between_registry = BETWEEN_TF_REGISTRY if between_registry is None else between_registry
    order = cfg["timeframe_order"]
    overrides = cfg.get("asset_overrides", {})
    per_tf, errs = [], []
    for tf in order:
        reg = registries[tf]
        ov = overrides.get(ticker, {}).get(tf) if ticker is not None else None
        sel = ov if ov is not None else cfg["defaults"][tf]
        if not sel.get("enabled", False):
            continue
        base = int(reg["id_base"])
        cat = {int(f["id"]): f for f in reg["additional_features"]}
        add, seen = [int(i) for i in sel.get("additional_feature_ids", [])], set()
        for i in add:
            if not (base + 9 <= i <= base + 99):
                errs.append(f"{tf}: Feature ID {i} not in additional band [{base+9},{base+99}]")
            if i in seen:
                errs.append(f"{tf}: duplicate Feature ID {i}")
            seen.add(i)
            if i not in cat:
                errs.append(f"{tf}: Feature ID {i} absent from registry")
            elif not bool(cat[i].get("implemented", False)):
                errs.append(f"{tf}: Feature ID {i} is implemented=false")
        # build only from valid selections (errs, if any, raise after the loop — the partial manifest is discarded);
        # guarding here avoids a KeyError on an absent id masking the collected fail-closed messages.
        valid = [i for i in sorted(add) if i in cat and bool(cat[i].get("implemented", False))]
        std = reg["standard_trendline_features"]
        per_tf.append({"timeframe": tf, "id_base": base, "column_suffix": reg["column_suffix"],
                       "standard_count": len(std),
                       "feature_ids": [int(f["id"]) for f in std] + valid,
                       "feature_names": [f["name"] for f in std] + [cat[i]["name"] for i in valid]})
    if errs:
        raise RuntimeError(f"feature_selection resolve failed for ticker={ticker!r}: " + "; ".join(errs))
    cross = _resolve_cross_timeframe(ticker, cfg, per_tf, between_registry)   # 2.3.4 block (None when disabled)
    eff_ids = [i for b in per_tf for i in b["feature_ids"]] + (cross["feature_ids"] if cross else [])
    eff_names = [n for b in per_tf for n in b["feature_names"]] + (cross["feature_names"] if cross else [])
    manifest = {
        "schema_version": cfg.get("schema_version", "layer2_3.v3"),
        "timeframe_order": list(order),
        "selected_timeframes": [b["timeframe"] for b in per_tf],
        "per_timeframe": per_tf,
        "effective_feature_ids": eff_ids,
        "effective_feature_names": eff_names,
        "effective_feature_count": len(eff_ids),
        "feature_selection_source": "config/per_asset_feature_selection.json",
    }
    if cross is not None:                                  # 2.3.4 carried as a SEPARATE manifest block (not in per_timeframe)
        manifest["cross_timeframe"] = cross
    return manifest


def output_b_columns(manifest):
    """Resolved Output-B (col, type) layout. The 1h FT1–FT8 are physical base columns; every OTHER model-feature
    column (1h additional F, then 1d FT+F, then 1w FT+F — timeframe then Feature-ID order) splices in immediately
    before closed_through_line. The audit-only context columns (per enabled coarse timeframe) append AFTER
    closed_through_line, outside the model-feature region (never in X / the DMatrix)."""
    feat_cols, ctx_cols = [], []
    for b in manifest["per_timeframe"]:
        feat_cols += [(nm, "float") for nm in b["feature_names"] if nm not in BASE_FEATURE_NAMES]
        if b["timeframe"] in CONTEXT_TIMEFRAMES:
            tf = b["timeframe"]
            ctx_cols += [(f"context_{tf}_timestamp", "ts"), (f"context_{tf}_age_hours", "float"),
                         (f"context_{tf}_available", "int")]
    cross = manifest.get("cross_timeframe")               # 2.3.4 block: feature cols splice AFTER 1h/1d/1w, still before
    if cross is not None:                                  # closed_through_line; its 3 audit cols append after context audit.
        feat_cols += [(nm, "float") for nm in cross["feature_names"]]
    out = []
    for c, t in OUTPUT_B_BASE_COLUMNS:
        if c == "closed_through_line":
            out.extend(feat_cols)
        out.append((c, t))
    out.extend(ctx_cols)
    if cross is not None:
        out.extend(list(BETWEEN_TF_AUDIT_COLUMNS))
    return out


def feature_names_of(manifest=None):
    """Model-input feature order (Feature-ID order) for a resolved manifest; the global default if None."""
    return (manifest or DEFAULT_FEATURE_MANIFEST)["effective_feature_names"]


DEFAULT_FEATURE_MANIFEST = resolve_feature_manifest(None)


def _features_at(df, setup, atr, vmean, vstd):
    # Missingness contract (00_conventions "MTF / NaN data-plane contract"): a feature that is UNDEFINED
    # from insufficient lookback history -> NaN (the 2.2 eligibility gate excludes the row; never imputed).
    # A flat-but-DEFINED degenerate case -> 0.0 ONLY as an explicit documented convention. ATR at t0 is
    # > 0 for every DETECTED setup (DET-09 rejects zero/NaN ATR); pre-window ATR is NaN -> NaN distances
    # -> row excluded. Prices are > 0 by the source contract (upstream QC-06). For real post-warmup setups
    # none of the NaN branches fire, so the default Output B is byte-identical.
    t, s = setup["t0"], setup["direction"]
    c, o, h, l, v = (df[x].to_numpy() for x in ("close", "open", "high", "low", "volume"))
    Lt, Lo = setup["L_trend_t0"], setup["L_opp_t0"]
    atr_t = atr[t]
    sd = vstd[t]
    return {"distance_to_trend_line": s * (c[t] - Lt) / atr_t,
            "distance_to_opposing_line": s * (c[t] - Lo) / atr_t,
            "risk_box_height_pct": 100.0 * setup["R0"] / max(EPS, abs(Lt)),
            # t==0 lacks a previous bar -> undefined -> NaN (excluded); prev close is > 0 by contract.
            "bar_return_pct": ((c[t] - c[t - 1]) / c[t - 1] * 100.0) if t >= 1 else float("nan"),
            # flat bar (high==low) -> 0.0 by explicit convention (a defined zero body ratio, not "missing").
            "body_to_range_ratio": (abs(c[t] - o[t]) / (h[t] - l[t])) if h[t] != l[t] else 0.0,
            # vol std NaN = pre-window (insufficient history) -> NaN (excluded); std==0 (flat volume over a
            # full window) -> 0.0 by explicit convention; else the z-score.
            "volume_z_score": (float("nan") if np.isnan(sd) else (0.0 if sd == 0 else (v[t] - vmean[t]) / sd)),
            "touch_count": int(setup["touch_count"]), "direction": int(s),
            # F9 log_return_5: causal 5-bar log-return; t<5 = insufficient history -> NaN (a mandatory 1h
            # feature, so the row is excluded by 2.2 eligibility, never imputed to 0.0). Prices are > 0.
            "log_return_5": float(np.log(c[t] / c[t - 5])) if t >= 5 else float("nan"),
            "closed_through_line": 1 if s * (c[t] - Lt) > 0 else 0}


# ===================== 2.3.2 / 2.3.3 — coarse 1d / 1w completed-bar context + causal as-of projection =====================
# The coarse timeframe produces COMPLETED-BAR trendline state only: the same 2.1 detector + _features_at run over
# completed 1d / 1w bars (no trade, no Y, no entry order). Each coarse setup becomes available at its bar's close_ts;
# it is projected as-of onto a 1h setup (the latest coarse state with available_at <= the 1h decision_timestamp; causal-only,
# Missing 1d/1w context -> NaN (XGBoost treats NaN as native missing and learns the split direction; no drop, no flag).

def coarse_context_states(df_tf, suffix, segment_of_ts):
    """Run the 2.1 detector over completed coarse bars -> for every coarse setup, the 8 standard trendline
    features + log_return_5 (suffixed), its available_at (the bar's close_ts) and its segment. Coarse bars that
    straddle a Train/Validation/OOS boundary (open vs close in different segments) are dropped (audited). Returns
    (states_df sorted by available_at, audit). Reuses wilder_atr / rolling_mean_std / layer2_1_detect / _features_at."""
    feat_cols = [n + suffix for n in FEATURE_MANIFEST] + ["log_return_5" + suffix]
    audit = {"n_setups": 0, "n_straddle_dropped": 0}
    empty = pd.DataFrame(columns=["available_at", "segment"] + feat_cols)
    if df_tf is None or len(df_tf) <= PIPELINE_PARAMETERS["W_ATR"]:
        return empty, audit
    high, low, close, vol = (df_tf[x].to_numpy() for x in ("high", "low", "close", "volume"))
    atr = wilder_atr(high, low, close, PIPELINE_PARAMETERS["W_ATR"])
    vmean, vstd = rolling_mean_std(vol, PIPELINE_PARAMETERS["W_VOL"])
    setups, _ = layer2_1_detect(df_tf, np.ones(len(df_tf), dtype=bool))
    ts_open = pd.to_datetime(df_tf["timestamp"]).reset_index(drop=True)
    ts_close = pd.to_datetime(df_tf["close_ts"]).reset_index(drop=True)
    rows = []
    for st in setups:
        t0 = st["t0"]
        if segment_of_ts(ts_open.iloc[t0]) != segment_of_ts(ts_close.iloc[t0]):   # coarse bar straddles a segment
            audit["n_straddle_dropped"] += 1
            continue
        f = _features_at(df_tf, st, atr, vmean, vstd)
        row = {"available_at": ts_close.iloc[t0], "segment": segment_of_ts(ts_close.iloc[t0])}
        for n in FEATURE_MANIFEST:
            row[n + suffix] = f[n]
        row["log_return_5" + suffix] = f["log_return_5"]
        rows.append(row)
        audit["n_setups"] += 1
    states = pd.DataFrame(rows, columns=["available_at", "segment"] + feat_cols)
    if len(states):
        states = states.sort_values("available_at").reset_index(drop=True)
    return states, audit


def build_context_states(df, manifest, segment_of_ts=None):
    """For each ENABLED coarse timeframe in the manifest: materialize the coarse OHLCV (aggregate_to_timeframe)
    then coarse_context_states -> the as-of-projectable state frame. Returns {tf: states_df}. Empty dict when no
    coarse timeframe is enabled -> the default 1h-only path does NO extra work (byte-identical to pre-MTF)."""
    segment_of_ts = segment_of_ts or make_segment_of_ts()
    states = {}
    for b in manifest["per_timeframe"]:
        if b["timeframe"] in CONTEXT_TIMEFRAMES:
            df_tf, _ = aggregate_to_timeframe(df, b["timeframe"])
            states[b["timeframe"]], _ = coarse_context_states(df_tf, b["column_suffix"], segment_of_ts)
    return states


def project_context_asof(signal_ts, states, suffix, out_names):
    """As-of projection for ONE 1h setup and ONE coarse timeframe: the latest coarse state with
    available_at <= signal_ts (CAUSAL). NO same-segment restriction — a coarse state completed before the signal
    is causal even when it formed in the prior Train/OOS segment, so it carries legitimate point-in-time context
    (segment governs labels/purge/embargo/CV/fit/eval, not historical feature warm-up; a coarse bar that
    STRADDLES a segment boundary is already dropped in coarse_context_states). Returns the requested suffixed
    feature values + the audit triplet context_<tf>_{timestamp,age_hours,available}. No qualifying state -> NaN
    features + age_hours NaN + available=0 (XGBoost native missing; never a future bar)."""
    tf = suffix.lstrip("_")
    res = {n: float("nan") for n in out_names}
    # age_hours unavailable = NaN (audit-only, not in X): 0.0 would alias "context formed exactly now".
    res.update({f"context_{tf}_timestamp": pd.NaT, f"context_{tf}_age_hours": float("nan"), f"context_{tf}_available": 0})
    if states is None or not len(states):
        return res
    elig = states[states["available_at"] <= pd.Timestamp(signal_ts)]
    if not len(elig):
        return res
    row = elig.iloc[-1]                                                    # states are sorted by available_at
    for n in out_names:
        res[n] = float(row[n])
    av = pd.Timestamp(row["available_at"])
    res[f"context_{tf}_timestamp"] = av
    res[f"context_{tf}_age_hours"] = float((pd.Timestamp(signal_ts) - av).total_seconds() / 3600.0)
    res[f"context_{tf}_available"] = 1
    return res


def _hidden_compute_closure(manifest):
    """RECURSIVE closure (P1-a) of coarse feature NAMES required — transitively — by the selected 2.3.4 cross features
    but NOT themselves selected model features. Materialised into the compute row so the kernels can read them, yet never
    in X / Output B (a required dependency is hidden iff it is not a selected model feature). FAIL-CLOSED on cross->cross:
    a cross feature may depend only on BASE 1h/1d/1w features; if a dependency id is itself a between/derived feature the
    closure raises (the runtime resolves only base coarse state — cross->cross is a documented future extension, never
    silently wrong). Base 1h/1d/1w features are primitive (no further edges), so the recursion terminates."""
    cross = manifest.get("cross_timeframe")
    if not cross:
        return {}
    selected_by_tf = {b["timeframe"]: set(b["feature_names"]) for b in manifest["per_timeframe"]}
    hidden, seen = {}, set()

    def _visit(defn):
        for e in defn["dependencies"].get("source_feature_requirements", []):
            tf, fid = e["timeframe"], int(e["feature_id"])
            if fid in BETWEEN_TF_ID_SET:                  # cross -> cross dependency: unsupported, fail closed
                raise RuntimeError(f"between_timeframes feature {defn['id']} depends on between feature {fid} "
                                   "(cross->cross dependencies are not supported)")
            key = (tf, fid)
            if key in seen:
                continue
            seen.add(key)
            if tf in CONTEXT_TIMEFRAMES and tf in selected_by_tf:
                colname = _FEATURE_NAME_BY_TF_ID.get(tf, {}).get(fid)
                if colname and colname not in selected_by_tf[tf]:
                    hidden.setdefault(tf, set()).add(colname)
            base_def = _BASE_FEATURE_DEF_BY_TF_ID.get(tf, {}).get(fid)   # recurse (base FT are primitive -> terminates)
            if base_def is not None:
                _visit(base_def)

    for nm in cross["feature_names"]:
        _visit(BETWEEN_TF_FEATURE_DEFS[nm])
    return hidden


def _project_all_context(signal_ts, manifest, context_states):
    """Project every enabled coarse timeframe for one 1h setup, into the COMPUTE row. Returns (feature_values,
    audit_columns) — empty dicts when no coarse timeframe is enabled (the default path). The projected names are the
    SELECTED coarse model features PLUS any hidden_compute coarse dependencies of selected 2.3.4 cross features; the
    hidden ones ride in compute_row for the kernels but are dropped from model X / Output B (they are not in
    effective_feature_names / output_b_columns)."""
    feats, audit = {}, {}
    if not context_states:
        return feats, audit
    hidden = _hidden_compute_closure(manifest)
    for b in manifest["per_timeframe"]:
        tf = b["timeframe"]
        if tf not in CONTEXT_TIMEFRAMES:
            continue
        out_names = list(b["feature_names"]) + sorted(hidden.get(tf, set()) - set(b["feature_names"]))
        proj = project_context_asof(signal_ts, context_states.get(tf), b["column_suffix"], out_names)
        for n in out_names:
            feats[n] = proj[n]
        for k in (f"context_{tf}_timestamp", f"context_{tf}_age_hours", f"context_{tf}_available"):
            audit[k] = proj[k]
    return feats, audit


# ===================== 2.3.4 — between_timeframes (cross-timeframe alignment; setup-level, no 4th OHLCV) =====================
# Computed from the ALREADY-RESOLVED setup row (1h base + causal as-of 1d/1w context). A pure function of already-causal
# inputs -> causal by construction (no new data access, no look-ahead). >= per-feature min_available_sources available+fresh sources
# required, else NaN (no imputation; the setup is never dropped). NaN is a legitimate native-missing signal the tree booster
# may learn (implicit availability) — NOT look-ahead; the between_timeframes_available_* AUDIT columns let it be verified.

# ---- 2.3.4 reducer kernel library (the ONLY math the runtime applies; selected per feature by registry `reducer`) ----
# Each kernel takes the feature-locally valid edge values + the feature's reducer_params + its min_available_sources.
def _reducer_mean(vals, params, minreq):
    return sum(vals) / len(vals)


def _reducer_abs_mean(vals, params, minreq):
    return abs(sum(vals) / len(vals))


def _reducer_sign_alignment(vals, params, minreq):          # |mean(sign(v))| in [0,1]; sign(0)=0
    signs = [(1.0 if v > 0 else (-1.0 if v < 0 else 0.0)) for v in vals]
    return abs(sum(signs) / len(signs))


def _reducer_min_max_ratio(vals, params, minreq):           # min/max of the POSITIVE values; <=0 rejected (no epsilon)
    pos = [v for v in vals if v > 0]
    return (min(pos) / max(pos)) if len(pos) >= minreq else float("nan")


def _reducer_norm_mean(vals, params, minreq):               # mean(v / normalizer); normalizer is a PIPELINE_PARAMETERS key
    # P1-d: fail closed — a missing normalizer key, or a non-finite / non-positive normalizer, is a configuration error,
    # NOT something to silently paper over with z=1.0 (which would change the feature's scale without anyone noticing).
    if "normalizer" not in params:
        raise RuntimeError("norm_mean reducer requires reducer_params.normalizer (a PIPELINE_PARAMETERS key)")
    z = float(PIPELINE_PARAMETERS[params["normalizer"]])
    if not (math.isfinite(z) and z > 0):
        raise RuntimeError(f"norm_mean normalizer {params['normalizer']!r} must be finite and > 0, got {z}")
    return sum(v / z for v in vals) / len(vals)


REDUCERS = {"mean": _reducer_mean, "abs_mean": _reducer_abs_mean, "sign_alignment": _reducer_sign_alignment,
            "min_max_ratio": _reducer_min_max_ratio, "norm_mean": _reducer_norm_mean}


def cross_timeframe_features(x, audit, manifest):
    """2.3.4 cross-timeframe alignment for ONE already-resolved setup row, fully REGISTRY-DRIVEN (no hardcoded
    feature-id branches): for each selected cross feature the runtime reads its dependency EDGES + `reducer` from the
    Feature Knowledge Base and applies REDUCERS[reducer]. Returns {} when the stage is disabled (default -> byte-identical).
    FEATURE-LOCAL availability (P0-3): a source timeframe contributes to feature F only when it is a selected source, its
    context is fresh (age <= max_source_age_hours), AND F's edge value for that TF is finite (math.isfinite). Each feature
    requires >= its own min_available_sources finite edge values, else NaN (no imputation; the setup is never dropped). NO
    row-fabrication primitive (no re-indexing / re-sampling / gap-filling): explicit masking only. The '_audit' key carries
    the between_timeframes_available_* GENERAL context-availability columns (never model X)."""
    cross = manifest.get("cross_timeframe")
    if cross is None:
        return {}
    max_age = cross.get("max_source_age_hours", {})
    selected_sources = set(cross.get("selected_source_timeframes", []))

    def _tf_valid(tf):                                       # general TF validity: 1h always; coarse = selected + fresh
        if tf == "1h":
            return True
        if tf not in selected_sources:
            return False
        lim = max_age.get(tf)
        age = audit.get(f"context_{tf}_age_hours", float("nan"))
        return (lim is None) or (math.isfinite(age) and age <= float(lim))

    valid_tfs = [tf for tf in cross.get("source_timeframes", []) if _tf_valid(tf)]
    n_avail = len(valid_tfs)
    defs = BETWEEN_TF_FEATURE_DEFS
    audit_min = min((int(defs[nm]["dependencies"].get("min_available_sources", 2)) for nm in cross["feature_names"]),
                    default=2)
    feats = {}
    for nm in cross["feature_names"]:
        fdef = defs.get(nm)
        if fdef is None:
            raise RuntimeError(f"between_timeframes feature {nm!r} absent from the Feature Knowledge Base registry")
        reducer = REDUCERS.get(fdef["reducer"])
        if reducer is None:
            raise RuntimeError(f"between_timeframes feature {nm!r} reducer {fdef['reducer']!r} not in REDUCERS")
        dep = fdef["dependencies"]
        minreq = int(dep.get("min_available_sources", 2))
        # P0-6: iterate the CANONICAL source order (config.cross_timeframe.source_timeframes), NOT the JSON edge order,
        # so a reordering of this feature's source_feature_requirements in the registry can never change the float
        # summation order (and thus the last bits of the reducer output). edge_by_tf is well-defined because P1-b
        # forbids >1 edge per timeframe.
        edge_by_tf = {e["timeframe"]: e for e in dep.get("source_feature_requirements", [])}
        vals = []
        for tf in cross.get("source_timeframes", []):
            e = edge_by_tf.get(tf)
            if e is None or not _tf_valid(tf):
                continue
            colname = _FEATURE_NAME_BY_TF_ID.get(tf, {}).get(int(e["feature_id"]))
            v = float(x.get(colname, float("nan"))) if colname else float("nan")
            if math.isfinite(v):                            # feature-LOCAL: this edge's value must be finite
                vals.append(v)
        feats[nm] = float(reducer(vals, fdef.get("reducer_params", {}), minreq)) if len(vals) >= minreq else float("nan")
    feats["_audit"] = {"between_timeframes_available_count": int(n_avail),
                       "between_timeframes_available_mask": ",".join(valid_tfs),
                       "between_timeframes_available": 1 if n_avail >= audit_min else 0}
    return feats


# The unified event-time contract (bar_open_timestamp / bar_close_timestamp / decision_timestamp_of_setup +
# condition_trigger_timestamp / scheduled_exit_timestamp) lives in contracts/temporal_contract.py and is imported at the
# top of this module — the ONLY source of every Output-B / trade-ledger / equity-event wall-clock.


def assemble_setup_x(df, setup, atr, vmean, vstd, manifest, context_states):
    """The SINGLE feature-vector assembler shared by 2.2 Output B and Train/OOS scoring, so X is identical everywhere:
    1h base (_features_at) + causal as-of 1d/1w context + 2.3.4 cross-timeframe alignment. Returns (x, audit): x holds
    every model / Output-B feature value; audit holds the context_* triplet + between_timeframes_available_* columns.
    Default (no coarse, no cross) -> x == _features_at, audit == {} (byte-identical to the pre-MTF / pre-2.3.4 path)."""
    base = _features_at(df, setup, atr, vmean, vstd)
    signal_ts = decision_timestamp_of_setup(df, setup["t0"]) if context_states else None   # close of 1h t0 (P0-1)
    context, audit = _project_all_context(signal_ts, manifest, context_states)
    x = {**base, **context}
    cross = cross_timeframe_features(x, audit, manifest)
    if cross:
        caud = cross.pop("_audit", {})
        x.update(cross)
        audit = {**audit, **caud}
    return x, audit


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


def mandatory_core_feature_names(manifest):
    """The mandatory 1h-core feature names from the resolved manifest. A setup row is INELIGIBLE until all
    of these are finite (the 2.2 eligibility gate excludes it; never imputes). Covers FT1–FT8 + any selected
    1h Feature F; the optional 1d/1w coarse context is deliberately excluded (it may be NaN in X)."""
    for block in manifest["per_timeframe"]:
        if block["timeframe"] == "1h":
            names = list(block["feature_names"])
            if not names:   # a present-but-empty block -> isnan([]).any()==False would silently pass every setup
                raise RuntimeError("resolved manifest has an empty mandatory 1h feature block")
            return names
    raise RuntimeError("resolved manifest has no mandatory 1h feature block")   # never silently all([])==True


def core_feature_eligibility(features, manifest):
    """Single eligibility predicate for BOTH Output B (2.2) and Train/OOS scoring. Returns the EXCLUSION REASON
    ('nan' | 'inf') when a mandatory 1h-core feature is non-finite, else None (eligible). Undefined mandatory
    features (insufficient warm-up history) are NaN -> the row/setup is excluded by EXCLUSION, never imputed."""
    values = np.asarray([features[n] for n in mandatory_core_feature_names(manifest)], dtype=float)
    if np.isnan(values).any():
        return "nan"
    if np.isinf(values).any():
        return "inf"
    return None


def layer2_2_output_b(df, setups, ticker, end_idx, manifest=None, context_states=None):
    """Build Output B; returns (df_b, eligibility_audit). The 2.2 eligibility gate (the shared
    core_feature_eligibility predicate, BEFORE simulate_trade — an ineligible row needs no label/cost) excludes
    a setup whose mandatory 1h-core feature is non-finite, by EXCLUSION not imputation. For real post-warmup
    setups all core features are finite -> 0 excluded (byte-identical default)."""
    manifest = manifest or resolve_feature_manifest(ticker)
    high, low, close, vol = (df[x].to_numpy() for x in ("high", "low", "close", "volume"))
    atr = wilder_atr(high, low, close, PIPELINE_PARAMETERS["W_ATR"])
    vmean, vstd = rolling_mean_std(vol, PIPELINE_PARAMETERS["W_VOL"])
    eligibility = {"core_nan_excluded": 0, "core_inf_excluded": 0}
    rows, actionable = [], []
    for st in setups:
        sid = f"{ticker}:{st['t0']}:{st['direction']}"
        feats, aud = assemble_setup_x(df, st, atr, vmean, vstd, manifest, context_states)   # 1h + 1d/1w + 2.3.4
        reason = core_feature_eligibility(feats, manifest)
        if reason is not None:
            eligibility[f"core_{reason}_excluded"] += 1
            continue
        sim = simulate_trade(df, st, end_idx)
        if sim["skip"] is not None:
            continue
        rows.append({"asset_id": ticker, "setup_id": sid,
                     "signal_open_timestamp": bar_open_timestamp(df, st["t0"]),         # open of 1h t0
                     "decision_timestamp": decision_timestamp_of_setup(df, st["t0"]),    # close of 1h t0 (the as-of clock)
                     "entry_fill_timestamp": bar_open_timestamp(df, sim["t_fill"]), **feats, **aud,
                     "local_market_exit_reason": sim["market_exit_reason"],
                     "local_per_unit_net_return": sim["local_per_unit_net_return"],
                     "Y_outcome": 1 if sim["local_per_unit_net_return"] > 0 else 0})
        actionable.append({"setup_id": sid, "t_fill": sim["t_fill"],
                           "t_end": min(st["t0"] + PIPELINE_PARAMETERS["H"], end_idx)})
    weights = _uniqueness_weights(actionable)
    for r in rows:
        r["label_uniqueness_weight"] = weights.get(r["setup_id"], 1.0)
    cols = [c for c, _ in output_b_columns(manifest)]
    df_b = pd.DataFrame(rows, columns=cols) if rows else pd.DataFrame(columns=cols)
    return df_b, eligibility


# ============================ 3.1 — Optuna (AUC-PR, purged WF CV by candle index) ============================

def average_precision(y, score):
    """Tie-invariant AP: evaluate precision/recall only at unique-score thresholds (the last index of each
    tie group), so identical prediction scores never make the result depend on row order."""
    y = np.asarray(y, int); score = np.asarray(score, float)
    pos = int(y.sum())
    if pos == 0:
        return 0.0
    order = np.argsort(-score, kind="mergesort")
    y, s = y[order], score[order]
    tp = np.cumsum(y); fp = np.cumsum(1 - y)
    grp = np.r_[np.where(np.diff(s) != 0)[0], len(s) - 1]   # last index of each equal-score group
    recall = tp[grp] / pos
    precision = tp[grp] / np.maximum(1, tp[grp] + fp[grp])
    rprev = np.r_[0.0, recall[:-1]]
    return float(np.sum((recall - rprev) * precision))


def purged_wf_folds(t0s, train_start_idx, train_end_idx, k=CV_FOLDS):
    """True purged WALK-FORWARD CV by candle index: k+1 contiguous segments; validation = segments 1..k;
    training for each validation block uses ONLY setups whose label window ends strictly before the block
    (minus the embargo) — never future data. The first segment is history-only (no fold)."""
    H, emb = PIPELINE_PARAMETERS["H"], embargo_candles()
    edges = np.linspace(train_start_idx, train_end_idx + 1, k + 2, dtype=int)   # k+1 segments
    folds = []
    for i in range(1, k + 1):
        val_lo, val_hi = int(edges[i]), int(edges[i + 1])
        val = [j for j, t0 in enumerate(t0s) if val_lo <= t0 < val_hi]
        cutoff = val_lo - emb
        tr = [j for j, t0 in enumerate(t0s) if t0 + H < cutoff]   # strictly earlier (+embargo) => walk-forward
        if len(val) >= 5 and len(tr) >= 10:
            folds.append((tr, val))
    return folds


def _xgb_train(X, y, w, params, seed, feature_names=None):
    import xgboost as xgb
    d = xgb.DMatrix(X, label=y, weight=w, feature_names=feature_names or FEATURE_MANIFEST)
    # booster PINNED to a TREE learner: the linear booster treats missing values as 0, which would silently
    # break the 2.3 native-NaN coarse-context contract. gbtree is xgboost's default, so this pin is byte-identical.
    p = {"objective": "binary:logistic", "eval_metric": "aucpr", "seed": seed, "booster": "gbtree",
         "nthread": PIPELINE_PARAMETERS["XGBOOST_N_JOBS"], "max_depth": params["max_depth"], "eta": params["eta"],
         "subsample": params["subsample"], "colsample_bytree": params["colsample_bytree"],
         "min_child_weight": params["min_child_weight"], "lambda": params["reg_lambda"], "verbosity": 0}
    return xgb.train(p, d, num_boost_round=params["n_estimators"])


def layer3_1_optuna(df_b, bounds, seed, manifest=None, trials=None):
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
        return dict(XGBOOST_OPTUNA_SEARCH_SPACE["fallback_params"]), 0.0, len(folds)   # registry SOT, not a hardcoded vector

    def objective(trial):
        # Built from config/xgboost_optuna_search_space.json (single SOT) in FROZEN_DATA_STATE_NUMBERS ORDER — preserving the suggest_* call
        # order keeps the TPE sequence deterministic at a fixed seed (same registry → same best_params).
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

    # direction is sourced from the registry (the SOT); sampler/pruner/metric/cv_scheme are pinned to it by
    # validate_xgb_optuna_space() (SUPPORTED_OBJECTIVE), so the registry and runtime can never silently drift.
    study = optuna.create_study(direction=XGBOOST_OPTUNA_SEARCH_SPACE["objective"]["direction"],
                                sampler=optuna.samplers.TPESampler(seed=seed),
                                pruner=optuna.pruners.MedianPruner(n_warmup_steps=MEDIAN_PRUNER_WARMUP))
    study.optimize(objective, n_trials=trials, show_progress_bar=False)
    best = dict(study.best_params)
    best.setdefault("n_estimators", 100)
    return best, float(study.best_value), len(folds)


def calibrate_kelly(df, df_b, train_setups, bounds, best_params, seed, manifest=None):
    """Layer 3.1b — per-asset fractional-Kelly calibration (Train only; OOS is NEVER read). Picks lambda (the
    fractional-Kelly multiplier) by MAXIMIZING Train OUT-OF-FOLD geometric log-growth: for each purged walk-forward
    fold a fold model (the SAME best XGB params, seeded) scores that fold's validation setups out-of-fold, then the
    SAME run_engine is run over the fold's validation candle span with per-trade Kelly(lambda); the objective is
    sum_folds log(end_capital / E0). A dedicated 1-D Optuna study with a deterministic GridSampler over
    KELLY_CALIBRATION returns the best lambda (ties -> smallest, most conservative). The caller stores it in
    best_params['kelly_fraction'] (rides into the OPTUNAs json + strategy file; inert in _xgb_train)."""
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
        return float(kc["low"])                            # no folds -> defined conservative default (mirrors 3.1 fallback)
    ticker = str(df_b["asset_id"].iloc[0])
    by_sid = {f"{ticker}:{s['t0']}:{s['direction']}": s for s in train_setups}   # df_b is a FILTERED subsequence -> map by id
    fold_data = []                                         # (scored_oof, val_lo, val_hi) built ONCE; lambda sweep reuses it
    for tr, va in folds:
        if len(np.unique(y[tr])) < 2:
            continue
        bst = _xgb_train(X[tr], y[tr], w[tr], best_params, seed, feature_names=names)
        oof = bst.predict(xgb.DMatrix(X[va], feature_names=names))
        scored = [(by_sid[df_b["setup_id"].iloc[j]], float(oof[k])) for k, j in enumerate(va)]
        vt0 = [t0s[j] for j in va]
        fold_data.append((scored, min(vt0), max(vt0)))     # run_engine filters start<=t0<=end -> only the OOF val setups
    if not fold_data:
        return float(kc["low"])
    assert all(hi < bounds["oos_start_idx"] for _, _, hi in fold_data), "Kelly calibration must not reach OOS"

    def objective(trial):
        lam = trial.suggest_float("kelly_fraction", kc["low"], kc["high"])   # GridSampler snaps to the grid
        g = 0.0
        for scored, lo, hi in fold_data:
            summ, _, _ = run_engine(df, scored, lo, hi, thr, kelly_fraction=lam)
            g += math.log(max(summ["end_capital"], EPS) / E0)               # guard depleted folds (end_capital<=0)
        return g

    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize",
                                sampler=optuna.samplers.GridSampler({"kelly_fraction": grid}))
    study.optimize(objective, n_trials=len(grid), show_progress_bar=False)
    bv = study.best_value
    tied = [t.params["kelly_fraction"] for t in study.trials if t.value is not None and t.value >= bv - 1e-12]
    return float(min(tied)) if tied else float(study.best_params["kelly_fraction"])


# ============================ 3.2 — final model + base64 strategy + acceptance ============================

def layer3_2_train(df_b, best_params, seed, manifest=None):
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
            "THRESHOLD_ENTRY": PIPELINE_PARAMETERS["THRESHOLD_ENTRY"],
            "LABEL_CONTRACT": "TB_v1.2", "best_params": best_params, "TRAIN_WINDOW": train_window,
            "EXECUTION_CONTRACT": {"entry_fill": PIPELINE_PARAMETERS["ENTRY_FILL"], "exit_fill": PIPELINE_PARAMETERS["EXIT_FILL"],
                                   "scheduled_exit_fill": PIPELINE_PARAMETERS["SCHEDULED_EXIT_FILL"],
                                   "commission_bps": PIPELINE_PARAMETERS["COMMISSION_BPS"], "slippage_bps": PIPELINE_PARAMETERS["SLIPPAGE_BPS"],
                                   "capital_mode": PIPELINE_PARAMETERS["CAPITAL_MODE"], "barrier_mode": PIPELINE_PARAMETERS["BARRIER_MODE"],
                                   "kelly_cap": PIPELINE_PARAMETERS["KELLY_CAP"],
                                   "kelly_basis": "per_trade_fractional_kelly_symmetric_b1: f=clip(kelly_fraction*(2p-1),0,kelly_cap)"},
            "golden_vectors": gv.tolist() if len(gv) else [], "golden_pred": gp, **lineage}


def predict_p(booster, X, feature_names=None):
    import xgboost as xgb
    names = feature_names or FEATURE_MANIFEST
    return booster.predict(xgb.DMatrix(np.asarray(X, float).reshape(-1, len(names)), feature_names=names))


def accept_strategy(train_summary):
    """Strategy objective gate (PF -> MaxDD -> TIM; WR informational). correctness_check acceptance when
    MIN_*_TRADES=null (there is no dev/prod mode — every run is a math/data-processing correctness check)."""
    min_tr = PIPELINE_PARAMETERS["MIN_TRAIN_ACCEPTANCE_TRADES"]
    pf = train_summary["profit_factor"]
    rankable = pf is not None and math.isfinite(pf)
    if min_tr is None:
        return {"accepted": True, "mode": "correctness_check", "rankable": rankable,
                "reason": "MIN_TRAIN_ACCEPTANCE_TRADES is null -> correctness-check acceptance (not a results claim)"}
    if train_summary["trades"] < min_tr:
        return {"accepted": False, "mode": "rejected", "rankable": rankable, "reason": "below MIN_TRAIN_ACCEPTANCE_TRADES"}
    if not rankable:
        return {"accepted": False, "mode": "rejected", "rankable": False, "reason": "PF not rankable"}
    return {"accepted": True, "mode": "accepted", "rankable": True, "reason": "PF-rankable, meets min trades"}


# ============================ shared sequential event engine (3.2 Train + 4.1 OOS) ============================

def run_engine(df, scored, start_idx, end_idx, threshold, kelly_fraction=None):
    """ONE sequential compounding engine used for both Train acceptance and the OOS verdict.
    scored: list of (setup, p). Implements the state machine (FLAT/PENDING/OPEN/HALTED), one open position,
    max-p selection with tie-skip, event-path mark-to-market MDD, inclusive TIM, and the full Risk-Box ledger.

    Position sizing — `kelly_fraction` selects the CAPITAL_MODE:
      * None  -> all-in compounding: q = E / (entry_fill*(1+fee))  (the legacy path; bit-for-bit unchanged).
      * float -> per-trade fractional Kelly: f = clip(kelly_fraction*(2p-1), 0, KELLY_CAP); q = f*E/(entry_fill*(1+fee)).
        The Risk-Box is symmetric (reward:risk b=1) so full per-trade Kelly = 2p-1 (p = the chosen setup's model
        probability); `kelly_fraction` (lambda) is the calibrated fractional-Kelly multiplier; KELLY_CAP forbids leverage.
    """
    E0, fee, slip = PIPELINE_PARAMETERS["INITIAL_CAPITAL_USD"], PIPELINE_PARAMETERS["COMMISSION_BPS"] * 1e-4, PIPELINE_PARAMETERS["SLIPPAGE_BPS"] * 1e-4
    kelly_cap = PIPELINE_PARAMETERS["KELLY_CAP"]
    tie_eps = PIPELINE_PARAMETERS["SIMULTANEOUS_SETUP_TIE_EPS"]
    c = df["close"].to_numpy()
    groups = {}
    for st, p in scored:
        if start_idx <= st["t0"] <= end_idx:
            groups.setdefault(st["t0"], []).append((st, p))
    counters = dict(signals_total=sum(len(v) for v in groups.values()), threshold_rejects=0, not_selected=0,
                    simultaneous_tie_skip=0, gap_invalidated_skip=0, gap_tp_skip=0, ignored_while_open=0, entered=0)
    E = E0
    # canonical equity EVENT trace: [{event_type, bar_index, trade_id, equity}] (replaces a flat float list). The equity
    # VALUES are unchanged (prices/PnL only); the structure adds event_type + bar_index + trade_id for strict identity.
    equity_events = [{"event_type": "initial_capital", "bar_index": -1, "trade_id": 0, "equity": E0}]
    ledger, exposure_bars, flat_from, halted, tid = [], 0, start_idx, False, 0
    for t0 in sorted(groups):
        if halted:
            break
        if t0 < flat_from:
            counters["ignored_while_open"] += len(groups[t0])
            continue
        cands = sorted(groups[t0], key=lambda x: -x[1])
        passing = [(st, p) for st, p in cands if p >= threshold]
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
        if sim["skip"] == "GAP_TP_SKIP":
            counters["gap_tp_skip"] += 1
            continue
        s = chosen["direction"]
        entry_fill, exit_fill, exit_idx = sim["entry_fill"], sim["exit_fill"], sim["exit_idx"]
        # position fraction: all-in (f=1) when kelly_fraction is None; else per-trade fractional Kelly (b=1 Risk-Box).
        f_size = 1.0 if kelly_fraction is None else min(max(kelly_fraction * (2.0 * chosen_p - 1.0), 0.0), kelly_cap)
        if f_size <= 0.0:                                   # no positive Kelly edge -> do not enter (kept out of PF/count)
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
        # event-path equity EVENTS: post-entry-fee dip (at the entry-fill bar), each held close, then the realized exit.
        # The equity VALUES are byte-identical to the prior flat marks (prices/PnL only).
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
        # P0-5 unified event-time contract: EVERY ledger timestamp comes from bar_open/bar_close/decision. The entry and
        # a condition exit fill at a bar OPEN; a scheduled/MOC exit (and the OOS forced exit) fills at a bar CLOSE — so
        # its recorded wall-clock is bar_close. The matching bar INDICES are recorded too (strict event identity), so
        # two different event paths can never share a trade_core projection hash.
        cond = sim["exit_kind"] == "condition"
        exit_fill_ts = bar_open_timestamp(df, exit_idx) if cond else bar_close_timestamp(df, exit_idx)
        ledger.append({"trade_id": tid, "direction": s,
                       "setup_t0_index": int(t0), "signal_bar_index": int(t0), "decision_bar_index": int(t0),
                       "entry_fill_index": int(sim["t_fill"]),
                       "exit_trigger_index": (int(sim["trigger_idx"]) if cond else -1),
                       "exit_fill_index": int(exit_idx),
                       "signal_open_timestamp": str(bar_open_timestamp(df, t0)),
                       "decision_timestamp": str(decision_timestamp_of_setup(df, t0)),
                       "entry_fill_timestamp": str(bar_open_timestamp(df, sim["t_fill"])),
                       "exit_trigger_timestamp": (str(bar_close_timestamp(df, sim["trigger_idx"])) if cond else ""),
                       "exit_fill_timestamp": str(exit_fill_ts),
                       "action_line_at_signal": chosen["L_trend_t0"], "safety_line_at_entry": sim["safety_at_entry"],
                       "safety_line_at_trigger": sim["safety_at_trigger"], "target_level": chosen["take_profit_level"],
                       "entry_fill": entry_fill, "exit_fill": exit_fill,
                       "risk_box_pct_at_fill": 100.0 * chosen["R0"] / max(EPS, abs(chosen["L_trend_t0"])),
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
    # equity_events = the ordered canonical event trace (initial_capital / entry_fee_mark / held_close_mark / exit_fill),
    # each {event_type, bar_index, trade_id, equity} — exposed for strict trading-engine parity hashing. The equity VALUES
    # depend only on prices/PnL (never on wall-clock), so they are an invariant of the calculator.
    return summary, ledger, equity_events


# ============================ 2.4 — independent re-derivation + QC gate ============================

def derive_output_b(df, ticker, manifest=None):
    """1.7 split -> 2.1 detect -> purge -> 2.3 resolve (incl. 2.3.2/2.3.3 coarse context) -> 2.2 Output B (labels
    resolve within Train by purge). The single derivation path used by Phase A and re-used (independently) by
    Phase B parity + the Phase C 3.1 gate. Returns the resolved per-Asset manifest + the coarse context_states /
    segment_of_ts so 4.1 OOS scoring assembles identical X. For the default (1h-only) manifest, context_states is
    empty and no coarse work runs -> behaviour byte-identical to the pre-MTF pipeline."""
    manifest = manifest or resolve_feature_manifest(ticker)
    masks, bounds = layer1_7_split(df)
    setups, detector_audit = layer2_1_detect(df, masks["train"])
    train_setups, n_purged = purge_train_setups(setups, bounds)
    seg = make_segment_of_ts()
    context_states = build_context_states(df, manifest, seg)
    df_b, eligibility_audit = layer2_2_output_b(df, train_setups, ticker, len(df) - 1, manifest, context_states)
    # namespaced audit: detector (2.1) / eligibility (2.2 row exclusion) / scoring (filled by run_universe's
    # score_setups calls, Train vs OOS) — keeps "row not in Output B" vs "setup not scored" distinguishable.
    audit = {"detector": detector_audit, "eligibility": eligibility_audit,
             "scoring": {"train_core_ineligible_skipped": None, "oos_core_ineligible_skipped": None}}
    return {"df": df, "masks": masks, "bounds": bounds, "train_setups": train_setups, "df_b": df_b,
            "audit": audit, "n_purged": n_purged, "manifest": manifest,
            "context_states": context_states, "segment_of_ts": seg}


def derive_output_b_from_parquet(parquet_path, ticker, manifest=None):
    """Independently re-derive Output B from the clean Parquet (no notebook/Phase-A memory) — used by 2.4
    Phase B (parity) and the 3.1 current-cycle start gate (Phase C)."""
    return derive_output_b(pd.read_parquet(parquet_path), ticker, manifest)


def score_setups(booster, df, setups, manifest=None, context_states=None, audit=None):
    """Score setups for Train acceptance / 4.1 OOS. Assembles X in manifest feature order: the 1h features from
    _features_at + (when coarse timeframes are enabled) the causal as-of-projected 1d/1w context — the SAME
    assembly as 2.2 Output B, so Train and OOS see identical X. **The SAME eligibility predicate as 2.2**: a setup
    whose mandatory 1h-core feature is non-finite is SKIPPED (not added to X, not predicted, not returned) — Train
    and OOS exclude identically. `audit`, if a dict, gets `core_ineligible_skipped`. Default (1h-only) skips all
    coarse work and excludes 0 post-warmup setups (byte-identical)."""
    if not setups:
        return []
    manifest = manifest or DEFAULT_FEATURE_MANIFEST     # resolve before the eligibility predicate (needs the 1h block)
    names = feature_names_of(manifest)
    high, low, close, vol = (df[x].to_numpy() for x in ("high", "low", "close", "volume"))
    atr = wilder_atr(high, low, close, PIPELINE_PARAMETERS["W_ATR"])
    vmean, vstd = rolling_mean_std(vol, PIPELINE_PARAMETERS["W_VOL"])
    eligible, X, skipped = [], [], 0
    for st in setups:
        merged, _ = assemble_setup_x(df, st, atr, vmean, vstd, manifest, context_states)   # SAME assembler as 2.2
        if core_feature_eligibility(merged, manifest) is not None:   # mandatory 1h-core non-finite -> skip
            skipped += 1
            continue
        eligible.append(st)
        X.append([merged[k] for k in names])
    if audit is not None:
        audit["core_ineligible_skipped"] = skipped
    if not eligible:
        return []
    ps = predict_p(booster, X, feature_names=names)
    return list(zip(eligible, [float(p) for p in ps]))

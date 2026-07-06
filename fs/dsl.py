"""Safe causal feature DSL for Sonnet-proposed features (port of lstm/features.py:213-322, tuned
for 1h bars). Causality is guaranteed by the GRAMMAR: the only variables are this bar's and earlier
OHLCV (`o/h/l/c/v`), `shift(x, n)` needs n>=1 (backward only), and rolling/ewm/zscore/rank are
trailing windows. So a validated expression can NEVER read the future — no expression the whitelist
accepts is look-ahead. New features are 1h-bar features; the WO §1 multi-TF / cross-TF pool is fixed.
"""
import ast
import json
from pathlib import Path

import numpy as np
import pandas as pd

WARMUP_1H = 500  # bars discarded before the finiteness check (indicator warmup on 1h)

_DSL_VARS = {"o", "h", "l", "c", "v"}
_DSL_FUNCS = {"shift", "rolling_mean", "rolling_std", "rolling_min", "rolling_max",
              "ewm", "zscore", "rank", "log", "abs", "sign", "clip"}


def _dsl_check(node):
    """Whitelist the AST: only allowed vars/funcs/ops/number literals; shift needs n>=1."""
    if isinstance(node, ast.Expression):
        return _dsl_check(node.body)
    if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult, ast.Div)):
        _dsl_check(node.left); _dsl_check(node.right); return
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        _dsl_check(node.operand); return
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _DSL_FUNCS:
            raise ValueError("call not allowed")
        if node.keywords:
            raise ValueError("keyword args not allowed")
        for a in node.args:
            _dsl_check(a)
        if node.func.id == "shift":
            n = node.args[1] if len(node.args) > 1 else None
            if not (isinstance(n, ast.Constant) and isinstance(n.value, int) and n.value >= 1):
                raise ValueError("shift(x, n) requires an integer n >= 1 (backward only)")
        return
    if isinstance(node, ast.Name):
        if node.id not in _DSL_VARS:
            raise ValueError(f"name not allowed: {node.id}")
        return
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return
    raise ValueError(f"node not allowed: {type(node).__name__}")


def _dsl_env(df):
    def S(x):
        return x if isinstance(x, pd.Series) else pd.Series(x)
    return {
        "__builtins__": {},
        "o": pd.Series(df["open"].to_numpy(float)), "h": pd.Series(df["high"].to_numpy(float)),
        "l": pd.Series(df["low"].to_numpy(float)), "c": pd.Series(df["close"].to_numpy(float)),
        "v": pd.Series(df["volume"].to_numpy(float)),
        "shift": lambda x, n: S(x).shift(int(n)),
        "rolling_mean": lambda x, w: S(x).rolling(int(w)).mean(),
        "rolling_std": lambda x, w: S(x).rolling(int(w)).std(ddof=0),
        "rolling_min": lambda x, w: S(x).rolling(int(w)).min(),
        "rolling_max": lambda x, w: S(x).rolling(int(w)).max(),
        "ewm": lambda x, span: S(x).ewm(span=int(span), adjust=False, min_periods=int(span)).mean(),
        "zscore": lambda x, w: (S(x) - S(x).rolling(int(w)).mean())
                               / S(x).rolling(int(w)).std(ddof=0).replace(0.0, np.nan),
        "rank": lambda x, w: S(x).rolling(int(w)).apply(lambda a: float((a <= a[-1]).mean()), raw=True),
        "log": lambda x: np.log(S(x)),
        "abs": lambda x: S(x).abs(),
        "sign": lambda x: np.sign(S(x)),
        "clip": lambda x, lo, hi: S(x).clip(float(lo), float(hi)),
    }


def dsl_eval(expr, df):
    """Compile + evaluate a validated DSL expression to a numpy array aligned to df."""
    tree = ast.parse(expr, mode="eval")
    _dsl_check(tree)
    with np.errstate(all="ignore"):
        out = eval(compile(tree, "<dsl>", "eval"), _dsl_env(df))
    return np.asarray(pd.Series(out).to_numpy(float))


def validate_proposal(name, expr, sample_df, known_names):
    """Fail-closed gate before a proposal enters the pool: identifier ok, unique, parses under the
    whitelist, evaluates, bounded z-clip applied by the caller, >=99% finite after warmup, not
    constant. Returns (ok, reason)."""
    if not name or not name.replace("_", "").isalnum() or name[0].isdigit():
        return False, "name must be a simple identifier"
    if name in known_names:
        return False, "name already exists"
    try:
        vals = dsl_eval(expr, sample_df)
    except Exception as e:  # noqa: BLE001
        return False, f"invalid DSL: {e}"
    if len(vals) != len(sample_df):
        return False, "length mismatch"
    tail = vals[WARMUP_1H:]
    finite = np.isfinite(tail)
    if len(tail) == 0 or finite.mean() < 0.99:
        return False, f"only {finite.mean():.0%} finite after warmup (need >=99%)"
    if np.nanstd(tail[finite]) < 1e-12:
        return False, "constant feature"
    if np.nanmax(np.abs(tail[finite])) > 1e6:
        return False, "unbounded magnitude (>1e6) — not stationary/bounded"
    return True, "ok"


def max_abs_corr(vals, existing_frame):
    """Max |Spearman ρ| of a candidate against existing feature columns (anti-redundancy)."""
    if existing_frame is None or existing_frame.shape[1] == 0:
        return 0.0
    s = pd.Series(vals)
    best = 0.0
    for col in existing_frame.columns:
        r = s.corr(existing_frame[col], method="spearman")
        if np.isfinite(r):
            best = max(best, abs(float(r)))
    return best


# ---------------- registry ----------------

def proposed_registry(path):
    return json.loads(Path(path).read_text()) if Path(path).exists() else {}


def proposed_names(path):
    return [k for k in proposed_registry(path) if not k.startswith("_")]


def proposed_frame(df, path):
    """Evaluate every registered proposed feature into a frame; a feature that fails for a ticker
    becomes all-NaN (that ticker's window is simply dropped by the finiteness filter downstream)."""
    reg = proposed_registry(path)
    f = pd.DataFrame(index=df.index)
    for nm, spec in reg.items():
        if nm.startswith("_"):
            continue
        try:
            f[nm] = dsl_eval(spec["expr"], df)
        except Exception:  # noqa: BLE001
            f[nm] = np.nan
    return f

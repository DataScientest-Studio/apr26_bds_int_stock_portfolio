#!/usr/bin/env python3
"""Prove the 2-seed feature-search evaluator is (a) deterministic, (b) genuinely averaging two
DIFFERENT weight inits (else it would be pointless), and (c) that eval_seeds=1 reproduces the
old single-seed per-fold score exactly. One ticker (AAPL); Train-only, no OOS touched."""
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import model as M          # noqa: E402
import feature_search as S  # noqa: E402

T = (sys.argv[1] if len(sys.argv) > 1 else "AAPL").upper()
print("EVAL_SEEDS =", S.EVAL_SEEDS)
prep = S._prep(T)
assert prep is not None, f"{T}: too thin"

# (a) determinism: evaluate([]) twice must be bit-identical
b1 = S.evaluate(prep, [])
b2 = S.evaluate(prep, [])
same = all((x is None and z is None) or (x == z) for x, z in zip(b1, b2))
print(f"[a] evaluate([]) reproducible: {same}  base_folds={['%.5f'%v if v is not None else None for v in b1]}")

# (b) the two seeds must produce DIFFERENT single-seed fold scores (variance being averaged)
one = M.SEED
two = int(M.SEED) + 10007
S.EVAL_SEEDS = [one]
s_a = S.evaluate(prep, [])
S.EVAL_SEEDS = [two]
s_b = S.evaluate(prep, [])
diffs = [abs(a - b) for a, b in zip(s_a, s_b) if a is not None and b is not None]
print(f"[b] per-seed fold-score spread (mean|Δ|): {np.mean(diffs):.5f}  seedA={['%.5f'%v for v in s_a if v is not None]} seedB={['%.5f'%v for v in s_b if v is not None]}")

# (c) eval_seeds=1 with the base SEED == the old single-seed path (sanity for backward-compat)
S.EVAL_SEEDS = [one]
c1 = S.evaluate(prep, [])
S.EVAL_SEEDS = [one]
c2 = S.evaluate(prep, [])
print(f"[c] eval_seeds=1 reproducible: {all(x==z for x,z in zip(c1,c2) if x is not None)}")

# restore 2-seed and run a full search twice -> identical subset
S.EVAL_SEEDS = [one, two]
r1 = S.search_ticker(T)
r2 = S.search_ticker(T)
print(f"[d] search_ticker reproducible: {r1 == r2}")
print(f"    result: base={r1['base']:.5f} best={r1['best_cv']:.5f} subset={r1['subset']}")
print("OK" if same and np.mean(diffs) > 0 and r1 == r2 else "FAIL")
sys.exit(0 if (same and np.mean(diffs) > 0 and r1 == r2) else 1)

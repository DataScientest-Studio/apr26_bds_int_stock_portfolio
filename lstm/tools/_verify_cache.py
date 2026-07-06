#!/usr/bin/env python3
"""Post-build cache transparency proof for one ticker:
  1. cached CORE+OPTIONAL frame == freshly computed frame, byte-identical (NaN-aware, per column)
  2. feature_frame(df, ticker) [cache path] == feature_frame(df, None) [compute path], incl PROPOSED
Exit 0 + IDENTICAL only if every column matches exactly.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import features as F   # noqa: E402
import pipeline as P   # noqa: E402

T = (sys.argv[1] if len(sys.argv) > 1 else "AAPL").upper()
df = P.load_bars(T)

# (1) raw cache vs fresh compute
cached = pd.read_parquet(ROOT / "cache" / "features" / f"{T}.parquet").reset_index(drop=True)
fresh = pd.concat([F.core_frame(df, P.CONFIG), F.optional_frame(df)], axis=1).reset_index(drop=True)
assert list(cached.columns) == list(fresh.columns), f"col mismatch {cached.columns} vs {fresh.columns}"
bad = [c for c in fresh.columns
       if not np.array_equal(cached[c].to_numpy(np.float64), fresh[c].to_numpy(np.float64), equal_nan=True)]
print(f"[1] {T} raw frame: {len(fresh.columns)} cols, {len(fresh)} rows, mismatched={bad}")

# (2) full feature_frame both paths (cache-hit vs forced-compute via ticker=None)
fc = P.feature_frame(df, T)      # cache path
fk = P.feature_frame(df, None)   # compute path
assert list(fc.columns) == list(fk.columns), "feature_frame col mismatch"
bad2 = [c for c in fk.columns
        if not np.array_equal(fc[c].to_numpy(np.float64), fk[c].to_numpy(np.float64), equal_nan=True)]
print(f"[2] {T} feature_frame: {len(fk.columns)} cols (incl PROPOSED), mismatched={bad2}")

print("IDENTICAL" if not bad and not bad2 else "MISMATCH")
sys.exit(0 if not bad and not bad2 else 1)

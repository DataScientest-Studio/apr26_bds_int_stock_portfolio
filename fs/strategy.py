"""Sealed, deployable strategy artifacts (one per model), produced after Study 2 + p* on the CV
window. Each carries the final model trained on ALL CV data, the selected feature/channel set, the
operating point p*, and a GOLDEN-VECTOR selfcheck (a few stored predictions the loader must
reproduce bit-identically) — the same sealing discipline as the sealed pipelines
(xgb/src/asset_writers.py write_strategy). Trained on CV only; the holdout is read separately, once.
"""
import base64
import hashlib

import numpy as np

from . import art_dir, write_json


def _sha(b):
    return hashlib.sha256(bytes(b)).hexdigest()


def _b64(b):
    return base64.b64encode(bytes(b)).decode("ascii")


def _unb64(s):
    return base64.b64decode(s.encode("ascii"))


def golden_sample(proba, n=8):
    """Indices + predictions to embed for a loader selfcheck (evenly spaced, deterministic)."""
    if len(proba) == 0:
        return {"idx": [], "pred": []}
    idx = list(range(0, len(proba), max(1, len(proba) // n)))[:n]
    return {"idx": idx, "pred": [[round(float(x), 10) for x in proba[i]] for i in idx]}


def check_golden(proba, golden, tol=1e-8):
    for k, i in enumerate(golden["idx"]):
        got, want = np.asarray(proba[i], float), np.asarray(golden["pred"][k], float)
        if not np.allclose(got, want, atol=tol, rtol=0):
            return False
    return True


def write(universe, name, meta):
    path = art_dir(universe) / name
    write_json(path, meta)
    return path

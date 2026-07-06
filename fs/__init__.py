"""WO-FS — shared feature-selection study (docs/XGB-ZLECENIE-LOOP.md + docs/LSTM-ZLECENIE-LOOP.md).

Both loops share one label truth (Study 1), one validation module (Purged K-Fold + CPCV + holdout-once)
and one results store. The sealed xgb/ and lstm/ pipelines are read strictly read-only; every artifact
of this study lives under fs/artifacts/<universe>/.
"""
import json
import os
import random
from pathlib import Path

import numpy as np

FS_ROOT = Path(__file__).resolve().parent
REPO = FS_ROOT.parent
ART = Path(os.environ.get("FS_ARTIFACTS") or FS_ROOT / "artifacts")

CLASSES = (-1, 0, 1)  # label y -> model class index = y + 1


def _strip(o):
    if isinstance(o, dict):
        return {k: _strip(v) for k, v in o.items() if not k.startswith("_")}
    return o


CONFIG = _strip(json.loads((FS_ROOT / "config.json").read_text()))
SEED = int(CONFIG["SEED"])


def seed_everything(seed=SEED):
    random.seed(seed)
    np.random.seed(seed)
    return seed


def art_dir(universe):
    d = ART / universe
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n")
    os.replace(tmp, path)


def read_json(path):
    return json.loads(Path(path).read_text())

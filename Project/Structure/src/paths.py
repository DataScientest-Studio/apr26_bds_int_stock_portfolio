"""Resolved project paths — single source of truth for where data/models live.

The live code (``Structure/``) is kept minimal: it holds NO data or model
artifacts. Those live in the active run under ``Archive/runs/<date>/`` and are
exposed through symlinks in ``Project/endproduct/``. This module reads
``Structure/config/paths.yaml`` and resolves the relative entries against the
``Structure/`` directory.

Switch the active run by editing ``config/paths.yaml`` (``active_run``) and/or
re-pointing the ``Project/endproduct/`` symlinks — no code change needed.
"""

from __future__ import annotations

from pathlib import Path

# Structure/ — the code root (this file is Structure/src/paths.py).
STRUCTURE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = STRUCTURE_DIR / "config" / "paths.yaml"


def _load_config(path: Path) -> dict:
    """Tiny flat-YAML reader (key: value per line) — avoids a PyYAML dependency."""
    config: dict[str, str] = {}
    if not path.exists():
        return config
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        config[key.strip()] = value.strip().strip("'\"")
    return config


_cfg = _load_config(CONFIG_FILE)


def _resolve(value: str, default: str) -> Path:
    """Resolve a config path relative to STRUCTURE_DIR."""
    return (STRUCTURE_DIR / _cfg.get(value, default)).resolve()


ENDPRODUCT_DIR = _resolve("endproduct_root", "../endproduct")
ARCHIVE_RUNS = _resolve("archive_runs", "../../Archive/runs")
ACTIVE_RUN = _cfg.get("active_run", "2026-06-08")

# Live artifact locations (symlinks under endproduct/ point at the active run).
DATA_DIR = ENDPRODUCT_DIR / "data"
MODEL_DIR = ENDPRODUCT_DIR / "models"
FIG_DIR = ENDPRODUCT_DIR / "reports" / "figures"

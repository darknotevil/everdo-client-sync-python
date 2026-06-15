"""Filesystem locations for Everdo client config and state.

The sync-client CLI (``everdo_cli.py``) and the ``everdo`` package both read
``config.json`` (host/key/version) and ``state.json`` (last_sync_ts + cached
items/tags) from a single directory.

Resolution order (read):

1. ``$XDG_CONFIG_HOME/everdo/`` (or ``~/.config/everdo/`` if unset) — default.
2. ``<project-root>/.config/everdo/`` — fallback for portable / per-checkout use.

Writes go to whichever directory the file was last found in; if neither
exists, the XDG location is created. The project-root fallback is computed
relative to *this* file so the resolution stays stable regardless of CWD.
"""

from __future__ import annotations

import os
from pathlib import Path

_PKG_DIR = Path(__file__).resolve().parent          # .../everdo-client-sync-python/everdo
_PROJECT_ROOT = _PKG_DIR.parent.parent              # .../<everdo-monorepo-root>

CONFIG_FILE = "config.json"
STATE_FILE = "state.json"


def xdg_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.join(os.path.expanduser("~"), ".config")
    return Path(base) / "everdo"


def project_dir() -> Path:
    return _PROJECT_ROOT / ".config" / "everdo"


def _resolve(filename: str) -> Path:
    xdg = xdg_dir() / filename
    if xdg.exists():
        return xdg
    proj = project_dir() / filename
    if proj.exists():
        return proj
    return xdg


def config_path() -> Path:
    return _resolve(CONFIG_FILE)


def state_path() -> Path:
    return _resolve(STATE_FILE)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)

"""Resolve Everdo connection settings and build a ready-to-use client.

Single source of truth for the ``flag > env > config-file > default``
precedence shared by the CLI (``everdo_cli.py``) and any embedding program
(e.g. the tag classifier), so neither has to re-implement config loading.

The config file itself is located via :mod:`everdo.paths` (XDG first, then a
project-root fallback); an explicit ``config_path`` overrides that lookup.
"""

from __future__ import annotations

import json
import os
from typing import Any

from . import paths
from .client import EverdoClient, EverdoError
from .tasks import EverdoTasks

DEFAULT_VERSION = "1.99.0"

# Setting name -> environment variable consulted between flag and config file.
ENV_VARS = {"host": "EVERDO_HOST", "key": "EVERDO_KEY", "version": "EVERDO_VERSION"}


class MissingConfigError(EverdoError):
    """Raised when host/key cannot be resolved from any source."""


def config_file(explicit: str | None = None) -> str:
    """Path the config is read from / written to (explicit wins, else XDG)."""
    return explicit if explicit else str(paths.config_path())


def load_config(config_path: str | None = None) -> dict[str, Any]:
    """Load the persisted config JSON; missing/corrupt file -> empty dict."""
    try:
        with open(config_file(config_path), encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_config(cfg: dict[str, Any], config_path: str | None = None) -> str:
    """Atomically persist ``cfg`` (0600) and return the path written to."""
    path = config_file(config_path)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return path


def resolve_setting(
    name: str,
    cli_value: Any = None,
    *,
    default: Any = None,
    config_path: str | None = None,
    _cfg: dict[str, Any] | None = None,
) -> Any:
    """One setting by ``flag > env (EVERDO_*) > config file > default``.

    ``_cfg`` lets callers resolving several settings share a single config
    read instead of re-opening the file per setting.
    """
    if cli_value:
        return cli_value
    env = os.environ.get(ENV_VARS.get(name, ""))
    if env:
        return env
    cfg = _cfg if _cfg is not None else load_config(config_path)
    return cfg.get(name, default)


def resolve_credentials(
    *,
    host: str | None = None,
    key: str | None = None,
    version: str | None = None,
    config_path: str | None = None,
) -> tuple[str, str, str]:
    """Resolve ``(host, key, version)`` or raise :class:`MissingConfigError`."""
    cfg = load_config(config_path)
    host = resolve_setting("host", host, config_path=config_path, _cfg=cfg)
    key = resolve_setting("key", key, config_path=config_path, _cfg=cfg)
    version = resolve_setting(
        "version", version, default=DEFAULT_VERSION, config_path=config_path, _cfg=cfg
    )
    if not host or not key:
        raise MissingConfigError(
            "host/key not configured. Run `everdo-cli config set "
            "--host <ip:port> --key <API_KEY>`, or pass host/key, or set "
            "EVERDO_HOST/EVERDO_KEY."
        )
    return host, key, version


def load_client(
    *,
    host: str | None = None,
    key: str | None = None,
    version: str | None = None,
    config_path: str | None = None,
    **client_kw: Any,
) -> EverdoClient:
    """Build an :class:`EverdoClient` from resolved credentials."""
    host, key, version = resolve_credentials(
        host=host, key=key, version=version, config_path=config_path
    )
    return EverdoClient(host, key=key, version=version, **client_kw)


def load_tasks(
    *,
    host: str | None = None,
    key: str | None = None,
    version: str | None = None,
    config_path: str | None = None,
    refresh_ttl: float | None = None,
    **client_kw: Any,
) -> EverdoTasks:
    """Build a ready :class:`EverdoTasks` from resolved config.

    Keyword overrides take precedence over env/config exactly as the CLI
    flags do. Extra keywords (``state_path``, ``timeout``, ``scheme`` …) flow
    through to :class:`EverdoClient`. ``refresh_ttl`` left as ``None`` keeps
    the :class:`EverdoTasks` default.
    """
    client = load_client(
        host=host, key=key, version=version, config_path=config_path, **client_kw
    )
    if refresh_ttl is None:
        return EverdoTasks(client)
    return EverdoTasks(client, refresh_ttl=refresh_ttl)

"""Low-level transport for the Everdo local sync API.

The official Everdo desktop app, when running in "Server" mode, exposes a small
HTTP(S) sync API on port 11111. It is the same protocol official clients use to
synchronize, so it allows pushing arbitrary changes to existing items (which the
public ``/api/items`` endpoint does not).

Confirmed against a live server (Everdo >= v1.0.6-3):

* Transport is HTTPS with a self-signed certificate -> ``verify=False``.
* Authentication is the ``key`` query parameter (the server "API Key").
* ``POST /pull``  (no body)            -> full dump ``{items, tags, deletions}``.
* ``POST /sync``  requires a ``version`` query parameter, otherwise the server
  answers ``400 "Outdated Everdo version. Please upgrade to v1.0.6-3 or higher."``
  Body: ``{last_sync_ts, time_delta_ms, changes: {items, tags, deletions}}``.
  Response: ``{sync_ts, success, items, tags, deletions_to_add}`` containing
  everything changed after ``last_sync_ts``.
* ``GET  /time``                       -> ``{"server_time_ms": <ms>}``.
* ``POST /push`` / ``POST /wipe`` overwrite/erase the whole database and are
  intentionally NOT wrapped here.
"""

from __future__ import annotations

import json
import os
from typing import Any

import requests
import urllib3

from . import paths

# The server uses a self-signed certificate; silence the noisy per-request warning.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class EverdoError(RuntimeError):
    """Raised when the server returns a non-200 response."""


class EverdoClient:
    """Thin HTTP wrapper around the Everdo sync endpoints.

    Parameters
    ----------
    host:
        ``"ip:port"`` of the Everdo server in Server mode, e.g. ``"127.0.0.1:11111"``.
    key:
        The server API key (the ``key`` query parameter).
    version:
        Client version advertised to pass the server's version gate. Any value
        ``>= 1.0.6-3`` works; the default is deliberately high.
    state_path:
        Where to persist ``last_sync_ts`` between runs so we behave like a proper
        incremental client. Defaults to the shared XDG location (see
        ``everdo.paths.state_path``).
    """

    def __init__(
        self,
        host: str,
        key: str,
        version: str = "1.99.0",
        *,
        scheme: str = "https",
        verify: bool = False,
        timeout: int = 30,
        state_path: str | None = None,
    ) -> None:
        self.base = f"{scheme}://{host}"
        self.key = key
        self.version = version
        self.verify = verify
        self.timeout = timeout
        self.state_path = state_path or str(paths.state_path())
        self._session = requests.Session()

    # ------------------------------------------------------------------ state
    def _load_state(self) -> dict[str, Any]:
        try:
            with open(self.state_path, encoding="utf-8") as fh:
                return json.load(fh)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_state(self, **values: Any) -> None:
        state = self._load_state()
        state.update(values)
        os.makedirs(os.path.dirname(self.state_path) or ".", exist_ok=True)
        tmp = self.state_path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, ensure_ascii=False, indent=2)
        os.replace(tmp, self.state_path)

    @property
    def last_sync_ts(self) -> int:
        """Last confirmed server sync timestamp (0 means 'everything')."""
        value = self._load_state().get("last_sync_ts")
        return int(value) if value is not None else 0

    # -------------------------------------------------------------- low level
    def _request(self, method: str, path: str, *, params=None, json_body=None) -> requests.Response:
        query = {"key": self.key}
        if params:
            query.update(params)
        resp = self._session.request(
            method,
            f"{self.base}{path}",
            params=query,
            json=json_body,
            verify=self.verify,
            timeout=self.timeout,
        )
        if resp.status_code != 200:
            raise EverdoError(f"{method} {path} -> HTTP {resp.status_code}: {resp.text[:300]}")
        return resp

    # ----------------------------------------------------------------- public
    def server_time_ms(self) -> int:
        return int(self._request("GET", "/time").json()["server_time_ms"])

    def time_delta_ms(self) -> int:
        """Server clock minus local clock, in milliseconds."""
        import time

        local = int(time.time() * 1000)
        return self.server_time_ms() - local

    def pull(self) -> dict[str, Any]:
        """Full snapshot of the server database."""
        return self._request("POST", "/pull").json()

    def sync(
        self,
        changes: dict[str, list] | None = None,
        last_sync_ts: Any = "__state__",
        *,
        persist_ts: bool = True,
    ) -> dict[str, Any]:
        """Push ``changes`` and pull everything newer than ``last_sync_ts``.

        ``changes`` is ``{"items": [...], "tags": [...], "deletions": [...]}``;
        missing keys default to empty lists.

        When ``persist_ts`` is true (the default, for standalone transport use)
        the new ``sync_ts`` is persisted as ``last_sync_ts`` immediately. The
        cache layer passes ``persist_ts=False`` and persists the cursor itself,
        atomically together with the delta it applied, so the on-disk cursor can
        never run ahead of the cached items (which would silently drop changes
        the server will not resend).
        """
        changes = dict(changes or {})
        for bucket in ("items", "tags", "deletions"):
            changes.setdefault(bucket, [])

        if last_sync_ts == "__state__":
            last_sync_ts = self.last_sync_ts

        body = {
            "last_sync_ts": last_sync_ts,
            "time_delta_ms": 0,
            "changes": changes,
        }
        resp = self._request("POST", "/sync", params={"version": self.version}, json_body=body).json()
        if persist_ts and resp.get("sync_ts") is not None:
            self._save_state(last_sync_ts=resp["sync_ts"])
        return resp

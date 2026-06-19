# Tech stack

## Runtime

- **Python 3.10+** (PEP 604 unions, `from __future__ import annotations`).
- **`requests`** — HTTP transport to the `/sync` API.
- **`typer`** — the CLI framework (`noun verb --params`, `--json`, `--help`). Vendors its own CLI engine; `click` is no longer a separate dependency.
- **`urllib3`** — comes in via `requests`; touched directly only to silence `InsecureRequestWarning` (self-signed cert).

## Target server

- Everdo `>= v1.0.6-3` in Server mode (Settings → Sync → Server → API).
- Default port `11111`, configurable via host string `<ip:port>`.

## Transport notes

- HTTPS-only. Self-signed certificate → `verify=False`. No dev-CA mechanism (Everdo does not expose one).
- Auth via `?key=<API_KEY>` query param. No header-based auth.
- No retry / backoff layer in `EverdoClient` — `/sync` is fast and the desktop server is local; on failure the next agent tick retries from a fresh `last_sync_ts`.

## Why no framework

- The whole HTTP surface is 3 endpoints; pulling in `httpx` / `aiohttp` would only add latency and dep surface.
- Cache layer is intentionally in-process: no Redis, no SQLite. The state file is a single JSON blob, atomically rewritten on every sync.
- No async — agent ticks are short-lived processes; an event loop buys nothing.

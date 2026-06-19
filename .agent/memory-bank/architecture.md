# Architecture

## Modules

| Module             | Responsibility |
|--------------------|----------------|
| `everdo/client.py` | Low-level transport: HTTP wrapper around `/pull`, `/sync`, `/time`. Persists `last_sync_ts` between runs. |
| `everdo/tasks.py`  | High-level item operations. Holds the in-memory cache of items/tags; resolves reads from cache; applies LWW; bumps `*_ts` on writes. |
| `everdo_cli.py`    | `typer` `noun verb --params` front-end to `EverdoTasks`. ID-prefix resolution, friendly list/type enums, and global `--json` output (incl. structured errors) live here, not in the library. |

Dependencies: `everdo_cli` → `typer` + `everdo.tasks` + `everdo.client`; `everdo.tasks` → `everdo.client`; `everdo.client` → `requests` (+ `urllib3` for the silence-warning import).

## Cache layer (EverdoTasks)

- Materialized from `client.pull()` on first use, then kept incremental via `client.sync()` deltas.
- Reads (`all_items`, `get`, `find`, project helpers) all go through the cache.
- Internal TTL (default 5 s) deduplicates incidental refreshes — a single agent "tick" of N reads costs one HTTP round-trip.
- Mutations bypass the TTL and always force a fresh `/sync` first, to avoid read-modify-write races against the desktop client.
- After a mutation, the `/sync` response is applied to the cache (per-item LWW).

## State file layout

The on-disk cache lives at `state.json` inside the resolved config directory (see *Config file resolution* below — same `_resolve()` is used for both `config.json` and `state.json`). Shape:

```
{
  "last_sync_ts": <int>,
  "items": {
    "<ID>": { "id": "<ID>", "title": "...", "note": "...",
              "list": "i", "type": "a", "parent_id": "...",
              "completed_on": null, "created_on": <int>,
              "tags": [...], ... },
    ...
  },
  "tags": {
    "<TAG_ID>": { "id": "<TAG_ID>", "title": "...", ... }
  }
}
```

Both `items` and `tags` are **dicts keyed by id**, NOT lists. Iterate via `state["items"].values()`. Iterating `state["items"]` itself yields id strings — `item["title"]` on a string raises `TypeError`.

Path can be overridden via `EverdoClient(..., state_path=...)`. Useful for tests with a throwaway state file in `/tmp/`.

## Config file resolution

CLI config (`host`, `key`, `version`) and the state cache share the same directory lookup, implemented by `_resolve()` in `everdo/paths.py`. Priority (highest → lowest):

1. **`--config` CLI flag** — explicit path override (config only; state stays in the resolved dir).
2. **XDG default** `$XDG_CONFIG_HOME/everdo/<file>` (or `~/.config/everdo/<file>` when `XDG_CONFIG_HOME` is unset).
3. **Portable fallback** `<repo-root>/.config/everdo/<file>` — per-checkout, useful for sandboxed/portable installs.

When *reading*, the first existing file wins. When *writing* (`config set`), the config is saved to whichever path was selected during read. If no config file exists yet, the XDG location is used as the default write target.

The `--config` flag can force any arbitrary path, bypassing the auto-detection entirely.

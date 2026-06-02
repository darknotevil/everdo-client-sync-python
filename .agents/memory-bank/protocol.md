# Sync protocol

Verified against Everdo `>= v1.0.6-3`. The Server-mode HTTP(S) API exposed on port 11111 is the same protocol the official desktop client uses — that is how this library can mutate existing items, unlike the public `/api/items` endpoint (create-only).

## Transport

- HTTPS with a **self-signed certificate** → `verify=False` in `requests`. `urllib3`'s `InsecureRequestWarning` is silenced at import time in `everdo/client.py`.
- Authentication: `?key=<API_KEY>` query parameter on every request.

## Endpoints

| Method | Path                  | Purpose |
|--------|-----------------------|---------|
| POST   | `/pull`               | Full dump: `{items, tags, deletions}`. No body. |
| POST   | `/sync?version=<ver>` | Incremental sync. **`version` is required**, otherwise the server answers `400 "Outdated Everdo version. Please upgrade to v1.0.6-3 or higher."` |
| GET    | `/time`               | `{"server_time_ms": <ms>}`. Doubles as connectivity / auth probe. |
| POST   | `/push` / `/wipe`     | Overwrite / erase the whole DB. **Intentionally not wrapped** — far too destructive for a manual-client design. See [progress.md](progress.md). |

## /sync body & response

Request body:

```
{
  "last_sync_ts": <int>,
  "time_delta_ms": <int>,
  "changes": { "items": [...], "tags": [...], "deletions": [...] }
}
```

Response:

```
{
  "sync_ts": <int>,
  "success": <bool>,
  "items": [...],          # everything newer than last_sync_ts
  "tags": [...],
  "deletions_to_add": [...]
}
```

## Last-write-wins merge

Server-side conflict resolution is LWW at **two levels**:

1. **Whole-item**: the version with the greater `changed_ts` becomes the base.
2. **Per-field**: individual fields are resolved by their paired `<field>_ts` timestamp.

Consequence: an edit must always **read the whole item**, bump `changed_ts` and the paired `*_ts` of the changed fields, then send it back. A partial diff is unsafe — fields without a `*_ts` may get clobbered by stale values from the desktop client.

### Field-timestamp pairing

In `everdo/tasks.py`:

- `TS_FIELDS` — fields with a regular `<field>_ts` companion (`title`, `note`, `list`, `type`, `is_focused`, `due_date`, `completed_on`, `parent_id`, position fields, ...).
- `IRREGULAR_TS = {"tags": "tags_changed_ts"}` — irregular naming exception.

### Derived fields stripped on write

`is_existing_item`, `effective_tags`, `parent_ref`, `contact_ref` are server-derived. The library deletes them before sending an item back (`DERIVED` set in `tasks.py`).

## Deletions

A deletion is `{"sync_id": "<id>", "entity_type": "i", "ts": <now>}` posted in `changes.deletions` on `/sync`. The server returns matching tombstones in `deletions_to_add`. The cache applies them by removing the item from `items` and remembering the tombstone, so a later incremental does not resurrect it.

## Client version string

`EverdoClient(version="1.99.0")` — deliberately high. Bumping the server-side floor in future Everdo releases would otherwise break clients pinned to a real historical version.

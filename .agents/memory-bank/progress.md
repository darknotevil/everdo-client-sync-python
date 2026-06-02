# Progress

## Implemented

- Full CRUD on items via `/sync`: create, mutate (move/convert/assign/rename/note/due/focus/complete), trash (soft delete), delete (permanent + tombstone).
- Persistent local cache with incremental `/sync` deltas, TTL-deduped reads, mutation-forced refresh.
- ID-prefix resolver (4+ hex) for short batch commands at the CLI layer.
- Fail-fast batch resolution — a typo or ambiguous prefix aborts the batch *before* any mutation runs.
- Project / notebook semantics: `assign --to <pid>` with auto-promote out of Inbox/Trash/Archived (`list ∈ {i,d,r}`) so newly attached items render in the project view.
- Server time fetch (`/time`), full backup dump (`/pull` → file).

## Intentionally NOT implemented

- **`/push` and `/wipe`** — these wipe or overwrite the entire database from the client side. Wrong shape for a manual client; the desktop server should remain authoritative. If you need to bulk-restore, use the desktop client's import flow.

## TODO / ideas

- **Tag helpers.** Currently `set_tags(id, [tag_obj, ...])` accepts already-shaped tag objects (form mirrors what `/pull` returns under `tags`). Two missing helpers would round out the API:
  - `resolve_tag(name) -> tag_obj` — case-insensitive lookup against the cached `tags` dict.
  - `create_tag(name, color=...) -> tag_obj` — write through `changes.tags` on `/sync`, then add to cache.
- **Smarter conflict diagnostics.** When a mutation returns with a different `changed_ts` than expected (someone else edited the item between our read and write), the library currently overwrites silently. Could detect and surface a warning.

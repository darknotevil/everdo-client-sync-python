# Progress

## Implemented

- Full CRUD on items via `/sync`: create, mutate (list/type/parent/title/note/due/focus/complete), trash (soft delete), delete (permanent + tombstone).
- Typer-based `noun verb --params` CLI (`item` / `tag` / `project` / `notebook` / `sync` / `config`); field setters collapsed into a single `item set`; global `--json` with structured `{"error": ...}` output. The library API keeps the granular wrappers (`rename`/`move`/`convert`/...) for programmatic callers.
- Persistent local cache with incremental `/sync` deltas, TTL-deduped reads, mutation-forced refresh.
- ID-prefix resolver (4+ hex) for short batch commands at the CLI layer.
- Fail-fast batch resolution — a typo or ambiguous prefix aborts the batch *before* any mutation runs.
- Project / notebook semantics: `item set --parent <pid>` with auto-promote out of Inbox/Trash/Archived (`list ∈ {i,d,r}`) so newly attached items render in the project view.
- Tag helpers: `resolve_tag(name)` (catalogue lookup by title), `add_tags`/`remove_tags`/`set_tags_by_name` (CLI `item tag add/remove/set`), and `item list --tag` filtering on `effective_tags`.
- `sync status` (server time + clock drift + last sync + cache size), full backup dump (`/pull` → file).

## Intentionally NOT implemented

- **`/push` and `/wipe`** — these wipe or overwrite the entire database from the client side. Wrong shape for a manual client; the desktop server should remain authoritative. If you need to bulk-restore, use the desktop client's import flow.

## TODO / ideas

- **Tag creation.** `resolve_tag(name)` (lookup) and the add/remove/set helpers exist; what is still missing is `create_tag(name, color=...) -> tag_obj` — writing through `changes.tags` on `/sync` so the CLI could mint a new tag instead of erroring on an unknown title.
- **Smarter conflict diagnostics.** When a mutation returns with a different `changed_ts` than expected (someone else edited the item between our read and write), the library currently overwrites silently. Could detect and surface a warning.

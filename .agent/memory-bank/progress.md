# Progress

## Implemented

- Full CRUD on items via `/sync`: create, mutate (list/type/parent/title/note/due/focus/complete), trash (soft delete), delete (permanent + tombstone).
- Typer-based `noun verb --params` CLI (`item` / `tag` / `project` / `notebook` / `sync` / `config`); field setters collapsed into a single `item set`; global `--json` with structured `{"error": ...}` output. The library API keeps the granular wrappers (`rename`/`move`/`convert`/...) for programmatic callers.
- Persistent local cache with incremental `/sync` deltas, TTL-deduped reads, mutation-forced refresh.
- ID-prefix resolver (4+ hex) for short batch commands at the CLI layer.
- Fail-fast batch resolution — a typo or ambiguous prefix aborts the batch *before* any mutation runs.
- Project / notebook semantics: `item set --parent <pid>` with auto-promote out of Inbox/Trash/Archived (`list ∈ {i,d,r}`) so newly attached items render in the project view.
- Tag helpers: `resolve_tag(name)` (catalogue lookup by title), `ensure_tag(title, *, type, color)` (opt-in creation through `changes.tags`), `add_tags`/`remove_tags`/`set_tags_by_name` (CLI `item tag add/remove/set`), and `item list --tag` filtering on `effective_tags`. Lookup helpers stay strict (raise on unknown title); only `ensure_tag` mints a tag.
- `sync status` (server time + clock drift + last sync + cache size), full backup dump (`/pull` → file).
- Config factory in `everdo.config` — single source of truth for the `flag > env (EVERDO_*) > config-file > default` precedence: `load_config`/`save_config` (0600, atomic), `resolve_setting`/`resolve_credentials`, and `load_tasks(...)` / `EverdoTasks.from_config(...)` (extra kwargs flow to `EverdoClient`). `MissingConfigError` (an `EverdoError`) when host/key absent. `everdo_cli.py` and embedding programs (classifier) both build their `EverdoTasks` through it instead of duplicating loader logic.

## Intentionally NOT implemented

- **`/push` and `/wipe`** — these wipe or overwrite the entire database from the client side. Wrong shape for a manual client; the desktop server should remain authoritative. If you need to bulk-restore, use the desktop client's import flow.

## TODO / ideas

- ~~**Tag creation.**~~ Done: `ensure_tag(title, *, type="a", color=0xCCCCCC) -> tag_obj` writes through `changes.tags` on `/sync` (mirrors `create()`: sync → `_apply` → `_post_mutation`). It is the *only* tag-minting entry point and is opt-in by design — `resolve_tag`/`add_tags` stay strict and still raise on unknown titles so a typo never mints a junk tag. Verified live (create, server persistence, color round-trip, idempotency).
- **Smarter conflict diagnostics.** When a mutation returns with a different `changed_ts` than expected (someone else edited the item between our read and write), the library currently overwrites silently. Could detect and surface a warning.

# Data model

Everything the CLI touches is an **item**. Four concepts describe it: **type** (what it is), **list** (where it lives), **parent_id** (what it belongs to), and **tags** (cross-cutting labels). Actions, projects, notes and notebooks are all items — they differ only by `type`, which is why a single `item` noun handles them all.

## list

Where the item lives. Single-letter code on the wire; the CLI accepts the friendly name everywhere a list is taken (`item set --list`, `item create --list`, `item list --list`):

| code | friendly  | meaning              |
|------|-----------|----------------------|
| `i`  | inbox     | Inbox                |
| `a`  | next      | Next                 |
| `s`  | scheduled | Scheduled            |
| `w`  | waiting   | Waiting              |
| `m`  | someday   | Someday              |
| `d`  | trash     | Trash (soft-deleted) |
| `r`  | archived  | Archived             |

**Not every list is legal for every type.** Actions and projects use all of the
above. Notes and notebooks (the note family) only ever live in `next` (`a`, the
visible/active state), `trash` (`d`) or `archived` (`r`) — the desktop app has no
UI to put them in inbox or an action-scheduling list (someday/scheduled/waiting),
and an item written into such a state is hidden in the notebook view. The CLI
enforces this: `item create`/`item set` reject an illegal type/list combination,
and a new note/notebook defaults to `next` (not `inbox`).

## type

The CLI takes the friendly name (`item create --type`, `item set --type`, `item list --type`):

| friendly | code | meaning                                  |
|----------|------|------------------------------------------|
| action   | `a`  | action (default)                         |
| project  | `p`  | project (container for actions)          |
| note     | `n`  | note (lives in a notebook)               |
| notebook | `l`  | notebook (container for notes)           |

Only these four types exist.

## parent_id

Links an item to its parent — an action to a project, or a note to a notebook. Same field for both. Set it with `item set --parent <ID>` (or `--parent none` to detach), never by hand-editing.

## tags

Tags are separate entities owned by the server (`{id, title, type}`), referenced by **title**. They are cross-cutting — independent of list/type/parent. The catalogue is read-only from the CLI (`tag list`); you attach/detach them per item with `item tag add/remove/set` and filter with `item list --tag <title>`. An unknown title is an error — create the tag in Everdo first; the CLI never auto-creates tags. See [mutating.md](mutating.md).

## IDs: prefixes accepted everywhere

Wherever the CLI takes an item id (`<ID>`), you may pass a **prefix of 4+ hex characters** instead of the full 32-char id. The CLI resolves it against the local cache:

- unique prefix → resolved to the full id and the command runs.
- ambiguous → error lists the matching ids; pick a longer prefix.
- no match → error `no item matches id prefix '...'`.
- shorter than 4 chars → error `id prefix '...' too short`.

This shortens batch commands a lot:

```
everdo-cli item trash AB12 CD34 EF56
```

The first 6–8 hex chars are almost always unique.

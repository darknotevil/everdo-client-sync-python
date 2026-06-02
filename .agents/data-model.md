# Data model

Three concepts cover everything the CLI does: **list** (where an item lives), **type** (what it is), and **parent_id** (what it belongs to).

## list

Where the item lives. Single-letter code on the wire; friendly names accepted by `move`:

| code | friendly  | meaning              |
|------|-----------|----------------------|
| `i`  | inbox     | Inbox                |
| `a`  | next / active | Next                 |
| `s`  | scheduled | Scheduled            |
| `w`  | waiting   | Waiting              |
| `m`  | someday   | Someday              |
| `d`  | trash     | Trash (soft-deleted) |
| `r`  | archived  | Archived             |

## type

| code | meaning                                  |
|------|------------------------------------------|
| `a`  | action (default)                         |
| `p`  | project (container for actions)          |
| `n`  | note (lives in a notebook)               |
| `l`  | notebook (container for notes)           |

Only these four are valid type codes.

## parent_id

Links an item to its parent — an action to a project, or a note to a notebook. Same field for both. Set it with `assign`, never by hand-editing.

## IDs: prefixes accepted everywhere

Wherever the CLI takes an item id (`<ID>`), you may pass a **prefix of 4+ hex characters** instead of the full 32-char id. The CLI resolves it against the local cache:

- unique prefix → resolved to the full id and the command runs.
- ambiguous → error lists the matching ids; pick a longer prefix.
- no match → error `no item matches id prefix '...'`.
- shorter than 4 chars → error `id prefix '...' too short`.

This shortens batch commands a lot:

```
./everdo_cli.py trash AB12 CD34 EF56
```

The first 6–8 hex chars are almost always unique.

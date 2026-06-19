# Projects & notebooks

A project (type `project`) contains actions; a notebook (type `notebook`) contains notes. Both use the **same** `parent_id` field, so the same commands handle both.

## Read

```
everdo-cli project list                     # open projects
everdo-cli project items <PROJECT_ID>       # items attached to a project
everdo-cli notebook list                    # notebooks
everdo-cli notebook items <NOTEBOOK_ID>     # notes attached to a notebook
everdo-cli project items none               # orphans (no parent)
```

## Attach / detach

`parent_id` is changed with `item set --parent`. It is single-id; to attach several items, loop:

```
everdo-cli item set <ITEM_ID> --parent <PROJECT_OR_NOTEBOOK_ID>   # attach
everdo-cli item set <ITEM_ID> --parent none                       # detach
for id in AB12 CD34 EF56; do everdo-cli item set "$id" --parent <PROJECT_ID>; done
```

## Auto-promote rule

Actions in Inbox, Trash, or Archived (`list ∈ {i, d, r}`) do **NOT** render in a project view even if `parent_id` is set.

`item set --parent` auto-promotes such items to Next (`list=next`); you don't have to do that yourself. To pick a different target list in the same call, pass `--list` alongside `--parent`:

```
everdo-cli item set <ID> --parent <PROJECT_ID> --list waiting
```

Or use the library API: `move_to_project(id, pid, list='w')`.

**Notes are stricter than actions.** A note in a notebook is only rendered when its `list` is `next` (`a`); notes have no someday/scheduled/waiting state. The CLI defaults a new note to `next` and refuses to move a note into an action-scheduling list, so don't pass `--list someday|scheduled|waiting` for notes — use `next` (active), or `trash`/`archived`.

## list vs parent — don't confuse them

- `--list` changes **where it lives** (Inbox / Next / Waiting / ...).
- `--parent` changes **which project/notebook contains it**.

To put something *into* a project you need `--parent`, not `--list`.

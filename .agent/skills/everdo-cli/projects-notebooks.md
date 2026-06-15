# Projects & notebooks

```
./everdo_cli.py assign --to <PROJECT_OR_NOTEBOOK_ID> <ITEM_ID> [<ITEM_ID>...]   # attach (batch)
./everdo_cli.py assign --to none                     <ITEM_ID> [<ITEM_ID>...]   # detach (batch)
```

`assign` is the right command for putting an action under a project AND for putting a note under a notebook (`parent_id` is the same field for both).

## Auto-promote rule

Items in Inbox, Trash, or Archived (`list ∈ {i, d, r}`) do **NOT** render in project/notebook views even if `parent_id` is set.

`assign` auto-promotes such items to Next (`list='a'`); you don't have to do that yourself. If you need a different target list (e.g., Waiting):

```
./everdo_cli.py assign --to <PROJECT_ID> <ID>
./everdo_cli.py move   --to waiting      <ID>
```

Or use the library API: `move_to_project(id, pid, list='w')`.

## move vs assign

These are different operations — don't confuse them.

- `move` changes the **list** field only (where it lives: Inbox / Next / Waiting / ...).
- `assign` changes the **parent_id** field (which project/notebook contains it).

To put something into a project, you need `assign`, not `move`.

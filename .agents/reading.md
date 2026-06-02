# Reading

Two output modes: **compact** (one line per item, only id/list/type/title) and **JSON** (full item with all fields including `note`, `due_date`, `parent_id`, `tags`, `completed_on`, `created_on`, ...).

## Compact

Fast scan of what's there:

```
./everdo_cli.py list                           # all items
./everdo_cli.py list --list i --no-completed   # inbox, open only
./everdo_cli.py list --type p                  # all projects
./everdo_cli.py list --type l                  # all notebooks
./everdo_cli.py find "<substring>"             # case-insensitive title search
./everdo_cli.py projects                       # open projects (alias for list --type p)
./everdo_cli.py children <PROJECT_OR_NOTEBOOK_ID>   # items whose parent_id == that
./everdo_cli.py children none                  # orphans (no parent)
```

## JSON

Use whenever you need fields beyond the title (notes, due dates, deduplication, filtering by tag, etc.):

```
./everdo_cli.py list --list i --json           # full items in inbox
./everdo_cli.py list --type p --json           # full projects
./everdo_cli.py find "<substring>" --json      # full matches
./everdo_cli.py get <ID>                       # one item, always JSON
```

**Rule of thumb:** if you would need to call `get` more than once after a `list`, you wanted `list --json` instead — it returns the same fields for every item in a single call.

## Server time

```
./everdo_cli.py time                           # server time (ms)
```

Also useful as a connectivity / auth check — if `time` works, config and network are fine.

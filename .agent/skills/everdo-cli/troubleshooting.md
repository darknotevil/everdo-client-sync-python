# Troubleshooting & anti-patterns

## When commands fail

- `error: no item matches id prefix '<X>'` — id/prefix is wrong, or the cache is stale. Run `./everdo_cli.py refresh --force` and retry. If still missing, the item was deleted on the server.
- `error: ambiguous id prefix '<X>': ...` — your prefix matches >1 item. The error lists the candidates; pass a longer prefix.
- `error: id prefix '<X>' too short` — minimum length is 4 hex characters.
- `error: item not found: <ID>` — same as above but raised from inside a mutation; usually means the cache was repopulated and your id is gone.
- `BLOCKED` / "user denied this command" — the user has not approved the action. **Stop.** Tell the user exactly which command on which item you were about to run, and ask for confirmation. Do not retry the same command and do not paraphrase it into a different one.
- `HTTP 400/401/...` — almost always config or network. Check `./everdo_cli.py config show` and `./everdo_cli.py time`. If `time` works, config is fine and the request body is the problem (likely an item field the server doesn't like).
- The command printed nothing — the cache may be empty. `./everdo_cli.py refresh` forces a fresh pull.

## Things to NOT do

- **Don't `delete --permanent` to "remove from a project"** — that wipes the item irreversibly. Use `assign --to none <ID>` to detach, or `trash <ID>` if you also want it out of the way.
- **Don't reach for `delete --permanent` during routine triage.** Use `trash`. `delete --permanent` is for cleaning up known-junk items (duplicates already merged, accidentally synced test data), not for "I'm done with this task".
- **Don't use `move` to put something into a project.** `move` only changes the `list` field. Use `assign --to <PROJECT_ID> <ID>`. See [projects-notebooks.md](projects-notebooks.md).
- **Don't create a notebook/project in inbox** (`--list i`) — they belong in Next (`--list a`) or another active list, otherwise the desktop client treats them oddly.

# Troubleshooting & anti-patterns

## When commands fail

- `error: no item matches id prefix '<X>'` — id/prefix is wrong, or the cache is stale. Run `everdo-cli sync refresh --force` and retry. If still missing, the item was deleted on the server.
- `error: ambiguous id prefix '<X>': ...` — your prefix matches >1 item. The error lists the candidates; pass a longer prefix.
- `error: id prefix '<X>' too short` — minimum length is 4 hex characters.
- `error: item not found: <ID>` — same as above but raised from inside a mutation; usually means the cache was repopulated and your id is gone.
- `error: unknown tag '<X>'; create it in Everdo first` — tags are referenced by title and must already exist. Run `everdo-cli tag list` to see the exact titles; the CLI never auto-creates tags (a typo must not mint one). Programmatic callers that *want* to create a tag use the library's `tasks.ensure_tag(title)`.
- `error: cannot reach Everdo server: ...` — network/host problem. Check the server is up and `everdo-cli config show` points at it.
- `BLOCKED` / "user denied this command" — the user has not approved the action. **Stop.** Tell the user exactly which command on which item you were about to run, and ask for confirmation. Do not retry the same command and do not paraphrase it into a different one.
- `HTTP 400/401/...` — almost always config or network. Check `everdo-cli config show` and `everdo-cli sync status`. If `sync status` works, config is fine and the request body is the problem (likely an item field the server doesn't like).
- The command printed nothing — the cache may be empty. `everdo-cli sync refresh` forces a fresh pull.

In `--json` mode (global flag before the noun) every error is also emitted as `{"error": "..."}` on stderr, so it can be parsed instead of scraped.

## Things to NOT do

- **Don't `item delete --permanent` to "remove from a project"** — that wipes the item irreversibly. Use `item set <ID> --parent none` to detach, or `item trash <ID>` if you also want it out of the way.
- **Don't reach for `item delete --permanent` during routine triage.** Use `item trash`. `item delete --permanent` is for cleaning up known-junk items (duplicates already merged, accidentally synced test data), not for "I'm done with this task".
- **Don't use `item set --list` to put something into a project.** `--list` only changes where it lives. Use `item set <ID> --parent <PROJECT_ID>`. See [projects-notebooks.md](projects-notebooks.md).
- **Don't `item tag set` when you mean `add`.** `set` replaces the whole tag list and drops tags you didn't name; `item tag add`/`remove` are the safe, additive operations.
- **Don't create a notebook/project in inbox** (`--list inbox`) — they belong in Next (`--list next`) or another active list, otherwise the desktop client treats them oddly.

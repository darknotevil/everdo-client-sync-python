# Reading

Two output modes: **compact** (the default — one line per item, only id/list/type/title) and **JSON** (full item with all fields including `note`, `due_date`, `parent_id`, `tags`, `effective_tags`, `completed_on`, `created_on`, ...). JSON is enabled by the global `--json` flag, which goes **before the noun**.

## Compact

Fast scan of what's there:

```
everdo-cli item list                          # active items (default: not completed, not archived/trash)
everdo-cli item list --status all             # everything, incl. completed + archive/trash
everdo-cli item list --status completed       # only completed items
everdo-cli item list --list archived          # the archive (auto --status all unless overridden)
everdo-cli item list --type project           # active projects
everdo-cli item list --type notebook          # all notebooks
everdo-cli item list --tag "<title>"          # items carrying a tag (incl. inherited)
everdo-cli item find "<substring>"            # case-insensitive title search
everdo-cli project list                       # open projects
everdo-cli project items <PROJECT_ID>         # items whose parent_id == that project
everdo-cli project items none                 # orphans (no parent)
everdo-cli notebook list                      # notebooks
everdo-cli notebook items <NOTEBOOK_ID>       # notes in that notebook
everdo-cli tag list                           # the tag catalogue
```

`item get <ID>` prints one item as a readable field block (id, title, type, list, parent, due, tags, note).

## JSON

Use whenever you need fields beyond the title (notes, due dates, deduplication, machine parsing, etc.). **`--json` is a global flag — put it BEFORE the noun, never at the end of the line** (`everdo-cli item list ... --json` fails with "No such option: --json"):

```
everdo-cli --json item list --list inbox      # full items in inbox
everdo-cli --json item list --type project    # full projects
everdo-cli --json item find "<substring>"     # full matches
everdo-cli --json item get <ID>               # one full item
```

In `--json` mode every command — reads, mutations, and even errors (`{"error": ...}` on stderr) — emits JSON, so it is the channel to use when parsing output programmatically.

**Rule of thumb:** if you would need to call `item get` more than once after a `list`, you wanted `--json item list` instead — it returns the same fields for every item in a single call.

## Connectivity / status

```
everdo-cli sync status                        # server time, clock drift, last sync, cache size
```

Also the quickest connectivity / auth check — if `sync status` works, config and network are fine.

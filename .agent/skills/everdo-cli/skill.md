---
name: everdo-cli
description: Read and modify tasks/projects/notebooks on a self-hosted Everdo server via the everdo-cli command-line tool. Use when an agent needs to triage an inbox, sort tasks into projects, convert items between types, or otherwise drive Everdo programmatically.
---

# everdo-cli

CLI is invoked as `everdo-cli` once the `everdo-client-sync-python` repo is installed (`uv tool install .` from the repo root). Without an install, the same CLI is reachable as `./everdo_cli.py` from the repo root — every example below works identically with either form. Every invocation is short-lived; reads are served from a local cache that auto-syncs incrementally.

## Command shape

The surface is **`everdo-cli <noun> <verb> [--params]`**. Nouns:

| noun | what it covers |
|------|----------------|
| `item` | every item — actions, projects, notes, notebooks (type is a flag) |
| `item tag` | the tags attached to one item |
| `tag` | the tag catalogue (read-only) |
| `project` | list projects and their items (read-only convenience) |
| `notebook` | list notebooks and their items (read-only convenience) |
| `sync` | `refresh` / `changes` / `backup` / `status` (server + cache plumbing) |
| `config` | `show` / `set` persisted CLI config |

A global **`--json`** switches every command to machine-readable JSON, including a `{"error": ...}` envelope on stderr. `--help` works on every noun and verb.

> ⚠️ **`--json` goes BEFORE the noun, never at the end.** It is a global flag on the root, not on the subcommand, so it must precede `item`/`project`/etc. — exactly like `git --no-pager log`.
> ```
> everdo-cli --json item list --status active     # ✅ correct
> everdo-cli item list --status active --json      # ❌ "No such option: --json"
> ```

For setup and config precedence, see the root [AGENTS.md](../../../AGENTS.md).

## Topical guides

- [data-model.md](data-model.md) — lists, types, parent_id, tags, ID prefixes
- [reading.md](reading.md) — listing, searching, JSON vs compact
- [mutating.md](mutating.md) — create/set/complete/tag/etc., batch behavior
- [projects-notebooks.md](projects-notebooks.md) — attaching items, auto-promote rule
- [cache.md](cache.md) — refresh, state file, drift recovery
- [recipes.md](recipes.md) — common end-to-end workflows
- [troubleshooting.md](troubleshooting.md) — errors and anti-patterns

---
name: everdo-cli
description: Read and modify tasks/projects/notebooks on a self-hosted Everdo server via the everdo_cli.py command-line tool. Use when an agent needs to triage an inbox, sort tasks into projects, convert items between types, or otherwise drive Everdo programmatically.
---

# everdo-cli

CLI lives at `everdo-client-sync-python/everdo_cli.py`. Every invocation is short-lived; reads are served from a local cache that auto-syncs incrementally.

For setup and config precedence, see the root [AGENTS.md](../AGENTS.md).

## Topical guides

- [data-model.md](data-model.md) — lists, types, parent_id, ID prefixes
- [reading.md](reading.md) — listing, searching, JSON vs compact
- [mutating.md](mutating.md) — create/complete/move/convert/assign/etc., batch behavior
- [projects-notebooks.md](projects-notebooks.md) — attaching items, auto-promote rule
- [cache.md](cache.md) — refresh, state file, drift recovery
- [recipes.md](recipes.md) — common end-to-end workflows
- [troubleshooting.md](troubleshooting.md) — errors and anti-patterns

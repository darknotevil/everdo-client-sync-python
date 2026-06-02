# everdo-client-sync-python

Python client + CLI for a self-hosted Everdo server. Uses the `/sync` protocol (not the create-only `/api/items`) so it can read, mutate, and delete items, backed by a persistent local cache (`everdo/.everdo_state.json`).

## Setup

- Python 3.10+, `requests`.
- One-time config:

  ```
  ./everdo_cli.py config set --host <ip:port> --key <API_KEY>
  ```

  After this, no flags or env vars are needed. Precedence: `--flag` > env (`EVERDO_HOST` / `EVERDO_KEY` / `EVERDO_VERSION`) > config file.

## Agent guides

Load only what the current task needs:

- [.agents/skill.md](.agents/skill.md) — skill manifest / entry point
- [.agents/data-model.md](.agents/data-model.md) — lists, types, parent_id, ID prefixes
- [.agents/reading.md](.agents/reading.md) — listing, searching, JSON vs compact
- [.agents/mutating.md](.agents/mutating.md) — create/complete/move/convert/assign/etc., batch behavior
- [.agents/projects-notebooks.md](.agents/projects-notebooks.md) — attaching items, auto-promote rule
- [.agents/cache.md](.agents/cache.md) — refresh, state file, drift recovery
- [.agents/recipes.md](.agents/recipes.md) — common end-to-end workflows
- [.agents/troubleshooting.md](.agents/troubleshooting.md) — errors and anti-patterns

## Project internals (for contributors)

- [.agents/memory-bank/](.agents/memory-bank/) — architecture, sync protocol, tech stack, roadmap

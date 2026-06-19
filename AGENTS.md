# everdo-client-sync-python

Python client + CLI for a self-hosted Everdo server. Uses the `/sync` protocol (not the create-only `/api/items`) so it can read, mutate, and delete items, backed by a persistent local cache (`~/.config/everdo/state.json`, XDG-respecting).

## Setup

- Python 3.10+, `requests`, `typer`.
- Install once (puts `everdo-cli` on `$PATH`):

  ```
  uv tool install .
  ```

  Without an install, the CLI is also reachable as `./everdo_cli.py` from the repo root — every example in this guide works identically with either form.

- One-time config:

  ```
  everdo-cli config set --host <ip:port> --key <API_KEY>
  ```

  After this, no flags or env vars are needed. Precedence: `--flag` > env (`EVERDO_HOST` / `EVERDO_KEY` / `EVERDO_VERSION`) > config file.

### Config file locations

The CLI looks for its config in this order (first existing file wins):

1. `--config <path>` — explicit override via CLI flag
2. `$XDG_CONFIG_HOME/everdo/config.json` (or `~/.config/everdo/config.json` if `XDG_CONFIG_HOME` is unset) — XDG Base Directory default
3. `<repo-root>/.config/everdo/config.json` — portable, per-checkout fallback

When saving (`config set`), the config is written to whichever path was used for reading.
If no config exists yet, it defaults to the XDG location.

## Agent guides

Load only what the current task needs:

- [.agent/skills/everdo-cli/skill.md](.agent/skills/everdo-cli/skill.md) — skill manifest / entry point
- [.agent/skills/everdo-cli/data-model.md](.agent/skills/everdo-cli/data-model.md) — lists, types, parent_id, ID prefixes
- [.agent/skills/everdo-cli/reading.md](.agent/skills/everdo-cli/reading.md) — listing, searching, JSON vs compact
- [.agent/skills/everdo-cli/mutating.md](.agent/skills/everdo-cli/mutating.md) — create/complete/move/convert/assign/etc., batch behavior
- [.agent/skills/everdo-cli/projects-notebooks.md](.agent/skills/everdo-cli/projects-notebooks.md) — attaching items, auto-promote rule
- [.agent/skills/everdo-cli/cache.md](.agent/skills/everdo-cli/cache.md) — refresh, state file, drift recovery
- [.agent/skills/everdo-cli/recipes.md](.agent/skills/everdo-cli/recipes.md) — common end-to-end workflows
- [.agent/skills/everdo-cli/troubleshooting.md](.agent/skills/everdo-cli/troubleshooting.md) — errors and anti-patterns

## Project internals (for contributors)

- [.agent/memory-bank/](.agent/memory-bank/) — architecture, sync protocol, tech stack, roadmap

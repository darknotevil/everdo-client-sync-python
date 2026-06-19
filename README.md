# Everdo client (Python)

Python client + CLI for a self-hosted [Everdo](https://everdo.net) server. Unlike the official `/api/items` endpoint (create-only), this client speaks the regular `/sync` protocol and can **read, mutate, and delete** existing items while remaining a regular client (not a master server).

A persistent local cache (`~/.config/everdo/state.json`, XDG-respecting) keeps state warm across short-lived CLI invocations and dedups incidental reads within a single agent tick.

## Requirements

- Python 3.10+ with `requests` and `typer`
- Everdo `>= v1.0.6-3` in Server mode (Settings → Sync → Server → API)

## Setup

Install the CLI (puts `everdo-cli` on your `$PATH`):

```
uv tool install .
```

Then configure host/key:

```
everdo-cli config set --host <HOST:PORT> --key <API_KEY>
everdo-cli config show          # key is masked
```

Precedence: `--flag` > env (`EVERDO_HOST` / `EVERDO_KEY` / `EVERDO_VERSION`) > config file.

> Without an install, the same CLI is reachable as `./everdo_cli.py` from the repo root — every example below works identically with either form.

## CLI quick-start

The surface is `everdo-cli <noun> <verb> [--params]`. Nouns: `item`, `tag`,
`project`, `notebook`, `sync`, `config`.

```
everdo-cli item list --no-completed
everdo-cli item find "milk"
everdo-cli item create "Buy milk" --list inbox --note "2%"
everdo-cli item set <ID> --list next            # move to Next
everdo-cli item complete <ID>
everdo-cli --json item list --list inbox        # JSON output (flag goes before the noun)
```

IDs accept 4+ hex-character prefixes. `--help` works on every noun and verb.

## Library quick-start

```python
from everdo import EverdoClient, EverdoTasks

tasks = EverdoTasks(EverdoClient("<HOST:PORT>", key="<API_KEY>"))
tid = tasks.create("Buy milk", note="2%", list="i")
tasks.move(tid, "a")                    # to Next
tasks.move_to_project(tid, project_id)
tasks.complete(tid)
```

## Docs

- [AGENTS.md](AGENTS.md) — full CLI reference for an agent or user driving Everdo.
- [.agent/memory-bank/](.agent/memory-bank/) — architecture, sync protocol, tech stack, roadmap.

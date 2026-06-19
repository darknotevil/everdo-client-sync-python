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

`EverdoTasks.from_config()` builds the client from the same `flag > env > config-file > default`
precedence the CLI uses, so an embedding program needs no connection boilerplate (pass
`host=`/`key=`/`config_path=` to override). Build the transport by hand only if you want to:

```python
from everdo import EverdoTasks

tasks = EverdoTasks.from_config()              # or EverdoTasks(EverdoClient("<HOST:PORT>", key="<API_KEY>"))
tid = tasks.create("Buy milk", note="2%", list="i")
tasks.move(tid, "a")                           # to Next
tasks.move_to_project(tid, project_id)
tasks.complete(tid)
```

Tags are server-owned: lookup helpers (`resolve_tag`, `add_tags`, …) stay strict and raise on an
unknown title, so a typo never mints a junk tag. Use `ensure_tag` for explicit opt-in creation:

```python
tag = tasks.ensure_tag("~suggest/proj=x")      # return it, creating on the server if absent
tasks.add_tags(tid, ["~suggest/proj=x"])
```

Batch mutations cost **two `/sync` round-trips total** (one refresh + one write) regardless of N —
the way to touch many items without 2N serial calls (the shared `state.json` rules out parallelism):

```python
tasks.update_many({id1: {"list": "a"}, id2: {"completed_on": None}})
tasks.add_tags_many([id1, id2], ["finance"])
tasks.remove_tags_matching("~suggest/*")       # sweep a whole tag family from every item
```

## Docs

- [AGENTS.md](AGENTS.md) — full CLI reference for an agent or user driving Everdo.
- [.agent/memory-bank/](.agent/memory-bank/) — architecture, sync protocol, tech stack, roadmap.

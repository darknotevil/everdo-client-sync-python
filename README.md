# Everdo client (Python)

Python client + CLI for a self-hosted [Everdo](https://everdo.net) server. Unlike the official `/api/items` endpoint (create-only), this client speaks the regular `/sync` protocol and can **read, mutate, and delete** existing items while remaining a regular client (not a master server).

A persistent local cache (`~/.config/everdo/state.json`, XDG-respecting) keeps state warm across short-lived CLI invocations and dedups incidental reads within a single agent tick.

## Requirements

- Python 3.10+ with `requests`
- Everdo `>= v1.0.6-3` in Server mode (Settings → Sync → Server → API)

## Setup

```
./everdo_cli.py config set --host <HOST:PORT> --key <API_KEY>
./everdo_cli.py config show          # key is masked
```

Precedence: `--flag` > env (`EVERDO_HOST` / `EVERDO_KEY` / `EVERDO_VERSION`) > config file.

## CLI quick-start

```
./everdo_cli.py list --no-completed
./everdo_cli.py find "milk"
./everdo_cli.py create "Buy milk" --list i --note "2%"
./everdo_cli.py move --to next <ID>
./everdo_cli.py complete <ID>
```

IDs accept 4+ hex-character prefixes.

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

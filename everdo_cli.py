#!/usr/bin/env python3
"""Command-line front-end to the Everdo sync client.

Config is read from the environment (or flags):
    EVERDO_HOST     e.g. 127.0.0.1:11111
    EVERDO_KEY      server API key
    EVERDO_VERSION  client version sent to /sync (default 1.99.0)

Examples
--------
    export EVERDO_HOST=127.0.0.1:11111 EVERDO_KEY=YOURKEY
    ./everdo_cli.py list --no-completed
    ./everdo_cli.py find "milk"
    ./everdo_cli.py create "TEST-LLM hello" --list i
    ./everdo_cli.py complete <ID> [<ID>...]                # batch
    ./everdo_cli.py move --to next <ID> [<ID>...]          # batch
    ./everdo_cli.py trash <ID> [<ID>...]                   # soft delete; reversible
    ./everdo_cli.py delete <ID> [<ID>...] --permanent      # hard delete + tombstone
    ./everdo_cli.py backup /tmp/everdo_backup.json
    ./everdo_cli.py changes        # incremental pull since last sync

IDs may be passed as 4+ hex-character prefixes; the CLI resolves them against
the cache and errors out cleanly on ambiguity or no-match.
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from everdo import EverdoClient, EverdoError, EverdoTasks, LISTS  # noqa: E402
from everdo import paths  # noqa: E402


def _get_config_path(explicit_path=None) -> str:
    """Resolve config path.

    Priority (reading): ``--config`` flag > XDG > project-root ``.config``
    (see :mod:`everdo.paths`). Writes go to whichever location was found, or
    XDG if neither exists yet.
    """
    if explicit_path:
        return explicit_path
    return str(paths.config_path())


def _load_config(config_path=None) -> dict:
    path = _get_config_path(config_path)
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_config(cfg: dict, config_path=None) -> None:
    path = _get_config_path(config_path)
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(cfg, fh, ensure_ascii=False, indent=2)
    os.replace(tmp, path)
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass


def _resolve(name: str, cli_value, env_var: str, default=None, config_path=None):
    """Priority: CLI flag > env var > config file > default."""
    if cli_value:
        return cli_value
    env = os.environ.get(env_var)
    if env:
        return env
    cfg = _load_config(config_path)
    return cfg.get(name, default)


def _client(args) -> EverdoClient:
    host = _resolve("host", args.host, "EVERDO_HOST", config_path=getattr(args, "config", None))
    key = _resolve("key", args.key, "EVERDO_KEY", config_path=getattr(args, "config", None))
    version = _resolve("version", args.version, "EVERDO_VERSION", default="1.99.0", config_path=getattr(args, "config", None))
    if not host or not key:
        sys.exit(
            "error: host/key not configured. Run `./everdo_cli.py config set "
            "--host <ip:port> --key <API_KEY>`, or pass --host/--key, or set "
            "EVERDO_HOST/EVERDO_KEY."
        )
    return EverdoClient(host, key=key, version=version)


def _resolve_list(value: str) -> str:
    return LISTS.get(value, value)


def _print(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _fmt_item(it: dict) -> str:
    done = "x" if it.get("completed_on") else " "
    return f"[{done}] {it.get('id')}  list={it.get('list')} type={it.get('type')}  {it.get('title')!r}"


def _resolve_ids(tasks: EverdoTasks, raw_ids):
    """Resolve a list of (possibly-shortened) id prefixes via the cache.

    Validates *all* ids up front; if any can't be resolved, exits before doing
    any mutation. This way a batch is never half-applied because of a typo.
    """
    full, errors = [], []
    for raw in raw_ids:
        try:
            full.append(tasks.resolve_id(raw))
        except EverdoError as e:
            errors.append(str(e))
    if errors:
        sys.exit("error: " + "; ".join(errors))
    return full


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Everdo sync client")
    p.add_argument("--host")
    p.add_argument("--key")
    p.add_argument("--version", dest="version")
    p.add_argument("--config", dest="config", help="path to config file (overrides auto-detection)")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("time", help="server time")

    sp = sub.add_parser("backup", help="dump full DB to a file")
    sp.add_argument("path")

    sp = sub.add_parser("list", help="list items")
    sp.add_argument("--list", dest="flist")
    sp.add_argument("--type", dest="ftype")
    sp.add_argument("--no-completed", action="store_true")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("find", help="find items by title substring")
    sp.add_argument("text")
    sp.add_argument("--json", action="store_true")

    sp = sub.add_parser("get", help="show one item")
    sp.add_argument("id")

    sp = sub.add_parser("create", help="create a new item")
    sp.add_argument("title")
    sp.add_argument("--note")
    sp.add_argument("--list", dest="flist", default="i")
    sp.add_argument("--type", dest="ftype", default="a")
    sp.add_argument("--parent", help="parent item id (e.g. project or notebook)")

    # Batch verbs with no extra target. All accept 1..N ids; each id may be a
    # prefix (>=4 hex chars) as long as it's unambiguous in the cache.
    for name, help_ in [("complete", "mark done"), ("uncomplete", "mark not done"),
                        ("focus", "add to focus"), ("unfocus", "remove from focus"),
                        ("trash", "soft delete (move to Trash; reversible)")]:
        sp = sub.add_parser(name, help=help_)
        sp.add_argument("ids", nargs="+", metavar="ID")

    sp = sub.add_parser("delete", help="permanently delete items (requires --permanent)")
    sp.add_argument("ids", nargs="+", metavar="ID")
    sp.add_argument("--permanent", action="store_true",
                    help="confirm permanent + tombstone delete; without this flag the command refuses to run")

    # Batch verbs that need a target. Target goes through --to so it never
    # collides with the variable-length id list.
    sp = sub.add_parser("move", help="move items to a list")
    sp.add_argument("--to", dest="to", required=True,
                    help="target list: inbox/next/waiting/scheduled/someday/archived/trash or raw code")
    sp.add_argument("ids", nargs="+", metavar="ID")

    sp = sub.add_parser("convert", help="change item type")
    sp.add_argument("--to", dest="to", required=True, choices=["a", "p", "n", "l"],
                    help="target type: a=action, p=project, n=note, l=notebook")
    sp.add_argument("ids", nargs="+", metavar="ID")

    sp = sub.add_parser("assign", help="attach items to a project/notebook (or 'none' to detach)")
    sp.add_argument("--to", dest="to", required=True,
                    help="parent project/notebook id (prefix ok), or 'none' to detach")
    sp.add_argument("ids", nargs="+", metavar="ID")

    # Single-id verbs (no batching: the second arg is per-item).
    sp = sub.add_parser("rename", help="change title")
    sp.add_argument("id")
    sp.add_argument("title")

    sp = sub.add_parser("note", help="set note")
    sp.add_argument("id")
    sp.add_argument("note")

    sp = sub.add_parser("due", help="set due date (unix seconds, or 'none')")
    sp.add_argument("id")
    sp.add_argument("ts")

    sub.add_parser("changes", help="incremental pull since last sync")

    sp = sub.add_parser("refresh", help="refresh local cache from server")
    sp.add_argument("--force", action="store_true", help="bypass TTL")

    sub.add_parser("projects", help="list projects (items of type 'p')")

    sp = sub.add_parser("children", help="items attached to a project (or 'none' for orphans)")
    sp.add_argument("project_id")

    sp = sub.add_parser("config", help="show or set persisted CLI config")
    sp.add_argument("action", choices=["show", "set"])
    sp.add_argument("--host")
    sp.add_argument("--key")
    sp.add_argument("--version", dest="cfg_version")

    args = p.parse_args(argv)

    # `config` is the only command that doesn't need a live client.
    cfg_path = getattr(args, "config", None)
    if args.cmd == "config":
        if args.action == "show":
            cfg = _load_config(cfg_path)
            key = cfg.get("key")
            masked = (key[:3] + "***" + key[-2:]) if key and len(key) > 5 else ("***" if key else None)
            shown = {**cfg, "key": masked} if "key" in cfg else cfg
            print(f"config file: {_get_config_path(cfg_path)}")
            _print(shown)
        else:  # set
            cfg = _load_config(cfg_path)
            for field, value in (("host", args.host), ("key", args.key), ("version", args.cfg_version)):
                if value is not None:
                    cfg[field] = value
            if not cfg:
                sys.exit("error: nothing to set; pass --host/--key/--version")
            _save_config(cfg, cfg_path)
            print(f"saved to {_get_config_path(cfg_path)}")
        return 0

    tasks = EverdoTasks(_client(args))

    try:
        return _dispatch(args, tasks)
    except EverdoError as e:
        sys.exit(f"error: {e}")


def _dispatch(args, tasks: EverdoTasks) -> int:
    if args.cmd == "time":
        print(tasks.client.server_time_ms())
    elif args.cmd == "backup":
        data = tasks.client.pull()
        with open(args.path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, ensure_ascii=False, indent=2)
        print(f"saved {len(data.get('items', []))} items, "
              f"{len(data.get('tags', []))} tags to {args.path}")
    elif args.cmd == "list":
        items = tasks.find(list=_resolve_list(args.flist) if args.flist else None,
                           type=args.ftype,
                           include_completed=not args.no_completed)
        _print(items) if args.json else [print(_fmt_item(it)) for it in items]
    elif args.cmd == "find":
        items = tasks.find(args.text)
        _print(items) if args.json else [print(_fmt_item(it)) for it in items]
    elif args.cmd == "get":
        _print(tasks.get(tasks.resolve_id(args.id)))
    elif args.cmd == "create":
        extra = {"parent_id": args.parent} if args.parent else {}
        tid = tasks.create(args.title, note=args.note,
                           list=_resolve_list(args.flist), type=args.ftype, **extra)
        print(tid)
    elif args.cmd == "complete":
        for full in _resolve_ids(tasks, args.ids):
            print(_fmt_item(tasks.complete(full)))
    elif args.cmd == "uncomplete":
        for full in _resolve_ids(tasks, args.ids):
            print(_fmt_item(tasks.uncomplete(full)))
    elif args.cmd == "focus":
        for full in _resolve_ids(tasks, args.ids):
            print(_fmt_item(tasks.focus(full, True)))
    elif args.cmd == "unfocus":
        for full in _resolve_ids(tasks, args.ids):
            print(_fmt_item(tasks.focus(full, False)))
    elif args.cmd == "trash":
        for full in _resolve_ids(tasks, args.ids):
            print(_fmt_item(tasks.move(full, "d")))
    elif args.cmd == "move":
        target = _resolve_list(args.to)
        for full in _resolve_ids(tasks, args.ids):
            print(_fmt_item(tasks.move(full, target)))
    elif args.cmd == "convert":
        for full in _resolve_ids(tasks, args.ids):
            print(_fmt_item(tasks.update(full, type=args.to)))
    elif args.cmd == "assign":
        pid = None if args.to.lower() == "none" else tasks.resolve_id(args.to)
        for full in _resolve_ids(tasks, args.ids):
            print(_fmt_item(tasks.move_to_project(full, pid)))
    elif args.cmd == "rename":
        print(_fmt_item(tasks.rename(tasks.resolve_id(args.id), args.title)))
    elif args.cmd == "note":
        print(_fmt_item(tasks.set_note(tasks.resolve_id(args.id), args.note)))
    elif args.cmd == "due":
        due = None if args.ts.lower() == "none" else int(args.ts)
        print(_fmt_item(tasks.set_due(tasks.resolve_id(args.id), due)))
    elif args.cmd == "delete":
        if not args.permanent:
            sys.exit(
                "error: `delete` permanently wipes items and writes tombstones. "
                "Use `trash <ID> [...]` for a reversible soft-delete, "
                "or re-run with `delete <ID> [...] --permanent` if you really mean it."
            )
        for full in _resolve_ids(tasks, args.ids):
            tasks.delete(full)
            print(f"permanently deleted {full}")
    elif args.cmd == "changes":
        _print(tasks.pull_changes())
    elif args.cmd == "refresh":
        delta = tasks.refresh(force=args.force)
        print(f"items applied: {len(delta.get('items', []))}, "
              f"tags applied: {len(delta.get('tags', []))}, "
              f"deletions applied: {len(delta.get('deletions', []))}")
    elif args.cmd == "projects":
        projects = tasks.find_projects(include_completed=False)
        [print(_fmt_item(it)) for it in projects]
    elif args.cmd == "children":
        pid = None if args.project_id.lower() == "none" else tasks.resolve_id(args.project_id)
        items = tasks.children_of(pid)
        [print(_fmt_item(it)) for it in items]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

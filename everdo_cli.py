#!/usr/bin/env python3
"""Command-line front-end to the Everdo sync client.

Surface is ``everdo-cli <noun> <verb> [--params]``. Nouns:

    item       create/read/modify items of any type (action/project/note/notebook)
    item tag   add/remove/set the tags attached to an item
    tag        list the tag catalogue
    project    list projects and their items (read-only convenience)
    notebook   list notebooks and their items (read-only convenience)
    sync       refresh / changes / backup / status (server + cache plumbing)
    config     show / set the persisted CLI config

A global ``--json`` (placed before the noun) switches every command to
machine-readable JSON output, including a ``{"error": ...}`` envelope on stderr.

Config precedence: ``--flag`` > env (EVERDO_HOST / EVERDO_KEY / EVERDO_VERSION)
> config file. IDs may be passed as 4+ hex-character prefixes; they are resolved
against the local cache with a clean error on ambiguity or no-match.
"""

from __future__ import annotations

import json
import os
import sys
from enum import Enum
from typing import Annotated, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import typer  # noqa: E402
import requests  # noqa: E402

from everdo import EverdoClient, EverdoError, EverdoTasks  # noqa: E402
from everdo import paths  # noqa: E402


# --------------------------------------------------------------------- enums
class ListName(str, Enum):
    inbox = "inbox"
    next = "next"
    waiting = "waiting"
    scheduled = "scheduled"
    someday = "someday"
    archived = "archived"
    trash = "trash"


class ItemType(str, Enum):
    action = "action"
    project = "project"
    note = "note"
    notebook = "notebook"


_LIST_CODE = {
    "inbox": "i", "next": "a", "waiting": "w", "scheduled": "s",
    "someday": "m", "archived": "r", "trash": "d",
}
_TYPE_CODE = {"action": "a", "project": "p", "note": "n", "notebook": "l"}
_TYPE_NAME = {v: k for k, v in _TYPE_CODE.items()}
_LIST_NAME = {v: k for k, v in _LIST_CODE.items()}


# --------------------------------------------------------------- app state
# Populated by the root callback; the EverdoTasks client is built lazily so
# `config` works without a configured server.
state: dict = {"json": False, "host": None, "key": None, "version": None,
               "config": None, "tasks": None}


# --------------------------------------------------------------- config I/O
def _get_config_path(explicit_path=None) -> str:
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


def _tasks() -> EverdoTasks:
    """Build (once) and return the live EverdoTasks for server-backed commands."""
    if state["tasks"] is not None:
        return state["tasks"]
    cfgp = state["config"]
    host = _resolve("host", state["host"], "EVERDO_HOST", config_path=cfgp)
    key = _resolve("key", state["key"], "EVERDO_KEY", config_path=cfgp)
    version = _resolve("version", state["version"], "EVERDO_VERSION",
                       default="1.99.0", config_path=cfgp)
    if not host or not key:
        raise EverdoError(
            "host/key not configured. Run `everdo-cli config set "
            "--host <ip:port> --key <API_KEY>`, or pass --host/--key, or set "
            "EVERDO_HOST/EVERDO_KEY."
        )
    state["tasks"] = EverdoTasks(EverdoClient(host, key=key, version=version))
    return state["tasks"]


# --------------------------------------------------------------- id helpers
def _rid(t: EverdoTasks, prefix: str) -> str:
    return t.resolve_id(prefix)


def _resolve_ids(t: EverdoTasks, raw_ids) -> list[str]:
    """Resolve all id prefixes up front; raise before any mutation on error.

    This keeps a batch from being half-applied because of a single bad id.
    """
    full, errors = [], []
    for raw in raw_ids:
        try:
            full.append(t.resolve_id(raw))
        except EverdoError as e:
            errors.append(str(e))
    if errors:
        raise EverdoError("; ".join(errors))
    return full


# --------------------------------------------------------------- output
def _dump(obj) -> None:
    print(json.dumps(obj, ensure_ascii=False, indent=2))


def _fmt_item(it: dict) -> str:
    done = "x" if it.get("completed_on") else " "
    return (f"[{done}] {it.get('id')}  list={it.get('list')} "
            f"type={it.get('type')}  {it.get('title')!r}")


def _emit_item(it: dict) -> None:
    """Compact feedback for a single mutated item (full dict in --json)."""
    if state["json"]:
        _dump(it)
    else:
        print(_fmt_item(it))


def _emit_items(items: list[dict]) -> None:
    if state["json"]:
        _dump(items)
    else:
        for it in items:
            print(_fmt_item(it))


def _emit_detail(it: Optional[dict]) -> None:
    """Rich, human-readable view of one item (full dict in --json)."""
    if state["json"]:
        _dump(it)
        return
    if it is None:
        print("not found")
        return
    tname = _TYPE_NAME.get(it.get("type"), it.get("type"))
    lname = _LIST_NAME.get(it.get("list"), it.get("list"))
    tags = ", ".join(
        filter(None, ((t.get("title") if isinstance(t, dict) else t)
                      for t in (it.get("effective_tags") or it.get("tags") or [])))
    )
    print(f"id:        {it.get('id')}")
    print(f"title:     {it.get('title')!r}")
    print(f"type:      {it.get('type')} ({tname})")
    print(f"list:      {it.get('list')} ({lname})")
    print(f"parent_id: {it.get('parent_id') or '-'}")
    print(f"due_date:  {it.get('due_date') or '-'}")
    print(f"focused:   {bool(it.get('is_focused'))}")
    print(f"completed: {it.get('completed_on') or '-'}")
    print(f"tags:      {tags or '-'}")
    print(f"note:      {it.get('note') or '-'}")


def _emit_tags(tags: list[dict]) -> None:
    if state["json"]:
        _dump(tags)
    else:
        for tg in tags:
            print(f"{tg.get('title')!r}  type={tg.get('type')}  id={tg.get('id')}")


def _emit_obj(obj) -> None:
    if state["json"]:
        _dump(obj)
    else:
        _dump(obj)  # structured payloads stay JSON-shaped for readability


def _emit_msg(text: str, data: Optional[dict] = None) -> None:
    if state["json"]:
        _dump(data if data is not None else {"message": text})
    else:
        print(text)


# --------------------------------------------------------------- typer apps
app = typer.Typer(no_args_is_help=True, add_completion=False,
                  help="Everdo sync client (noun-verb CLI).")
item_app = typer.Typer(no_args_is_help=True,
                       help="Create, read and modify items of any type.")
item_tag_app = typer.Typer(no_args_is_help=True,
                           help="Manage the tags attached to an item.")
tag_app = typer.Typer(no_args_is_help=True, help="The tag catalogue (read-only).")
project_app = typer.Typer(no_args_is_help=True,
                          help="List projects and their items (read-only).")
notebook_app = typer.Typer(no_args_is_help=True,
                           help="List notebooks and their items (read-only).")
sync_app = typer.Typer(no_args_is_help=True, help="Server and local-cache plumbing.")
config_app = typer.Typer(no_args_is_help=True, help="Show or set persisted CLI config.")

app.add_typer(item_app, name="item")
item_app.add_typer(item_tag_app, name="tag")
app.add_typer(tag_app, name="tag")
app.add_typer(project_app, name="project")
app.add_typer(notebook_app, name="notebook")
app.add_typer(sync_app, name="sync")
app.add_typer(config_app, name="config")


@app.callback()
def _root(
    json_out: Annotated[bool, typer.Option("--json/--no-json", "-j",
                        help="Machine-readable JSON output for every command.")] = False,
    host: Annotated[Optional[str], typer.Option(help="Server ip:port (overrides env/config).")] = None,
    key: Annotated[Optional[str], typer.Option(help="API key (overrides env/config).")] = None,
    version: Annotated[Optional[str], typer.Option(help="Client version sent to /sync.")] = None,
    config: Annotated[Optional[str], typer.Option(help="Path to config file (overrides auto-detection).")] = None,
) -> None:
    state["json"] = json_out
    state["host"] = host
    state["key"] = key
    state["version"] = version
    state["config"] = config


# ----------------------------------------------------------------- item verbs
@item_app.command("create")
def item_create(
    title: Annotated[str, typer.Argument(help="Item title.")],
    note: Annotated[Optional[str], typer.Option(help="Note body.")] = None,
    list_: Annotated[ListName, typer.Option("--list", help="Target list.")] = ListName.inbox,
    type_: Annotated[ItemType, typer.Option("--type", help="Item type.")] = ItemType.action,
    parent: Annotated[Optional[str], typer.Option(help="Parent project/notebook id.")] = None,
    tag: Annotated[Optional[List[str]], typer.Option("--tag", help="Tag by title (repeatable).")] = None,
) -> None:
    """Create a new item; prints its id (full item in --json)."""
    t = _tasks()
    extra = {}
    if parent:
        extra["parent_id"] = _rid(t, parent)
    tags = [t.resolve_tag(n) for n in (tag or [])]
    tid = t.create(title, note=note, list=_LIST_CODE[list_.value],
                   type=_TYPE_CODE[type_.value], tags=tags or None, **extra)
    if state["json"]:
        _emit_item(t.get(tid))
    else:
        print(tid)


@item_app.command("get")
def item_get(id: Annotated[str, typer.Argument(help="Item id or 4+ hex prefix.")]) -> None:
    """Show one item in detail."""
    t = _tasks()
    _emit_detail(t.get(_rid(t, id)))


@item_app.command("list")
def item_list(
    list_: Annotated[Optional[ListName], typer.Option("--list", help="Filter by list.")] = None,
    type_: Annotated[Optional[ItemType], typer.Option("--type", help="Filter by type.")] = None,
    tag: Annotated[Optional[str], typer.Option("--tag", help="Filter by tag title.")] = None,
    no_completed: Annotated[bool, typer.Option("--no-completed", help="Hide completed items.")] = False,
) -> None:
    """List items, optionally filtered by list/type/tag."""
    t = _tasks()
    items = t.find(
        list=_LIST_CODE[list_.value] if list_ else None,
        type=_TYPE_CODE[type_.value] if type_ else None,
        tag=tag,
        include_completed=not no_completed,
    )
    _emit_items(items)


@item_app.command("find")
def item_find(text: Annotated[str, typer.Argument(help="Case-insensitive title substring.")]) -> None:
    """Find items whose title contains TEXT."""
    t = _tasks()
    _emit_items(t.find(text))


@item_app.command("set")
def item_set(
    id: Annotated[str, typer.Argument(help="Item id or 4+ hex prefix.")],
    title: Annotated[Optional[str], typer.Option(help="New title.")] = None,
    note: Annotated[Optional[str], typer.Option(help="New note body.")] = None,
    due: Annotated[Optional[str], typer.Option(help="Due date (unix seconds, or 'none').")] = None,
    list_: Annotated[Optional[ListName], typer.Option("--list", help="Move to list.")] = None,
    parent: Annotated[Optional[str], typer.Option(help="Attach to project/notebook id, or 'none' to detach.")] = None,
    type_: Annotated[Optional[ItemType], typer.Option("--type", help="Convert type.")] = None,
) -> None:
    """Change one or more fields of an existing item."""
    t = _tasks()
    full = _rid(t, id)
    result = None

    # parent goes through move_to_project so the inbox->Next auto-promote rule
    # (and any explicit --list) is honoured exactly like the desktop client.
    if parent is not None:
        pid = None if parent.lower() == "none" else _rid(t, parent)
        list_code = _LIST_CODE[list_.value] if list_ else None
        result = t.move_to_project(full, pid, list=list_code)

    fields: dict = {}
    if title is not None:
        fields["title"] = title
    if note is not None:
        fields["note"] = note
    if due is not None:
        fields["due_date"] = None if due.lower() == "none" else int(due)
    if type_ is not None:
        fields["type"] = _TYPE_CODE[type_.value]
    if list_ is not None and parent is None:
        # when parent is set, the list was already handled by move_to_project
        fields["list"] = _LIST_CODE[list_.value]

    if fields:
        result = t.update(full, **fields)
    if result is None:
        raise EverdoError("nothing to set; pass at least one of "
                          "--title/--note/--due/--list/--parent/--type")
    _emit_item(result)


def _batch(ids: list[str], op) -> None:
    t = _tasks()
    out = [op(t, full) for full in _resolve_ids(t, ids)]
    _emit_items(out)


@item_app.command("complete")
def item_complete(ids: Annotated[List[str], typer.Argument(help="Item ids/prefixes.")]) -> None:
    """Mark items done."""
    _batch(ids, lambda t, f: t.complete(f))


@item_app.command("uncomplete")
def item_uncomplete(ids: Annotated[List[str], typer.Argument()]) -> None:
    """Mark items not done."""
    _batch(ids, lambda t, f: t.uncomplete(f))


@item_app.command("focus")
def item_focus(ids: Annotated[List[str], typer.Argument()]) -> None:
    """Star items (focus)."""
    _batch(ids, lambda t, f: t.focus(f, True))


@item_app.command("unfocus")
def item_unfocus(ids: Annotated[List[str], typer.Argument()]) -> None:
    """Unstar items."""
    _batch(ids, lambda t, f: t.focus(f, False))


@item_app.command("trash")
def item_trash(ids: Annotated[List[str], typer.Argument()]) -> None:
    """Soft-delete items (to Trash; reversible)."""
    _batch(ids, lambda t, f: t.move(f, "d"))


@item_app.command("delete")
def item_delete(
    ids: Annotated[List[str], typer.Argument()],
    permanent: Annotated[bool, typer.Option("--permanent",
               help="Required: permanently wipe items and write tombstones.")] = False,
) -> None:
    """Permanently delete items (requires --permanent)."""
    if not permanent:
        raise EverdoError(
            "`item delete` permanently wipes items and writes tombstones. "
            "Use `item trash <ID> [...]` for a reversible soft-delete, "
            "or re-run with `--permanent` if you really mean it."
        )
    t = _tasks()
    fulls = _resolve_ids(t, ids)
    for full in fulls:
        t.delete(full)
    _emit_msg(f"permanently deleted {len(fulls)} item(s): {', '.join(fulls)}",
              {"deleted": fulls})


# ----------------------------------------------------------- item tag verbs
@item_tag_app.command("add")
def item_tag_add(
    id: Annotated[str, typer.Argument(help="Item id or prefix.")],
    names: Annotated[List[str], typer.Argument(help="Tag titles (must exist in the catalogue).")],
) -> None:
    """Add tags to an item (idempotent; never clobbers existing tags)."""
    t = _tasks()
    _emit_item(t.add_tags(_rid(t, id), names))


@item_tag_app.command("remove")
def item_tag_remove(
    id: Annotated[str, typer.Argument()],
    names: Annotated[List[str], typer.Argument()],
) -> None:
    """Remove the named tags from an item."""
    t = _tasks()
    _emit_item(t.remove_tags(_rid(t, id), names))


@item_tag_app.command("set")
def item_tag_set(
    id: Annotated[str, typer.Argument()],
    names: Annotated[List[str], typer.Argument()],
) -> None:
    """Replace an item's tags with exactly the named ones."""
    t = _tasks()
    _emit_item(t.set_tags_by_name(_rid(t, id), names))


# ----------------------------------------------------------------- tag verbs
@tag_app.command("list")
def tag_list() -> None:
    """List all tags known to the server."""
    t = _tasks()
    _emit_tags(t.all_tags())


# ------------------------------------------------------------- project verbs
@project_app.command("list")
def project_list() -> None:
    """List open projects."""
    t = _tasks()
    _emit_items(t.find_projects(include_completed=False))


@project_app.command("items")
def project_items(
    id: Annotated[str, typer.Argument(help="Project id/prefix, or 'none' for orphans.")],
) -> None:
    """List items attached to a project."""
    t = _tasks()
    pid = None if id.lower() == "none" else _rid(t, id)
    _emit_items(t.children_of(pid))


# ------------------------------------------------------------ notebook verbs
@notebook_app.command("list")
def notebook_list() -> None:
    """List notebooks."""
    t = _tasks()
    _emit_items(t.find(type="l", include_completed=False))


@notebook_app.command("items")
def notebook_items(
    id: Annotated[str, typer.Argument(help="Notebook id/prefix, or 'none' for orphans.")],
) -> None:
    """List notes attached to a notebook."""
    t = _tasks()
    pid = None if id.lower() == "none" else _rid(t, id)
    _emit_items(t.children_of(pid))


# ---------------------------------------------------------------- sync verbs
@sync_app.command("refresh")
def sync_refresh(
    force: Annotated[bool, typer.Option("--force", help="Bypass the read TTL.")] = False,
) -> None:
    """Bring the local cache up to date with the server."""
    t = _tasks()
    delta = t.refresh(force=force)
    counts = {
        "items": len(delta.get("items", [])),
        "tags": len(delta.get("tags", [])),
        "deletions": len(delta.get("deletions", [])),
    }
    _emit_msg(f"items applied: {counts['items']}, tags applied: {counts['tags']}, "
              f"deletions applied: {counts['deletions']}", counts)


@sync_app.command("changes")
def sync_changes() -> None:
    """Show the latest incremental delta (diagnostic)."""
    t = _tasks()
    _emit_obj(t.pull_changes())


@sync_app.command("backup")
def sync_backup(path: Annotated[str, typer.Argument(help="Destination file.")]) -> None:
    """Dump the full server database to a file."""
    t = _tasks()
    data = t.client.pull()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    _emit_msg(
        f"saved {len(data.get('items', []))} items, {len(data.get('tags', []))} tags to {path}",
        {"items": len(data.get("items", [])), "tags": len(data.get("tags", [])), "path": path},
    )


@sync_app.command("status")
def sync_status() -> None:
    """Server time, clock drift, last sync and cache size."""
    t = _tasks()
    _emit_obj(t.status())


# -------------------------------------------------------------- config verbs
@config_app.command("show")
def config_show() -> None:
    """Show the persisted CLI config (key masked)."""
    cfg = _load_config(state["config"])
    key = cfg.get("key")
    masked = (key[:3] + "***" + key[-2:]) if key and len(key) > 5 else ("***" if key else None)
    shown = {**cfg, "key": masked} if "key" in cfg else cfg
    if state["json"]:
        _dump({"config_path": _get_config_path(state["config"]), **shown})
    else:
        print(f"config file: {_get_config_path(state['config'])}")
        _dump(shown)


@config_app.command("set")
def config_set(
    host: Annotated[Optional[str], typer.Option()] = None,
    key: Annotated[Optional[str], typer.Option()] = None,
    version: Annotated[Optional[str], typer.Option()] = None,
) -> None:
    """Persist host/key/version to the config file."""
    if host is None and key is None and version is None:
        raise EverdoError("nothing to set; pass --host/--key/--version")
    cfg = _load_config(state["config"])
    for field, value in (("host", host), ("key", key), ("version", version)):
        if value is not None:
            cfg[field] = value
    _save_config(cfg, state["config"])
    _emit_msg(f"saved to {_get_config_path(state['config'])}",
              {"saved_to": _get_config_path(state["config"])})


# --------------------------------------------------------------------- main
def _err(msg: str) -> None:
    if state["json"]:
        print(json.dumps({"error": msg}, ensure_ascii=False), file=sys.stderr)
    else:
        print(f"error: {msg}", file=sys.stderr)


def main(argv=None) -> int:
    # Typer 0.26 vendors its CLI engine (the historical `click`) as a private
    # module, so we catch by public typer exceptions + duck-typing instead of
    # importing `click`, which is no longer a top-level dependency.
    try:
        app(args=argv, standalone_mode=False)
        return 0
    except EverdoError as e:
        _err(str(e))
        return 1
    except requests.RequestException as e:
        _err(f"cannot reach Everdo server: {e}")
        return 1
    except typer.Abort:
        _err("aborted")
        return 1
    except SystemExit as e:
        code = e.code
        return code if isinstance(code, int) else (0 if code is None else 1)
    except BaseException as e:
        # Engine Exit (has exit_code) and usage errors (also expose .show()).
        code = getattr(e, "exit_code", None)
        if code is not None:
            show = getattr(e, "show", None)
            if callable(show):
                show()
            return int(code)
        raise


if __name__ == "__main__":
    raise SystemExit(main())

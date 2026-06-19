"""High-level task operations with a persistent local cache.

The cache is materialized from ``client.pull()`` on first use, then kept up to
date incrementally through ``client.sync()`` deltas. Reads (``all_items``,
``get``, ``find``, project helpers) go through the cache; an internal TTL
deduplicates incidental refreshes so a single agent "tick" of N reads costs
one HTTP round-trip. Mutations bypass the TTL to avoid read-modify-write
races against the desktop client.

Server merge stays last-write-wins: it takes the version with the greater
``changed_ts`` as the base and resolves individual fields by their paired
``*_ts``. Therefore an edit must send the **whole** item with a bumped
``changed_ts`` (and the paired ``*_ts`` of the changed fields), otherwise
unspecified fields would be lost.
"""

from __future__ import annotations

import fnmatch
import time
import uuid
from typing import Any, Callable

from .client import EverdoClient, EverdoError

# Lists (the "list" field) and item types, as used by the data model.
LISTS = {
    "inbox": "i",
    "next": "a",
    "active": "a",
    "waiting": "w",
    "scheduled": "s",
    "someday": "m",
    "archived": "r",
    "trash": "d",
}
TYPES = {"action": "a", "project": "p", "note": "n", "list": "l"}

# Lists that take an item out of circulation. An item in one of these is never
# "active", regardless of its completion flag.
ARCHIVE_LISTS = ("r", "d")
# Status filter values for ``find``. "active" mirrors the desktop default:
# not completed and not in archive/trash.
STATUSES = ("active", "completed", "all")


def is_active(item: dict[str, Any]) -> bool:
    """True when an item is open and in a working list (not archived/trash)."""
    return not item.get("completed_on") and item.get("list") not in ARCHIVE_LISTS

# Fields that have a regular "<field>_ts" companion (set when the field changes).
TS_FIELDS = {
    "title", "note", "type", "list", "is_focused", "completed_on", "due_date",
    "start_date", "energy", "time", "schedule", "parent_id", "contact_id",
    "notification_time", "num_parallel_actions",
    "position_global", "position_parent", "position_child", "position_focus",
}
# Irregular companion timestamps: field -> timestamp field.
IRREGULAR_TS = {"tags": "tags_changed_ts"}

# Server-derived / runtime-only fields that must not be written back.
DERIVED = {"is_existing_item", "effective_tags", "parent_ref", "contact_ref"}

# Lists each item type may legally occupy. Actions and projects are the
# actionable types and use the full set. Notes and notebooks (the note family)
# only ever live in Active/Trash/Archived in the desktop app -- it offers no way
# to put a note in Inbox or an action-scheduling list (Someday/Scheduled/
# Waiting). Writing such a state via the sync API produces a note the app cannot
# render in its notebook view, so we refuse it here instead of silently
# corrupting the database.
_ALL_LISTS = {"i", "a", "w", "s", "m", "d", "r"}
_NOTE_LISTS = {"a", "d", "r"}
LEGAL_LISTS = {"a": _ALL_LISTS, "p": _ALL_LISTS, "n": _NOTE_LISTS, "l": _NOTE_LISTS}

_LIST_LABEL = {
    "i": "inbox", "a": "next", "w": "waiting", "s": "scheduled",
    "m": "someday", "d": "trash", "r": "archived",
}
_TYPE_LABEL = {"a": "action", "p": "project", "n": "note", "l": "notebook"}


def _validate_list(item_type: str | None, list_code: str | None) -> None:
    """Reject a ``list`` value that is illegal for ``item_type``.

    Only constrains the note family (notes/notebooks); actions and projects
    accept every list. Unknown types are left alone so the guard never blocks a
    shape it does not understand.
    """
    legal = LEGAL_LISTS.get(item_type or "")
    if legal is None or list_code is None or list_code in legal:
        return
    t = _TYPE_LABEL.get(item_type, item_type)
    where = _LIST_LABEL.get(list_code, list_code)
    allowed = ", ".join(_LIST_LABEL.get(c, c) for c in ("a", "d", "r") if c in legal)
    raise EverdoError(
        f"cannot put a {t} in the {where} list; a {t} can only be in: {allowed}. "
        f"(The desktop app never creates this state and hides such items in the "
        f"notebook view.)"
    )


def _now() -> int:
    return int(time.time())


def _tag_title(tag: Any) -> str | None:
    """Extract a tag's title whether it is stored as a dict or a bare string."""
    if isinstance(tag, dict):
        return tag.get("title")
    return tag if isinstance(tag, str) else None


def new_sync_id() -> str:
    return uuid.uuid4().hex.upper()


class EverdoTasks:
    """Task operations layered on top of :class:`EverdoClient`, with a
    persistent local cache of items and tags.

    Parameters
    ----------
    client:
        Transport. The cache shares its ``state_path``.
    refresh_ttl:
        Seconds between automatic incremental refreshes. Reads within the
        TTL window reuse the in-memory cache. Mutations always force a
        refresh regardless of TTL. Set to ``0`` to refresh on every read,
        or a negative value to disable automatic refresh entirely.
    """

    def __init__(self, client: EverdoClient, *, refresh_ttl: float = 5.0) -> None:
        self.client = client
        self.refresh_ttl = refresh_ttl
        self._items: dict[str, dict[str, Any]] | None = None
        self._tags: dict[str, dict[str, Any]] | None = None
        self._last_refresh: float = 0.0

    @classmethod
    def from_config(cls, **kwargs: Any) -> "EverdoTasks":
        """Build from resolved config (``flag > env > config file > default``).

        Thin alias for :func:`everdo.config.load_tasks`; see it for the full
        keyword set (``host``/``key``/``version``/``config_path``/…).
        """
        from .config import load_tasks

        return load_tasks(**kwargs)

    # --------------------------------------------------------- cache plumbing
    def _load_cache(self) -> None:
        state = self.client._load_state()
        items = state.get("items")
        tags = state.get("tags")
        if isinstance(items, dict):
            self._items = dict(items)
        if isinstance(tags, dict):
            self._tags = dict(tags)

    def _save_cache(self, sync_ts: int | None = None) -> None:
        """Persist the cache, optionally advancing the sync cursor atomically.

        ``items``, ``tags`` and ``last_sync_ts`` land in a single state write
        (one ``os.replace``), so the durable cursor is never ahead of the
        durable items. A cursor left *behind* the items is harmless: the next
        sync merely re-delivers already-applied (idempotent, id-keyed) changes.
        """
        values: dict[str, Any] = {"items": self._items or {}, "tags": self._tags or {}}
        if sync_ts is not None:
            values["last_sync_ts"] = sync_ts
        self.client._save_state(**values)

    def _apply(
        self,
        items: list[dict] | None,
        tags: list[dict] | None,
        deletions: list[dict] | None,
    ) -> None:
        # Lazy-load from disk before mutating: create/delete reach _apply
        # without going through _refresh, so without this the in-memory dicts
        # would start empty and _save_cache would overwrite the disk file.
        if self._items is None or self._tags is None:
            self._load_cache()
            if self._items is None:
                self._items = {}
            if self._tags is None:
                self._tags = {}
        for it in items or []:
            sid = it.get("id") or it.get("sync_id")
            if sid:
                self._items[sid] = it
        for tg in tags or []:
            sid = tg.get("id") or tg.get("sync_id")
            if sid:
                self._tags[sid] = tg
        for d in deletions or []:
            # Tombstones key the deleted entity differently across channels
            # (``deletions_to_add`` from /sync, the ``deletions`` list from a
            # full /pull, and our own delete() dicts); accept either spelling.
            sid = d.get("sync_id") or d.get("id")
            if not sid:
                continue
            # Last-write-wins: a tombstone only evicts the item if it is not
            # older than the item's last change. An item modified *after* its
            # deletion ts was resurrected and must survive (a full /pull ships
            # the entire tombstone history, so without this stale tombstones
            # would wrongly hide live items). A missing ts always evicts.
            del_ts = d.get("ts")
            existing = self._items.get(sid)
            if existing is not None and del_ts is not None \
                    and (existing.get("changed_ts") or 0) > del_ts:
                continue
            self._items.pop(sid, None)
            self._tags.pop(sid, None)

    def _refresh(self, *, force: bool = False) -> dict[str, Any]:
        """Bring the in-memory cache in sync with the server.

        Returns the delta that was applied (items/tags/deletions). On cold
        start does a full ``client.pull()`` then a no-op ``client.sync()`` to
        obtain a valid ``last_sync_ts`` (``pull`` does not return one).
        """
        if self._items is None or self._tags is None:
            self._load_cache()

        now = time.monotonic()
        if not force and self._last_refresh and (now - self._last_refresh) < self.refresh_ttl:
            return {"items": [], "tags": [], "deletions": [], "sync_ts": self.client.last_sync_ts}

        if self._items is None:
            # Cold start: full snapshot, then a sync to fix last_sync_ts.
            dump = self.client.pull()
            self._items = {it["id"]: it for it in dump.get("items", []) if it.get("id")}
            self._tags = {tg["id"]: tg for tg in dump.get("tags", []) if tg.get("id")}
            # A full /pull lists tombstones separately; reconcile them so a
            # deleted item that still shows up among ``items`` does not linger
            # in the fresh cache.
            self._apply(None, None, dump.get("deletions"))
            sync_resp = self.client.sync(persist_ts=False)
            self._apply(
                sync_resp.get("items"),
                sync_resp.get("tags"),
                sync_resp.get("deletions_to_add"),
            )
            self._save_cache(sync_ts=sync_resp.get("sync_ts"))
            self._last_refresh = time.monotonic()
            return {
                "items": list(self._items.values()),
                "tags": list(self._tags.values()),
                "deletions": sync_resp.get("deletions_to_add", []),
                "sync_ts": sync_resp.get("sync_ts"),
            }

        resp = self.client.sync(persist_ts=False)
        delta = {
            "items": resp.get("items", []),
            "tags": resp.get("tags", []),
            "deletions": resp.get("deletions_to_add", []),
            "sync_ts": resp.get("sync_ts"),
        }
        self._apply(delta["items"], delta["tags"], delta["deletions"])
        self._save_cache(sync_ts=resp.get("sync_ts"))
        self._last_refresh = time.monotonic()
        return delta

    def refresh(self, *, force: bool = False) -> dict[str, Any]:
        """Public refresh entry point — see :meth:`_refresh`."""
        return self._refresh(force=force)

    # --------------------------------------------------------------- reading
    def all_items(self) -> list[dict[str, Any]]:
        self._refresh()
        return list((self._items or {}).values())

    def all_tags(self) -> list[dict[str, Any]]:
        self._refresh()
        return list((self._tags or {}).values())

    def get(self, item_id: str) -> dict[str, Any] | None:
        self._refresh()
        return (self._items or {}).get(item_id)

    def resolve_id(self, prefix: str) -> str:
        """Resolve a (possibly-shortened) item id to a full id from the cache.

        Matching is case-insensitive on hex prefix. Minimum length is 4
        characters — shorter prefixes are rejected because a uuid4 has very
        broad collisions in the first 2-3 hex digits. Full ids (32 chars) are
        accepted directly if they exist.
        """
        self._refresh()
        p = (prefix or "").upper()
        if len(p) < 4:
            raise EverdoError(f"id prefix {prefix!r} too short (need at least 4 hex chars)")
        items = self._items or {}
        if p in items:
            return p
        matches = [iid for iid in items if iid.startswith(p)]
        if not matches:
            raise EverdoError(f"no item matches id prefix {prefix!r}")
        if len(matches) > 1:
            head = ", ".join(matches[:5])
            more = f" (and {len(matches) - 5} more)" if len(matches) > 5 else ""
            raise EverdoError(
                f"ambiguous id prefix {prefix!r}: {len(matches)} items match [{head}{more}]"
            )
        return matches[0]

    def find(
        self,
        text: str | None = None,
        *,
        list: str | None = None,
        type: str | None = None,
        tag: str | None = None,
        status: str = "all",
    ) -> list[dict[str, Any]]:
        """Filter items by title substring (case-insensitive), list, type and tag.

        ``tag`` matches against ``effective_tags`` (which includes tags
        inherited from a parent), case-insensitively on the tag title.

        ``status`` selects a completion state: ``"active"`` (open and not in
        archive/trash), ``"completed"`` (has ``completed_on``), or ``"all"``.
        """
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}, got {status!r}")
        self._refresh()
        tag_low = tag.lower() if tag else None
        out = []
        for item in (self._items or {}).values():
            if text and text.lower() not in (item.get("title") or "").lower():
                continue
            if list is not None and item.get("list") != list:
                continue
            if type is not None and item.get("type") != type:
                continue
            if tag_low is not None:
                effective = item.get("effective_tags") or item.get("tags") or []
                titles = {(_tag_title(t) or "").lower() for t in effective}
                if tag_low not in titles:
                    continue
            if status == "active" and not is_active(item):
                continue
            if status == "completed" and not item.get("completed_on"):
                continue
            out.append(item)
        return out

    # --------------------------------------------------------------- helpers
    @staticmethod
    def _clean(item: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in item.items() if k not in DERIVED}

    @staticmethod
    def _stamp(item: dict[str, Any], field: str, ts: int) -> None:
        if field in IRREGULAR_TS:
            item[IRREGULAR_TS[field]] = ts
        elif field in TS_FIELDS:
            item[f"{field}_ts"] = ts

    def _post_mutation(self, resp: dict[str, Any]) -> None:
        self._apply(
            resp.get("items"),
            resp.get("tags"),
            resp.get("deletions_to_add"),
        )
        self._save_cache(sync_ts=resp.get("sync_ts"))
        self._last_refresh = time.monotonic()

    # --------------------------------------------------------------- writing
    def create(
        self,
        title: str,
        *,
        note: str | None = None,
        list: str = "i",
        type: str = "a",
        tags: list[dict] | None = None,
        **fields: Any,
    ) -> str:
        """Create a new item and return its id."""
        _validate_list(type, list)
        ts = _now()
        item_id = new_sync_id()
        item: dict[str, Any] = {
            "id": item_id,
            "sync_id": item_id,
            "title": title,
            "title_ts": ts,
            "note": note,
            "note_ts": ts if note is not None else None,
            "type": type,
            "type_ts": None,
            "list": list,
            "list_ts": None,
            "created_on": ts,
            "changed_ts": ts,
            "is_focused": 0,
            "is_focused_ts": 0,
            "completed_on": None,
            "completed_on_ts": None,
            "repeated_on": None,
            "energy": None,
            "energy_ts": None,
            "time": None,
            "time_ts": None,
            "position_global": None,
            "position_global_ts": None,
            "position_child": None,
            "position_child_ts": None,
            "position_parent": None,
            "position_parent_ts": None,
            "position_focus": None,
            "position_focus_ts": None,
            "num_parallel_actions": None,
            "num_parallel_actions_ts": None,
            "recurrent_task_id": "",
            "schedule": None,
            "schedule_ts": None,
            "due_date": None,
            "due_date_ts": None,
            "start_date": None,
            "start_date_ts": None,
            "contact_id": "",
            "contact_id_ts": None,
            "parent_id": "",
            "parent_id_ts": None,
            "hide_note": None,
            "notification_time": None,
            "notification_time_ts": None,
            "tags": tags or [],
            "tags_changed_ts": ts if tags else None,
        }
        for key, value in fields.items():
            item[key] = value
            self._stamp(item, key, ts)
        resp = self.client.sync({"items": [item]}, persist_ts=False)
        # The server may not echo our own write back; merge it locally so
        # subsequent reads see it immediately.
        self._apply([item], None, None)
        self._post_mutation(resp)
        return item_id

    def update(self, item_id: str, **fields: Any) -> dict[str, Any]:
        """Change one or more fields of an existing item (sends the whole item)."""
        return self.update_many({item_id: fields})[0]

    def update_many(
        self, updates: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Apply field changes to several items in one ``/sync`` round-trip.

        ``updates`` maps item id -> ``{field: value}``. Every target is
        resolved against the cache first, so an unknown id aborts the whole
        batch *before* any write. Whole items are sent (bumped ``changed_ts``
        plus the paired ``*_ts``), so the server's last-write-wins merge
        resolves field-by-field exactly as :meth:`update` does. Cost is two
        round-trips total (one forced refresh + one sync) regardless of batch
        size -- versus two *per item* when looping :meth:`update`.
        """
        if not updates:
            return []
        self._refresh(force=True)
        return self._commit_items(self._build_updates(updates))

    def _build_updates(
        self, updates: dict[str, dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Materialise whole-item payloads from ``{id: {field: value}}``."""
        items_by_id = self._items or {}
        ts = _now()
        built = []
        for item_id, fields in updates.items():
            current = items_by_id.get(item_id)
            if current is None:
                raise EverdoError(f"item not found: {item_id}")
            item = self._clean(current)
            for key, value in fields.items():
                item[key] = value
                self._stamp(item, key, ts)
            item["changed_ts"] = ts
            # Validate the resulting type/list pair only when the change
            # actually touches one of them. This guards `set --list`/`--type`/
            # `--parent` (which may move the item) against producing an illegal
            # state, without retroactively blocking unrelated edits (e.g. a tag
            # change) on an item that is already in a bad list.
            if "list" in fields or "type" in fields:
                _validate_list(item.get("type"), item.get("list"))
            built.append(item)
        return built

    def _commit_items(
        self, items: list[dict[str, Any]]
    ) -> list[dict[str, Any]]:
        """Send already-built whole items in one ``/sync`` and reconcile.

        Mirrors the tail of :meth:`create`: the server may not echo our own
        write back, so merge locally before applying the response delta.
        """
        if not items:
            return []
        resp = self.client.sync({"items": items}, persist_ts=False)
        self._apply(items, None, None)
        self._post_mutation(resp)
        return items

    # ---- convenience wrappers -------------------------------------------
    def complete(self, item_id: str) -> dict[str, Any]:
        return self.update(item_id, completed_on=_now())

    def uncomplete(self, item_id: str) -> dict[str, Any]:
        return self.update(item_id, completed_on=None)

    def rename(self, item_id: str, title: str) -> dict[str, Any]:
        return self.update(item_id, title=title)

    def set_note(self, item_id: str, note: str | None) -> dict[str, Any]:
        return self.update(item_id, note=note)

    def move(self, item_id: str, list: str) -> dict[str, Any]:
        return self.update(item_id, list=list)

    def focus(self, item_id: str, on: bool = True) -> dict[str, Any]:
        return self.update(item_id, is_focused=1 if on else 0)

    def set_due(self, item_id: str, due_date: int | None) -> dict[str, Any]:
        return self.update(item_id, due_date=due_date)

    def set_start(self, item_id: str, start_date: int | None) -> dict[str, Any]:
        return self.update(item_id, start_date=start_date)

    def set_tags(self, item_id: str, tags: list[dict]) -> dict[str, Any]:
        return self.update(item_id, tags=tags)

    # ---- tag helpers (name-based, resolved against the catalog) ----------
    def resolve_tag(self, name: str) -> dict[str, Any]:
        """Look a tag up by title (case-insensitive) in the synced catalog.

        Tags are entities owned by the server; this CLI does not create them.
        An unknown name is an error rather than a silent no-op so a typo never
        ends up as a brand-new tag.
        """
        self._refresh()
        return self._resolve_tag_cached(name)

    def _resolve_tag_cached(self, name: str) -> dict[str, Any]:
        """Tag lookup against the in-memory catalogue without a refresh.

        Lets batch helpers resolve many names after a single forced refresh
        instead of re-syncing per name (which a ``refresh_ttl`` of 0 would
        otherwise force).
        """
        low = (name or "").lower()
        for tg in (self._tags or {}).values():
            if (tg.get("title") or "").lower() == low:
                return tg
        raise EverdoError(f"unknown tag {name!r}; create it in Everdo first")

    def ensure_tag(
        self, title: str, *, type: str = "a", color: int = 0xCCCCCC
    ) -> dict[str, Any]:
        """Return the tag named ``title``, creating it on the server if absent.

        Unlike :meth:`resolve_tag` (which refuses unknown names), this is an
        explicit opt-in to tag creation. Callers that want strict lookup keep
        using ``resolve_tag``/``add_tags`` so a typo never mints a junk tag.
        """
        try:
            return self.resolve_tag(title)
        except EverdoError:
            pass
        ts = _now()
        tag = {
            "id": new_sync_id(),
            "changed_ts": ts,
            "changed_properties": ["title", "type", "color"],
            "title": title, "title_ts": ts,
            "type": type, "type_ts": ts,
            "color": color, "color_ts": ts,
        }
        resp = self.client.sync({"tags": [tag]}, persist_ts=False)
        # Mirror create(): the server may not echo our own write back, so merge
        # it locally before reconciling with the response.
        self._apply(None, [tag], None)
        self._post_mutation(resp)
        return self.resolve_tag(title)

    def add_tags(self, item_id: str, names: list[str]) -> dict[str, Any]:
        """Add tags to an item's own tag list (idempotent, never clobbers)."""
        current = list((self.get(item_id) or {}).get("tags") or [])
        have = {t.get("id") for t in current if isinstance(t, dict)}
        for name in names:
            tg = self.resolve_tag(name)
            if tg.get("id") not in have:
                current.append(tg)
                have.add(tg.get("id"))
        return self.set_tags(item_id, current)

    def remove_tags(self, item_id: str, names: list[str]) -> dict[str, Any]:
        """Remove the named tags from an item's own tag list."""
        current = list((self.get(item_id) or {}).get("tags") or [])
        drop = {(n or "").lower() for n in names}
        kept = [t for t in current if (_tag_title(t) or "").lower() not in drop]
        return self.set_tags(item_id, kept)

    def set_tags_by_name(self, item_id: str, names: list[str]) -> dict[str, Any]:
        """Replace an item's own tag list with exactly the named tags."""
        return self.set_tags(item_id, [self.resolve_tag(n) for n in names])

    # ---- batch tag helpers (one /sync round-trip for the whole set) ------
    def set_tags_many(
        self, tags_by_id: dict[str, list[dict]]
    ) -> list[dict[str, Any]]:
        """Replace each item's own tag list, all in one ``/sync``."""
        return self.update_many(
            {iid: {"tags": tags} for iid, tags in tags_by_id.items()}
        )

    def add_tags_many(
        self, item_ids: list[str], names: list[str]
    ) -> list[dict[str, Any]]:
        """Add the named tags to every listed item in one ``/sync``.

        Idempotent per item (never clobbers existing tags). Names are resolved
        against the catalogue up front, so an unknown tag aborts before any
        write.
        """
        self._refresh(force=True)
        tags = [self._resolve_tag_cached(n) for n in names]
        updates: dict[str, dict[str, Any]] = {}
        for item_id in item_ids:
            item = (self._items or {}).get(item_id)
            if item is None:
                raise EverdoError(f"item not found: {item_id}")
            current = list(item.get("tags") or [])
            have = {t.get("id") for t in current if isinstance(t, dict)}
            changed = False
            for tg in tags:
                if tg.get("id") not in have:
                    current.append(tg)
                    have.add(tg.get("id"))
                    changed = True
            if changed:
                updates[item_id] = {"tags": current}
        return self._commit_items(self._build_updates(updates))

    def remove_tags_many(
        self, item_ids: list[str], names: list[str]
    ) -> list[dict[str, Any]]:
        """Remove the named tags from every listed item in one ``/sync``."""
        drop = {(n or "").lower() for n in names}
        self._refresh(force=True)
        updates = self._tag_removal_updates(
            item_ids, lambda title: title.lower() in drop
        )
        return self._commit_items(self._build_updates(updates))

    def remove_tags_matching(
        self, pattern: str, *, item_ids: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """Remove every tag whose title matches the glob ``pattern`` in one ``/sync``.

        Scope is ``item_ids`` if given, otherwise *all* cached items -- handy
        for sweeping a machine-written tag family like ``'~suggest/*'`` out of
        the whole database. Only items that actually lose a tag are written.
        """
        self._refresh(force=True)
        updates = self._tag_removal_updates(
            item_ids, lambda title: fnmatch.fnmatch(title, pattern)
        )
        return self._commit_items(self._build_updates(updates))

    def _tag_removal_updates(
        self, item_ids: list[str] | None, predicate: Callable[[str], bool]
    ) -> dict[str, dict[str, Any]]:
        """Build ``{id: {'tags': kept}}`` for items losing >=1 tag to ``predicate``.

        Assumes the caller has already refreshed. An explicit but unknown id
        aborts the batch; ``item_ids=None`` scans every cached item.
        """
        if item_ids is None:
            items = list((self._items or {}).values())
        else:
            items = []
            for iid in item_ids:
                it = (self._items or {}).get(iid)
                if it is None:
                    raise EverdoError(f"item not found: {iid}")
                items.append(it)
        updates: dict[str, dict[str, Any]] = {}
        for item in items:
            current = list(item.get("tags") or [])
            kept = [t for t in current if not predicate(_tag_title(t) or "")]
            if len(kept) != len(current):
                updates[item["id"]] = {"tags": kept}
        return updates

    def delete(self, item_id: str) -> dict[str, Any]:
        """Delete an item via the deletions channel."""
        deletion = {"sync_id": item_id, "entity_type": "i", "ts": _now()}
        resp = self.client.sync({"deletions": [deletion]}, persist_ts=False)
        self._apply(None, None, [deletion])
        self._post_mutation(resp)
        return resp

    # --------------------------------------------------------------- projects
    def find_projects(self, *, status: str = "active") -> list[dict[str, Any]]:
        """All items of type ``p``. Archived/completed projects hidden by default."""
        return self.find(type="p", status=status)

    def children_of(self, project_id: str | None) -> list[dict[str, Any]]:
        """Items whose ``parent_id`` matches. ``None`` means orphans."""
        self._refresh()
        out = []
        for item in (self._items or {}).values():
            parent = item.get("parent_id") or None
            target = project_id or None
            if parent == target:
                out.append(item)
        return out

    def create_project(self, title: str, *, list: str = "a", **fields: Any) -> str:
        """Create a new project (item of type ``p``). Default list is Active."""
        return self.create(title, type="p", list=list, **fields)

    def move_to_project(
        self, item_id: str, project_id: str | None, *, list: str | None = None
    ) -> dict[str, Any]:
        """Attach ``item_id`` to ``project_id``; ``None`` detaches it.

        Mirrors the desktop client's drop-into-project behaviour: if the item
        is currently in Inbox/Deleted/Archived and is being attached to a
        project, it is auto-promoted to Next (``list='a'``). Items in those
        lists do not render in the project view. Pass ``list=`` to override
        the target list explicitly.
        """
        fields: dict[str, Any] = {"parent_id": project_id or ""}
        if list is not None:
            fields["list"] = list
        elif project_id:
            current = self.get(item_id)
            if current is None:
                raise EverdoError(f"item not found: {item_id}")
            if current.get("list") in {"i", "d", "r"}:
                fields["list"] = "a"
        return self.update(item_id, **fields)

    # --------------------------------------------------------------- pulling
    def pull_changes(self) -> dict[str, Any]:
        """Force an incremental refresh; return the delta that was applied."""
        return self._refresh(force=True)

    def status(self) -> dict[str, Any]:
        """Snapshot of connectivity and cache health for diagnostics.

        Reports server vs. local clock (a large ``drift_ms`` hints at clock
        skew), the last confirmed sync timestamp, and how much is cached.
        """
        server_ms = self.client.server_time_ms()
        local_ms = int(time.time() * 1000)
        self._refresh()
        return {
            "server_time_ms": server_ms,
            "local_time_ms": local_ms,
            "drift_ms": server_ms - local_ms,
            "last_sync_ts": self.client.last_sync_ts,
            "items_cached": len(self._items or {}),
            "tags_cached": len(self._tags or {}),
            "state_path": self.client.state_path,
        }

"""Reusable Everdo sync client for programmatic (LLM-driven) task management.

Example
-------
>>> from everdo import EverdoClient, EverdoTasks
>>> client = EverdoClient("127.0.0.1:11111", key="YOURKEY")
>>> tasks = EverdoTasks(client)
>>> tid = tasks.create("Buy milk", list="i")
>>> tasks.complete(tid)
>>> tasks.delete(tid)
"""

from .client import EverdoClient, EverdoError
from .tasks import EverdoTasks, LISTS, TYPES, new_sync_id

__all__ = [
    "EverdoClient",
    "EverdoError",
    "EverdoTasks",
    "LISTS",
    "TYPES",
    "new_sync_id",
]

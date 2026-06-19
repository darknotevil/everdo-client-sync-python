"""Reusable Everdo sync client for programmatic (LLM-driven) task management.

Example
-------
>>> from everdo import EverdoTasks
>>> tasks = EverdoTasks.from_config()        # flag > env > config-file > default
>>> tid = tasks.create("Buy milk", list="i")
>>> tasks.complete(tid)
>>> tasks.delete(tid)

Or build the transport by hand:

>>> from everdo import EverdoClient, EverdoTasks
>>> tasks = EverdoTasks(EverdoClient("127.0.0.1:11111", key="YOURKEY"))
"""

from . import config
from .client import EverdoClient, EverdoError
from .config import MissingConfigError, load_tasks
from .tasks import EverdoTasks, LISTS, TYPES, new_sync_id

__all__ = [
    "EverdoClient",
    "EverdoError",
    "EverdoTasks",
    "MissingConfigError",
    "LISTS",
    "TYPES",
    "config",
    "load_tasks",
    "new_sync_id",
]

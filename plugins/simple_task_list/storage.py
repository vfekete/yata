"""Task data model and JSON persistence."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

import plugin_data
from plugin_api import API_VERSION

STATUS_ACTIVE = "active"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"

PLUGIN_ID = "simple_task_list"
# The floor this plugin currently writes: the oldest version of ITSELF that
# can still read back what save() is about to write. Bump only when a
# genuinely backward-incompatible change is made to the task data shape —
# see plugin_data.py's module docstring for the full floor/block contract.
MODEL_VERSION = "1.0"


@dataclass
class Task:
    text: str = ""
    status: str = STATUS_ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    completed_at: str = ""  # ISO timestamp of last transition to done/cancelled; "" if never finished
    note: str = ""  # optional markdown note explaining a done/cancelled state; "" if never added (r-6.md)


def data_dir() -> str:
    # Private to this plugin, for its own legacy-default-window fallback
    # below only — deliberately NOT imported from window_registry.py (the
    # host's own copy, used for host-owned paths like windows.json): a
    # plugin reaching into host internals it doesn't need would be
    # backwards, and this is a stable, four-line helper not worth the
    # cross-package coupling to share (same reasoning the codebase already
    # applies to `_read_bool`, duplicated between settings.py/model.py).
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "yata")
    os.makedirs(path, exist_ok=True)
    return path


class TaskStore:
    """Loads and saves the task list as a JSON file, through
    plugin_data.py's versioned block envelope (r-9.md)."""

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(data_dir(), "tasks.json")

    def load(self) -> list[Task]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            # Pre-r-9.md format: a bare JSON array, written before this
            # file gained a versioned envelope. Still read forever — the
            # very next save() upgrades it to the enveloped format,
            # whether or not any task inside was actually touched.
            return [Task(**item) for item in raw]
        data = plugin_data.read_compatible(self.path, MODEL_VERSION, API_VERSION)
        if data is None:
            return []
        return [Task(**item) for item in data]

    def save(self, tasks: list[Task]) -> None:
        plugin_data.write_block(
            self.path, PLUGIN_ID, MODEL_VERSION, API_VERSION,
            [asdict(t) for t in tasks],
        )

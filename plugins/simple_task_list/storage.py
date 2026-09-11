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
MODEL_VERSION = "1.0"


@dataclass
class Task:
    text: str = ""
    status: str = STATUS_ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    completed_at: str = ""
    note: str = ""


def data_dir() -> str:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "yata")
    os.makedirs(path, exist_ok=True)
    return path


class TaskStore:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(data_dir(), "tasks.json")

    def load(self) -> list[Task]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
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

"""Task data model and JSON persistence."""
from __future__ import annotations

import json
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime

STATUS_ACTIVE = "active"
STATUS_DONE = "done"
STATUS_CANCELLED = "cancelled"


@dataclass
class Task:
    text: str = ""
    status: str = STATUS_ACTIVE
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    id: str = field(default_factory=lambda: uuid.uuid4().hex)


def data_dir() -> str:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "yata")
    os.makedirs(path, exist_ok=True)
    return path


class TaskStore:
    """Loads and saves the task list as a JSON file."""

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(data_dir(), "tasks.json")

    def load(self) -> list[Task]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            raw = json.load(f)
        return [Task(**item) for item in raw]

    def save(self, tasks: list[Task]) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump([asdict(t) for t in tasks], f, indent=2)

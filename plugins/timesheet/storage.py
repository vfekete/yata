from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

import plugin_data
from plugin_api import API_VERSION

PLUGIN_ID = "timesheet"
MODEL_VERSION = "1.0"


@dataclass
class WorkSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    start: str = field(default_factory=lambda: datetime.now().isoformat())
    stop: str = ""
    abandoned: bool = False


@dataclass
class WorkItem:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    non_working: bool = False
    deleted: bool = False
    sessions: list = field(default_factory=list)


def data_dir() -> str:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "yata")
    os.makedirs(path, exist_ok=True)
    return path


def day_end_iso(start_iso: str) -> str:
    start = datetime.fromisoformat(start_iso)
    next_midnight = datetime(start.year, start.month, start.day) + timedelta(days=1)
    return next_midnight.isoformat()


def _session_from_dict(d: dict) -> WorkSession:
    return WorkSession(
        id=d.get("id", uuid.uuid4().hex),
        start=d["start"],
        stop=d.get("stop", ""),
        abandoned=d.get("abandoned", False),
    )


def _item_from_dict(d: dict) -> WorkItem:
    return WorkItem(
        id=d.get("id", uuid.uuid4().hex),
        name=d.get("name", ""),
        non_working=d.get("non_working", False),
        deleted=d.get("deleted", False),
        sessions=[_session_from_dict(s) for s in d.get("sessions", [])],
    )


class TimesheetStore:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(data_dir(), "timesheet.json")

    def load(self) -> tuple[list[WorkItem], dict[str, str]]:
        data = plugin_data.read_compatible(self.path, MODEL_VERSION, API_VERSION)
        if data is None:
            return [], {}
        items = [_item_from_dict(d) for d in data.get("items", [])]
        day_locations = dict(data.get("day_locations", {}))
        if self._sweep_abandoned(items):
            self.save(items, day_locations)
        return items, day_locations

    @staticmethod
    def _sweep_abandoned(items: list[WorkItem]) -> bool:
        changed = False
        for item in items:
            for session in item.sessions:
                if session.stop == "":
                    session.stop = day_end_iso(session.start)
                    session.abandoned = True
                    changed = True
        return changed

    def save(self, items: list[WorkItem], day_locations: dict[str, str]) -> None:
        plugin_data.write_block(self.path, PLUGIN_ID, MODEL_VERSION, API_VERSION, {
            "items": [asdict(i) for i in items],
            "day_locations": dict(day_locations),
        })

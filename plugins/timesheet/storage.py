"""Work item/session data model and JSON persistence (r-10.md).

A WorkItem is a named thing you track time against (e.g. "Feature X"). Each
WorkItem carries its own list of WorkSessions — one per start/stop (or
start/still-running) occurrence, so restarting a stopped item never loses
its earlier history. Only one session across every WorkItem in a given
window may be running (stop == "") at a time — enforced by the model layer
(model.py), not here; this module stays a plain data/persistence layer,
same division of responsibility TaskStore/Task already have.

Brand new file format — no legacy migration concerns (unlike TaskStore's
own pre-envelope plain-JSON-array fallback).
"""
from __future__ import annotations

import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta

import plugin_data
from plugin_api import API_VERSION

PLUGIN_ID = "timesheet"
# The floor this plugin currently writes — see plugin_data.py's own
# docstring for the full floor/block contract.
MODEL_VERSION = "1.0"


@dataclass
class WorkSession:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    start: str = field(default_factory=lambda: datetime.now().isoformat())
    stop: str = ""  # "" while running
    # Set only by TimesheetStore.load()'s abandoned-session sweep below;
    # cleared the moment a user manually adjusts this session's start/stop
    # (see model.py's updateSession).
    abandoned: bool = False


@dataclass
class WorkItem:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = ""
    # Visible in the list, excluded from totals — spec: "Work item can be
    # marked as non-working task... does not contribute to the overall
    # time tracked."
    non_working: bool = False
    # Soft-delete: drops out of the active list (and can no longer be
    # started), but its past sessions are kept and still counted in
    # summaries/PDF exports — deleting a work item mid-month must not
    # silently erase hours already logged against it. No separate
    # restore/purge UI exists for this (not asked for in r-10.md) — this
    # is a one-way hide, unlike YATAS's own window delete/recreate/purge.
    deleted: bool = False
    sessions: list = field(default_factory=list)  # list[WorkSession]


def data_dir() -> str:
    # Private to this plugin, for its own default-path fallback only —
    # deliberately not shared with window_registry.py's own copy, same
    # reasoning plugins/simple_task_list/storage.py already gives for its
    # own duplicate of this helper.
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "yata")
    os.makedirs(path, exist_ok=True)
    return path


def day_end_iso(start_iso: str) -> str:
    """Midnight at the end of the calendar day `start_iso` falls on — used
    to bound an abandoned (never-stopped) session's stop time (explicit
    spec decision: bounded to at most one day, regardless of how long YATA
    was actually closed for)."""
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
    """Loads/saves work items + the day-location map as one JSON file via
    plugin_data.py's versioned envelope — same shape TaskStore already
    uses for tasks.json."""

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
        """Any session left running (stop == "") when this file is loaded
        means YATA closed (crashed, or was just quit) without it being
        stopped — mark it abandoned and bound its duration to the day it
        started on. Returns True if anything changed (so load() only
        re-saves when this sweep actually did something)."""
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

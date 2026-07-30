"""Persisted registry of YATA window instances (id + display tag).

Backward compatibility: the very first window a user ever had (before this
feature existed) keeps using the exact same storage it always did —
TaskStore's own default path and QSettings("yata", "yata") — rather than a
new instances/<uuid> path, so upgrading users see no change and lose
nothing. It's registered under the reserved id DEFAULT_WINDOW_ID; every
other window gets a fresh uuid4 id and a real per-instance path (see
tasks_path_for/settings_path_for below).
"""
from __future__ import annotations

import json
import os
import uuid

from storage import data_dir

DEFAULT_WINDOW_ID = "default"
DEFAULT_TAG = "YATA"


def config_dir() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = os.path.join(base, "yata")
    os.makedirs(path, exist_ok=True)
    return path


def tasks_path_for(window_id: str) -> str | None:
    """None means "use TaskStore's own default path" (the legacy location)."""
    if window_id == DEFAULT_WINDOW_ID:
        return None
    d = os.path.join(data_dir(), "instances", window_id)
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "tasks.json")


def settings_path_for(window_id: str) -> str | None:
    """None means "use AppSettings' own default (QSettings("yata","yata"))"."""
    if window_id == DEFAULT_WINDOW_ID:
        return None
    d = os.path.join(config_dir(), "instances")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{window_id}.conf")


class WindowRegistry:
    """Loads/saves the list of known windows (id + tag) as JSON."""

    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(data_dir(), "windows.json")
        first_run = not os.path.exists(self.path)
        self._entries: list[dict] = self._load()
        if first_run:
            # Seed with the legacy/default window only on a true first run —
            # never re-add it just because it's later missing, or an
            # explicit delete of it would silently undo itself on restart.
            self._entries = [{"id": DEFAULT_WINDOW_ID, "tag": DEFAULT_TAG, "open": True}]
            self._save()

    def _load(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        # "open" is newer than this file format — entries written before it
        # existed default to open, so upgrading users see every window they
        # already had, exactly as before this field existed.
        for e in entries:
            e.setdefault("open", True)
        return entries

    def _save(self) -> None:
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self._entries, f, indent=2)

    def list(self) -> list[dict]:
        return [dict(e) for e in self._entries]

    def get_tag(self, window_id: str) -> str:
        for e in self._entries:
            if e["id"] == window_id:
                return e["tag"]
        return ""

    def add(self, tag: str = DEFAULT_TAG) -> str:
        window_id = uuid.uuid4().hex
        self._entries.append({"id": window_id, "tag": tag, "open": True})
        self._save()
        return window_id

    def next_available_tag(self, base_tag: str) -> str:
        """base_tag unchanged if no window already has it, otherwise
        "<base_tag> - <n>" where n is one more than the highest number
        already in use for this base (the bare tag itself counts as 1) —
        used by WindowManager.createWindow() so ADDing a new window while
        one is already named "YATA" doesn't produce two identically-tagged
        windows. Only applies there — add()/rename() themselves still allow
        duplicate tags freely, since a manual rename is the user's own
        explicit choice.
        """
        highest = 0
        prefix = base_tag + " - "
        for e in self._entries:
            t = e["tag"]
            if t == base_tag:
                highest = max(highest, 1)
            elif t.startswith(prefix) and t[len(prefix):].isdigit():
                highest = max(highest, int(t[len(prefix):]))
        return base_tag if highest == 0 else f"{base_tag} - {highest + 1}"

    def rename(self, window_id: str, new_tag: str) -> None:
        for e in self._entries:
            if e["id"] == window_id:
                e["tag"] = new_tag
                self._save()
                return

    def set_open(self, window_id: str, open_: bool) -> None:
        """Persists whether this window should be (re)opened at next launch —
        the SHOW toggle in YatasView. Separate from WindowManager.is_open(),
        which reflects whether it's actually running right now."""
        for e in self._entries:
            if e["id"] == window_id:
                e["open"] = open_
                self._save()
                return

    def remove(self, window_id: str) -> None:
        self._entries = [e for e in self._entries if e["id"] != window_id]
        self._save()

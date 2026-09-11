from __future__ import annotations

import json
import os
import uuid

DEFAULT_WINDOW_ID = "default"
DEFAULT_TAG = "YATA"
DEFAULT_PLUGIN_ID = "simple_task_list"


def data_dir() -> str:
    base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "yata")
    os.makedirs(path, exist_ok=True)
    return path


def config_dir() -> str:
    base = os.environ.get("XDG_CONFIG_HOME") or os.path.expanduser("~/.config")
    path = os.path.join(base, "yata")
    os.makedirs(path, exist_ok=True)
    return path


def instance_dir_for(window_id: str) -> str | None:
    if window_id == DEFAULT_WINDOW_ID:
        return None
    d = os.path.join(data_dir(), "instances", window_id)
    os.makedirs(d, exist_ok=True)
    return d


def tasks_path_for(window_id: str) -> str | None:
    d = instance_dir_for(window_id)
    return None if d is None else os.path.join(d, "tasks.json")


def settings_path_for(window_id: str) -> str | None:
    if window_id == DEFAULT_WINDOW_ID:
        return None
    d = os.path.join(config_dir(), "instances")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{window_id}.conf")


class WindowRegistry:
    def __init__(self, path: str | None = None):
        self.path = path or os.path.join(data_dir(), "windows.json")
        first_run = not os.path.exists(self.path)
        self._entries: list[dict] = self._load()
        if first_run:
            self._entries = [{
                "id": DEFAULT_WINDOW_ID, "tag": DEFAULT_TAG,
                "open": True, "deleted": False, "plugin": DEFAULT_PLUGIN_ID,
            }]
            self._save()

    def _load(self) -> list[dict]:
        if not os.path.exists(self.path):
            return []
        with open(self.path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        for e in entries:
            e.setdefault("open", True)
            e.setdefault("deleted", False)
            e.setdefault("plugin", DEFAULT_PLUGIN_ID)
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

    def add(self, tag: str = DEFAULT_TAG, plugin: str = DEFAULT_PLUGIN_ID) -> str:
        window_id = uuid.uuid4().hex
        self._entries.append({
            "id": window_id, "tag": tag,
            "open": True, "deleted": False, "plugin": plugin,
        })
        self._save()
        return window_id

    def get_plugin(self, window_id: str) -> str:
        for e in self._entries:
            if e["id"] == window_id:
                return e["plugin"]
        return DEFAULT_PLUGIN_ID

    def next_available_tag(self, base_tag: str) -> str:
        highest = 0
        prefix = base_tag + " - "
        for e in self._entries:
            if e.get("deleted", False):
                continue
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
        for e in self._entries:
            if e["id"] == window_id:
                e["open"] = open_
                self._save()
                return

    def set_deleted(self, window_id: str, deleted: bool) -> None:
        for e in self._entries:
            if e["id"] == window_id:
                e["deleted"] = deleted
                self._save()
                return

    def remove(self, window_id: str) -> None:
        self._entries = [e for e in self._entries if e["id"] != window_id]
        self._save()

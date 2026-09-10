"""r-9.md plugin registration for the simple task list — the original,
and so far only, YATA window content."""
from __future__ import annotations

import os

from plugin_api import API_VERSION, Plugin, PluginContent

from .model import TaskListModel
from .settings import TaskListSettings
from .storage import TaskStore, data_dir

COPYRIGHT = "(C) 2026, Vladimir Fekete, MIT License"

_QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
CONTENT_QML_SOURCE = os.path.join(_QML_DIR, "TaskListContent.qml")
THEME_QML_SOURCE = os.path.join(_QML_DIR, "ThemeImpl.qml")


def _plugin_state_path(tasks_path: str | None) -> str:
    """Sits next to tasks.json (same per-window instance directory), or in
    this plugin's own default data_dir() for the legacy default window
    (tasks_path is None) — same "None means legacy default location"
    convention TaskStore's own `path` parameter already uses."""
    directory = os.path.dirname(tasks_path) if tasks_path else data_dir()
    return os.path.join(directory, "plugin-state.json")


def create_content(window_id: str, tasks_path: str | None, settings) -> PluginContent:
    """tasks_path: today, exactly TaskStore's own `path` parameter (a
    tasks.json path, or None for the legacy default window) — see
    window_registry.tasks_path_for() and main.py's call site. Will
    generalize to a true per-window directory if this plugin ever needs a
    third file. `settings`: the window's legacy per-window QSettings
    (main.py's `_open_settings`) — used only for TaskListSettings' one-time
    migration off its old theme/* keys.
    """
    task_model = TaskListModel(TaskStore(tasks_path))
    task_list_settings = TaskListSettings(_plugin_state_path(tasks_path), settings)
    return PluginContent(
        context_properties={"taskModel": task_model, "appSettings": task_list_settings},
        qml_source=CONTENT_QML_SOURCE,
        theme_qml_source=THEME_QML_SOURCE,
        take_item=task_model.take_task,
        insert_item=task_model.insert_task,
    )


PLUGIN = Plugin(
    id="simple_task_list",
    display_name="Simple Task List",
    min_api_version=API_VERSION,
    create_content=create_content,
    copyright=COPYRIGHT,
    qml_import_dir=_QML_DIR,
)

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


def _plugin_state_path(instance_dir: str | None) -> str:
    directory = instance_dir if instance_dir else data_dir()
    return os.path.join(directory, "plugin-state.json")


def create_content(window_id: str, instance_dir: str | None, settings) -> PluginContent:
    tasks_path = os.path.join(instance_dir, "tasks.json") if instance_dir else None
    if instance_dir:
        os.makedirs(instance_dir, exist_ok=True)
    task_model = TaskListModel(TaskStore(tasks_path))
    task_list_settings = TaskListSettings(_plugin_state_path(instance_dir), settings)
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

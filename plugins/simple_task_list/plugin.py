"""r-9.md plugin registration for the simple task list — the original,
and so far only, YATA window content."""
from __future__ import annotations

from plugin_api import API_VERSION, Plugin, PluginContent

from .model import TaskListModel
from .storage import TaskStore

COPYRIGHT = "(C) 2026, Vladimir Fekete, MIT License"


def create_content(window_id: str, tasks_path: str | None, settings) -> PluginContent:
    """tasks_path: today, exactly TaskStore's own `path` parameter (a
    tasks.json path, or None for the legacy default window) — see
    window_registry.tasks_path_for() and main.py's call site. This will
    generalize to a true per-window directory once this plugin owns more
    than one file (the settings/theme split deferred to r-9.md's plan's
    step 4). `window_id`/`settings` are accepted now for the shape the
    Plugin contract settles on, but unused until that same step.
    """
    task_model = TaskListModel(TaskStore(tasks_path))
    return PluginContent(
        context_properties={"taskModel": task_model},
        take_item=task_model.take_task,
        insert_item=task_model.insert_task,
    )


PLUGIN = Plugin(
    id="simple_task_list",
    display_name="Simple Task List",
    min_api_version=API_VERSION,
    create_content=create_content,
    copyright=COPYRIGHT,
)

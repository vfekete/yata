"""r-10.md plugin registration for the work time tracker."""
from __future__ import annotations

import os

from plugin_api import API_VERSION, Plugin, PluginContent

from .holidays import HolidaysProvider
from .model import TimesheetModel
from .settings import TimesheetSettings
from .storage import TimesheetStore, data_dir

COPYRIGHT = "(C) 2026, Vladimir Fekete, MIT License"

_QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
CONTENT_QML_SOURCE = os.path.join(_QML_DIR, "TimesheetContent.qml")
THEME_QML_SOURCE = os.path.join(_QML_DIR, "ThemeImpl.qml")


def create_content(window_id: str, instance_dir: str | None, settings) -> PluginContent:
    """instance_dir: see plugin_api.py's own PluginContent docstring and
    plugins/simple_task_list/plugin.py's matching function — a directory
    this window's plugin instance owns entirely, or None for the legacy
    default window. `settings` (the window's legacy per-window QSettings)
    is unused here — this plugin has no pre-existing settings to migrate
    off of, unlike TaskListSettings.
    """
    base_dir = instance_dir if instance_dir else data_dir()
    if instance_dir:
        os.makedirs(instance_dir, exist_ok=True)
    store = TimesheetStore(os.path.join(base_dir, "timesheet.json"))
    model = TimesheetModel(store)
    timesheet_settings = TimesheetSettings(os.path.join(base_dir, "plugin-state.json"))
    holidays_provider = HolidaysProvider(os.path.join(base_dir, "holidays-cache"))
    return PluginContent(
        # "taskModel" is deliberately NOT used here — main.py's own
        # docstring (register_window's task_model= kwarg) documents that
        # name as simple_task_list-specific test/tooling convenience, not
        # a cross-plugin contract; nothing generic depends on it existing.
        context_properties={
            "timesheetModel": model,
            "appSettings": timesheet_settings,
            "holidaysProvider": holidays_provider,
        },
        qml_source=CONTENT_QML_SOURCE,
        theme_qml_source=THEME_QML_SOURCE,
    )


PLUGIN = Plugin(
    id="timesheet",
    display_name="Timesheet",
    min_api_version=API_VERSION,
    create_content=create_content,
    copyright=COPYRIGHT,
    qml_import_dir=_QML_DIR,
)

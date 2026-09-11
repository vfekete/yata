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
    base_dir = instance_dir if instance_dir else data_dir()
    if instance_dir:
        os.makedirs(instance_dir, exist_ok=True)
    store = TimesheetStore(os.path.join(base_dir, "timesheet.json"))
    model = TimesheetModel(store)
    timesheet_settings = TimesheetSettings(os.path.join(base_dir, "plugin-state.json"))
    holidays_provider = HolidaysProvider(os.path.join(base_dir, "holidays-cache"))
    return PluginContent(
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

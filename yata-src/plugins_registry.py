from __future__ import annotations

from plugin_api import API_VERSION, Plugin
from plugins.simple_task_list.plugin import PLUGIN as SIMPLE_TASK_LIST
from plugins.timesheet.plugin import PLUGIN as TIMESHEET

ALL_PLUGINS: list[Plugin] = [SIMPLE_TASK_LIST, TIMESHEET]


def _version_tuple(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def build_registry(plugins: list[Plugin], api_version: str = API_VERSION) -> dict[str, Plugin]:
    my_api = _version_tuple(api_version)
    return {
        p.id: p for p in plugins
        if _version_tuple(p.min_api_version) <= my_api
    }


AVAILABLE_PLUGINS: dict[str, Plugin] = build_registry(ALL_PLUGINS)


def get(plugin_id: str) -> Plugin:
    return AVAILABLE_PLUGINS[plugin_id]

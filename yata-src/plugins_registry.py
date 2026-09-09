"""Static plugin registry (r-9.md).

Plugins are compiled in, not dynamically loaded (see plugin_api.py's
module docstring) — this module is just the fixed list of what's
statically linked into this build, plus the load-time compatibility gate
against plugin_api.API_VERSION.
"""
from __future__ import annotations

from plugin_api import API_VERSION, Plugin
from plugins.simple_task_list.plugin import PLUGIN as SIMPLE_TASK_LIST

# Every statically-registered plugin this build was compiled with,
# regardless of whether it's actually usable — see build_registry() for
# the compatibility filter applied to this list.
ALL_PLUGINS: list[Plugin] = [SIMPLE_TASK_LIST]


def _version_tuple(v: str) -> tuple:
    return tuple(int(x) for x in v.split("."))


def build_registry(plugins: list[Plugin], api_version: str = API_VERSION) -> dict[str, Plugin]:
    """id -> Plugin for every given plugin whose min_api_version this
    host's own api_version satisfies. A plugin needing a newer API than
    this host provides is silently left out — there's no way today for an
    incompatible statically-linked plugin to exist at all (it would fail
    to build against a mismatched plugin_api.py in the first place), but
    this is the same gate a future dynamically-loaded plugin would need,
    exercised directly via a fake too-new Plugin in tests."""
    my_api = _version_tuple(api_version)
    return {
        p.id: p for p in plugins
        if _version_tuple(p.min_api_version) <= my_api
    }


AVAILABLE_PLUGINS: dict[str, Plugin] = build_registry(ALL_PLUGINS)


def get(plugin_id: str) -> Plugin:
    return AVAILABLE_PLUGINS[plugin_id]

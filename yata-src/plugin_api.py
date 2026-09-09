"""Contract between the host app and a window-content plugin (r-9.md).

Plugins are statically registered, not dynamically loaded — see
plugins_registry.py. This module only defines the shape both sides agree
on; nothing here talks to Qt/QML directly.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

# Bumped only when this contract itself changes incompatibly (a field is
# removed/repurposed, a call signature changes) — not on every plugin
# release. Plugins declare the lowest API_VERSION they need
# (Plugin.min_api_version); plugins_registry.py checks that against this
# host's own API_VERSION before registering a plugin at all. See
# plugin_data.py for the finer, per-data-file version check.
API_VERSION = "1.0"


@dataclass
class PluginContent:
    """Everything main.py needs to build one window's content area.

    qml_source: absolute path to the plugin's root content QML file, loaded
    into Main.qml's content Loader. Optional/unused for now — r-9.md's
    delivery plan doesn't move any QML into a plugin-owned Loader until its
    step 4; until then, Main.qml itself is still the only QML loaded, so
    this is None until a plugin actually has a content file of its own.
    context_properties: name -> QObject, set on the window's QQmlContext
    alongside the host's own (e.g. "borderColor").
    take_item/insert_item: optional cross-window drag&drop hooks (see
    WindowManager.moveTaskToWindow) — a plugin that doesn't support moving
    its items between windows simply leaves these None.
    on_lock_state_changed/on_window_closing: optional, informational-only
    lifecycle notifications from the host. Never called to ask permission —
    the plugin cannot veto either transition.
    """
    context_properties: dict
    qml_source: str | None = None
    take_item: Callable[[str], object] | None = None
    insert_item: Callable[[object, int], None] | None = None
    on_lock_state_changed: Callable[[str], None] | None = None
    on_window_closing: Callable[[], None] | None = None


@dataclass
class Plugin:
    """A statically-registered window-content plugin's module-level PLUGIN
    object (see plugins/simple_task_list/plugin.py)."""
    id: str
    display_name: str
    min_api_version: str
    create_content: Callable[[str, str, object], PluginContent]
    copyright: str

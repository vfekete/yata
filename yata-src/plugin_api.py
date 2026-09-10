"""Contract between the host app and a window-content plugin (r-9.md).

Plugins are statically registered, not dynamically loaded — see
plugins_registry.py. This module only defines the shape both sides agree
on; nothing here talks to Qt/QML directly.

Not every part of the contract is a field on the dataclasses below — some
of it is a QML-level context property every window already shares between
host and plugin. The generic zoom API is one of these: the host owns
Ctrl+scroll/Ctrl+=/Ctrl+-/Ctrl+0 input handling and a per-window
`hostSettings.zoomLevel` float (see yata-src/settings.py's own docstring),
reachable from any plugin's own QML the same way `hostSettings.borderColor`
already is. A plugin decides entirely on its own whether and how to apply
it — simple_task_list multiplies its own base font size by it
(ThemeImpl.qml); a future plugin could ignore it, or use it for something
else entirely. This is deliberately generic rather than task-list-specific,
since more host-level, cross-plugin controls (zoom included) are expected
to keep landing here as this plugin architecture grows.
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
    into Main.qml's content Loader.
    theme_qml_source: absolute path to the plugin's Theme QML file (a
    QtObject exposing whatever color/font properties the plugin's own
    content QML wants under the bare "Theme" identifier). Constructed by
    the host (main.py) and set as the "Theme" context property *before*
    qml_source is loaded, same as before r-9.md — cross-file QML id lookup
    doesn't reach across separate documents, so this has to stay a context
    property rather than something qml_source's own file declares locally.
    Both of these are None only for a plugin with no visual content at all
    (nothing in this codebase yet needs that).
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
    theme_qml_source: str | None = None
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
    # Added once to the QQmlEngine's import path (see main.py) so this
    # plugin's own QML files can reference each other by bare type name
    # (e.g. "Toolbar { ... }") the same way yata-src/qml's own files do —
    # None for a plugin with no QML of its own.
    qml_import_dir: str | None = None

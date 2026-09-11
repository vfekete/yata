from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

API_VERSION = "1.0"


@dataclass
class PluginContent:
    context_properties: dict
    qml_source: str | None = None
    theme_qml_source: str | None = None
    take_item: Callable[[str], object] | None = None
    insert_item: Callable[[object, int], None] | None = None
    on_lock_state_changed: Callable[[str], None] | None = None
    on_window_closing: Callable[[], None] | None = None


@dataclass
class Plugin:
    id: str
    display_name: str
    min_api_version: str
    create_content: Callable[[str, str, object], PluginContent]
    copyright: str
    qml_import_dir: str | None = None

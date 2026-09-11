from __future__ import annotations

from PySide6.QtCore import QSettings

import plugin_data
from plugin_api import API_VERSION
from plugin_settings import DEFAULT_OPACITY_PERCENT, ThemedSettings

from .storage import PLUGIN_ID

MODEL_VERSION = "1.0"


class TaskListSettings(ThemedSettings):
    def __init__(self, path: str, legacy_settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self._path = path
        data = plugin_data.read_compatible(path, MODEL_VERSION, API_VERSION)
        already_on_disk = data is not None
        if data is None:
            data = self._migrate_from_legacy(legacy_settings) if legacy_settings else {}
        self._load_themed(data)

        if not already_on_disk:
            self._save()

    @staticmethod
    def _migrate_from_legacy(legacy_settings: QSettings) -> dict:
        return {
            "themeMode": legacy_settings.value("theme/mode", "dark"),
            "themeTint": legacy_settings.value("theme/tint", "none"),
            "opacityPercent": legacy_settings.value("theme/opacityPercent", DEFAULT_OPACITY_PERCENT),
        }

    def _save(self) -> None:
        plugin_data.write_block(self._path, PLUGIN_ID, MODEL_VERSION, API_VERSION, self._themed_data())

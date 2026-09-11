"""Plugin-owned theme/opacity settings (r-9.md step 4).

Split out of the host's AppSettings (yata-src/settings.py), which now only
keeps host-owned keys (window geometry, borderColor, lockState, zoomLevel,
wheelZoomInverted). These three properties are genuinely content-facing
(a different plugin could have no concept of "theme"/"tint" at all), so
they stay here — backed by plugin_data.py's versioned envelope in their
own file rather than the shared per-window QSettings .conf, with a
one-time migration off the legacy QSettings keys for existing installs.

The themeMode/themeTint/opacityPercent property trio itself now lives in
yata-src/plugin_settings.py's ThemedSettings base (r-10.md follow-up,
extracted once timesheet's own TimesheetSettings needed the exact same
~90 lines verbatim) — this class only adds the legacy-QSettings
migration on top, which is specific to this plugin's own pre-r-9.md
history.

zoom (fontScale/wheelZoomInverted) moved to yata-src/settings.py's
AppSettings in a later follow-up: zoom is generic per-window host state,
not plugin-owned — see that module's own docstring. This class no longer
reads or writes those two keys at all; an existing plugin-state.json with
old fontScale/wheelZoomInverted entries simply leaves them as harmless,
unread orphaned data (same "skip, don't delete" philosophy plugin_data.py
already applies to incompatible blocks).
"""
from __future__ import annotations

from PySide6.QtCore import QSettings

import plugin_data
from plugin_api import API_VERSION
from plugin_settings import DEFAULT_OPACITY_PERCENT, ThemedSettings

from .storage import PLUGIN_ID

MODEL_VERSION = "1.0"


class TaskListSettings(ThemedSettings):
    """Backed by plugin_data.py's versioned envelope; QML binds to these
    properties two-way exactly as it always has via the "appSettings"
    context property (see plugin.py's create_content)."""

    def __init__(self, path: str, legacy_settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self._path = path
        data = plugin_data.read_compatible(path, MODEL_VERSION, API_VERSION)
        already_on_disk = data is not None
        if data is None:
            data = self._migrate_from_legacy(legacy_settings) if legacy_settings else {}
        self._load_themed(data)

        if not already_on_disk:
            # Either truly first-run, or just migrated above — either way,
            # write the file now so a second window/session never re-reads
            # legacy_settings again (and so a fresh window with no legacy
            # settings at all still gets a real file on disk from the start).
            self._save()

    @staticmethod
    def _migrate_from_legacy(legacy_settings: QSettings) -> dict:
        """One-time migration off yata-src/settings.py's old theme/* keys —
        pre-r-9.md, these lived in the same per-window QSettings .conf as
        window geometry/borderColor/lockState. Reads them once; never
        deletes them from legacy_settings (harmless orphaned data, not
        worth the extra risk of touching a file this class no longer
        otherwise writes to)."""
        return {
            "themeMode": legacy_settings.value("theme/mode", "dark"),
            "themeTint": legacy_settings.value("theme/tint", "none"),
            "opacityPercent": legacy_settings.value("theme/opacityPercent", DEFAULT_OPACITY_PERCENT),
        }

    def _save(self) -> None:
        plugin_data.write_block(self._path, PLUGIN_ID, MODEL_VERSION, API_VERSION, self._themed_data())

"""Plugin-owned theme/opacity settings (r-9.md step 4).

Split out of the host's AppSettings (yata-src/settings.py), which now only
keeps host-owned keys (window geometry, borderColor, lockState, zoomLevel,
wheelZoomInverted). These three properties are genuinely content-facing
(a different plugin could have no concept of "theme"/"tint" at all), so
they stay here — backed by plugin_data.py's versioned envelope in their
own file rather than the shared per-window QSettings .conf, with a
one-time migration off the legacy QSettings keys for existing installs.

zoom (fontScale/wheelZoomInverted) moved to yata-src/settings.py's
AppSettings in a later follow-up: zoom is generic per-window host state,
not plugin-owned — see that module's own docstring. This class no longer
reads or writes those two keys at all; an existing plugin-state.json with
old fontScale/wheelZoomInverted entries simply leaves them as harmless,
unread orphaned data (same "skip, don't delete" philosophy plugin_data.py
already applies to incompatible blocks).
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QSettings, Signal

import plugin_data
from plugin_api import API_VERSION

from .storage import PLUGIN_ID

MODEL_VERSION = "1.0"

THEME_MODES = ("light", "dark")
# "none" is the safe default: it keeps the plain look. The rest recreate old
# CRT/terminal displays (green/amber phosphor, paperwhite monitor, teletype
# paper) and are handled entirely in qml/ThemeImpl.qml.
THEME_TINTS = ("none", "green", "goldenrod", "white", "black")

DEFAULT_OPACITY_PERCENT = 65
MIN_OPACITY_PERCENT = 5
MAX_OPACITY_PERCENT = 100


class TaskListSettings(QObject):
    """Backed by plugin_data.py's versioned envelope; QML binds to these
    properties two-way exactly as it always has via the "appSettings"
    context property (see plugin.py's create_content)."""

    themeModeChanged = Signal()
    themeTintChanged = Signal()
    opacityPercentChanged = Signal()

    def __init__(self, path: str, legacy_settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self._path = path
        data = plugin_data.read_compatible(path, MODEL_VERSION, API_VERSION)
        already_on_disk = data is not None
        if data is None:
            data = self._migrate_from_legacy(legacy_settings) if legacy_settings else {}

        mode = data.get("themeMode", "dark")
        self._theme_mode = mode if mode in THEME_MODES else "dark"
        tint = data.get("themeTint", "none")
        self._theme_tint = tint if tint in THEME_TINTS else "none"
        self._opacity_percent = self._clamp_opacity(data.get("opacityPercent", DEFAULT_OPACITY_PERCENT))

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

    @staticmethod
    def _clamp_opacity(value) -> int:
        return max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(round(float(value)))))

    def _save(self) -> None:
        plugin_data.write_block(self._path, PLUGIN_ID, MODEL_VERSION, API_VERSION, {
            "themeMode": self._theme_mode,
            "themeTint": self._theme_tint,
            "opacityPercent": self._opacity_percent,
        })

    def _get_theme_mode(self) -> str:
        return self._theme_mode

    def _set_theme_mode(self, value: str):
        if value not in THEME_MODES or value == self._theme_mode:
            return
        self._theme_mode = value
        self._save()
        self.themeModeChanged.emit()

    themeMode = Property(str, _get_theme_mode, _set_theme_mode, notify=themeModeChanged)

    def _get_theme_tint(self) -> str:
        return self._theme_tint

    def _set_theme_tint(self, value: str):
        if value not in THEME_TINTS or value == self._theme_tint:
            return
        self._theme_tint = value
        self._save()
        self.themeTintChanged.emit()

    themeTint = Property(str, _get_theme_tint, _set_theme_tint, notify=themeTintChanged)

    def _get_opacity_percent(self) -> int:
        return self._opacity_percent

    def _set_opacity_percent(self, value: int):
        value = self._clamp_opacity(value)
        if value == self._opacity_percent:
            return
        self._opacity_percent = value
        self._save()
        self.opacityPercentChanged.emit()

    opacityPercent = Property(
        int, _get_opacity_percent, _set_opacity_percent, notify=opacityPercentChanged
    )

    # Read-only so QML can reset to this without hardcoding the value
    # itself in more than one place (ThemeMenu's own Reset item).
    defaultOpacityPercent = Property(int, lambda self: DEFAULT_OPACITY_PERCENT, constant=True)

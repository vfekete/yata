"""Plugin-owned theme/zoom settings (r-9.md step 4).

Split out of the host's AppSettings (yata-src/settings.py), which now only
keeps host-owned keys (window geometry, borderColor, lockState). These five
properties were always content-facing (the task list's own look and zoom),
so they move here — backed by plugin_data.py's versioned envelope in their
own file rather than the shared per-window QSettings .conf, with a
one-time migration off the legacy QSettings keys for existing installs.
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

DEFAULT_FONT_SCALE = 1.0
MIN_FONT_SCALE = 0.5
# Not literally unbounded — Qt's font.pixelSize is still a real int under
# the hood, and an astronomically large value risks overflow/undefined
# behavior there. 200x (2800px base task text at the default 14px) is
# effectively "as far as you'd ever actually zoom" while staying nowhere
# near that ceiling.
MAX_FONT_SCALE = 200.0


def _read_bool(s: QSettings, key: str, default: bool) -> bool:
    """Read a boolean from QSettings, correctly handling stored 'false'
    strings. Only used for the legacy-QSettings migration below — see
    yata-src/settings.py's own copy of this same helper."""
    v = s.value(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() not in ("false", "0", "no")
    return bool(v)


class TaskListSettings(QObject):
    """Backed by plugin_data.py's versioned envelope; QML binds to these
    properties two-way exactly as it always has via the "appSettings"
    context property (see plugin.py's create_content)."""

    themeModeChanged = Signal()
    themeTintChanged = Signal()
    opacityPercentChanged = Signal()
    fontScaleChanged = Signal()
    wheelZoomInvertedChanged = Signal()

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
        self._font_scale = self._clamp_font_scale(data.get("fontScale", DEFAULT_FONT_SCALE))
        self._wheel_zoom_inverted = bool(data.get("wheelZoomInverted", False))

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
            "fontScale": legacy_settings.value("theme/fontScale", DEFAULT_FONT_SCALE),
            "wheelZoomInverted": _read_bool(legacy_settings, "theme/wheelZoomInverted", False),
        }

    @staticmethod
    def _clamp_opacity(value) -> int:
        return max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(round(float(value)))))

    @staticmethod
    def _clamp_font_scale(value) -> float:
        return max(MIN_FONT_SCALE, min(MAX_FONT_SCALE, float(value)))

    def _save(self) -> None:
        plugin_data.write_block(self._path, PLUGIN_ID, MODEL_VERSION, API_VERSION, {
            "themeMode": self._theme_mode,
            "themeTint": self._theme_tint,
            "opacityPercent": self._opacity_percent,
            "fontScale": self._font_scale,
            "wheelZoomInverted": self._wheel_zoom_inverted,
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

    def _get_font_scale(self) -> float:
        return self._font_scale

    def _set_font_scale(self, value: float):
        value = self._clamp_font_scale(value)
        if value == self._font_scale:
            return
        self._font_scale = value
        self._save()
        self.fontScaleChanged.emit()

    fontScale = Property(float, _get_font_scale, _set_font_scale, notify=fontScaleChanged)

    def _get_wheel_zoom_inverted(self) -> bool:
        return self._wheel_zoom_inverted

    def _set_wheel_zoom_inverted(self, value: bool):
        value = bool(value)
        if value == self._wheel_zoom_inverted:
            return
        self._wheel_zoom_inverted = value
        self._save()
        self.wheelZoomInvertedChanged.emit()

    wheelZoomInverted = Property(
        bool, _get_wheel_zoom_inverted, _set_wheel_zoom_inverted, notify=wheelZoomInvertedChanged
    )

    # Read-only so QML can reset to these without hardcoding the values
    # itself in more than one place (the RESET button and the Ctrl+0
    # shortcut both need them).
    defaultOpacityPercent = Property(int, lambda self: DEFAULT_OPACITY_PERCENT, constant=True)
    defaultFontScale = Property(float, lambda self: DEFAULT_FONT_SCALE, constant=True)
    minFontScale = Property(float, lambda self: MIN_FONT_SCALE, constant=True)
    maxFontScale = Property(float, lambda self: MAX_FONT_SCALE, constant=True)

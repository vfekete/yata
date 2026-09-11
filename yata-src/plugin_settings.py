"""Shared base for plugin-owned, envelope-persisted settings objects
(plugin_data.py) that expose the "themeMode/themeTint/opacityPercent"
property trio — main.py's window_factory clones a NEW window's theme
generically onto whatever "appSettings" object the new window's plugin
returns (plugin_settings.themeMode = ..., etc.), regardless of which
plugin that turns out to be, so every plugin needing this look-
customizable is expected to expose exactly this surface (see
plugin_api.py's own PluginContent docstring).

Extracted after simple_task_list's TaskListSettings and timesheet's
TimesheetSettings ended up with ~90 lines of identical Property/Signal
boilerplate for this trio (r-10.md's "Bug wave 1" follow-up, once a
second plugin needed the exact same thing) — a plugin's own settings
class subclasses ThemedSettings, calls _load_themed(data)/_themed_data()
from its own __init__/_save(), and adds whatever plugin-specific
properties it needs on top.
"""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal

THEME_MODES = ("light", "dark")
THEME_TINTS = ("none", "green", "goldenrod", "white", "black")

DEFAULT_OPACITY_PERCENT = 65
MIN_OPACITY_PERCENT = 5
MAX_OPACITY_PERCENT = 100


class ThemedSettings(QObject):
    """QObject base providing themeMode/themeTint/opacityPercent as Qt
    Properties. A subclass is responsible for its own persistence: call
    _load_themed(data) once, early in __init__, to seed these three from
    whatever dict was just read back from disk (or defaults, on first
    run), and have its own _save() call _themed_data() to fold these
    three back into whatever larger dict it writes out.
    """
    themeModeChanged = Signal()
    themeTintChanged = Signal()
    opacityPercentChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._theme_mode = "dark"
        self._theme_tint = "none"
        self._opacity_percent = DEFAULT_OPACITY_PERCENT

    def _load_themed(self, data: dict) -> None:
        mode = data.get("themeMode", "dark")
        self._theme_mode = mode if mode in THEME_MODES else "dark"
        tint = data.get("themeTint", "none")
        self._theme_tint = tint if tint in THEME_TINTS else "none"
        self._opacity_percent = self._clamp_opacity(data.get("opacityPercent", DEFAULT_OPACITY_PERCENT))

    def _themed_data(self) -> dict:
        return {
            "themeMode": self._theme_mode,
            "themeTint": self._theme_tint,
            "opacityPercent": self._opacity_percent,
        }

    def _save(self) -> None:
        """A subclass MUST override this — this base has no file/path of
        its own to persist to, only the in-memory property trio."""
        raise NotImplementedError

    @staticmethod
    def _clamp_opacity(value) -> int:
        return max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(round(float(value)))))

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
    # itself in more than one place — same convention every plugin's own
    # ThemeMenu-equivalent Reset item already relies on.
    defaultOpacityPercent = Property(int, lambda self: DEFAULT_OPACITY_PERCENT, constant=True)

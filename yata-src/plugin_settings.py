from __future__ import annotations

from PySide6.QtCore import Property, QObject, Signal

THEME_MODES = ("light", "dark")
THEME_TINTS = ("none", "green", "goldenrod", "white", "black")

DEFAULT_OPACITY_PERCENT = 65
MIN_OPACITY_PERCENT = 5
MAX_OPACITY_PERCENT = 100


class ThemedSettings(QObject):
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

    defaultOpacityPercent = Property(int, lambda self: DEFAULT_OPACITY_PERCENT, constant=True)

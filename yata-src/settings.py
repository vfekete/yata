"""Window geometry and theme persistence."""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QSettings, Signal
from PySide6.QtGui import QGuiApplication

ASPECT_WIDTH = 9
ASPECT_HEIGHT = 16
FIRST_RUN_WIDTH_RATIO = 0.20

THEME_MODES = ("light", "dark")
# "none" is the safe default: it keeps the plain look. The rest recreate old
# CRT/terminal displays (green/amber phosphor, paperwhite monitor, teletype
# paper) and are handled entirely in Theme.qml.
THEME_TINTS = ("none", "green", "goldenrod", "white", "black")

DEFAULT_OPACITY_PERCENT = 65
MIN_OPACITY_PERCENT = 5
MAX_OPACITY_PERCENT = 100

DEFAULT_FONT_SCALE = 1.0
MIN_FONT_SCALE = 0.5
MAX_FONT_SCALE = 2.0


def monitor_signature() -> str:
    """A string identifying the current monitor layout (order + resolution)."""
    parts = []
    for screen in QGuiApplication.screens():
        geo = screen.geometry()
        parts.append(f"{geo.x()},{geo.y()},{geo.width()},{geo.height()}")
    return "|".join(parts)


def first_run_geometry() -> tuple[int, int, int, int]:
    """Centered on the primary screen, 20% of its width, 9:16 aspect ratio."""
    geo = QGuiApplication.primaryScreen().geometry()
    width = int(geo.width() * FIRST_RUN_WIDTH_RATIO)
    height = int(width * ASPECT_HEIGHT / ASPECT_WIDTH)
    x = geo.x() + (geo.width() - width) // 2
    y = geo.y() + (geo.height() - height) // 2
    return x, y, width, height


class AppSettings(QObject):
    """Backed by QSettings; QML binds to these properties two-way."""

    xChanged = Signal()
    yChanged = Signal()
    widthChanged = Signal()
    heightChanged = Signal()
    themeModeChanged = Signal()
    themeTintChanged = Signal()
    opacityPercentChanged = Signal()
    fontScaleChanged = Signal()
    wheelZoomInvertedChanged = Signal()

    def __init__(self, settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self._settings = settings or QSettings("yata", "yata")
        self._x, self._y, self._width, self._height = self._load_geometry()
        mode = self._settings.value("theme/mode", "dark")
        self._theme_mode = mode if mode in THEME_MODES else "dark"
        tint = self._settings.value("theme/tint", "none")
        self._theme_tint = tint if tint in THEME_TINTS else "none"
        self._opacity_percent = self._clamp_opacity(
            self._settings.value("theme/opacityPercent", DEFAULT_OPACITY_PERCENT)
        )
        self._font_scale = self._clamp_font_scale(
            self._settings.value("theme/fontScale", DEFAULT_FONT_SCALE)
        )
        self._wheel_zoom_inverted = bool(
            self._settings.value("theme/wheelZoomInverted", False)
        )

    @staticmethod
    def _clamp_opacity(value) -> int:
        return max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(round(float(value)))))

    @staticmethod
    def _clamp_font_scale(value) -> float:
        return max(MIN_FONT_SCALE, min(MAX_FONT_SCALE, float(value)))

    def _load_geometry(self) -> tuple[int, int, int, int]:
        current_signature = monitor_signature()
        stored_signature = self._settings.value("window/monitorSignature", "")
        if stored_signature == current_signature and self._settings.contains("window/width"):
            return (
                int(self._settings.value("window/x")),
                int(self._settings.value("window/y")),
                int(self._settings.value("window/width")),
                int(self._settings.value("window/height")),
            )
        x, y, width, height = first_run_geometry()
        self._settings.setValue("window/monitorSignature", current_signature)
        return x, y, width, height

    def _save_geometry(self):
        self._settings.setValue("window/monitorSignature", monitor_signature())
        self._settings.setValue("window/x", self._x)
        self._settings.setValue("window/y", self._y)
        self._settings.setValue("window/width", self._width)
        self._settings.setValue("window/height", self._height)

    def _get_x(self) -> int:
        return self._x

    def _set_x(self, value: int):
        value = int(value)
        if value == self._x:
            return
        self._x = value
        self._save_geometry()
        self.xChanged.emit()

    x = Property(int, _get_x, _set_x, notify=xChanged)

    def _get_y(self) -> int:
        return self._y

    def _set_y(self, value: int):
        value = int(value)
        if value == self._y:
            return
        self._y = value
        self._save_geometry()
        self.yChanged.emit()

    y = Property(int, _get_y, _set_y, notify=yChanged)

    def _get_width(self) -> int:
        return self._width

    def _set_width(self, value: int):
        value = int(value)
        if value == self._width:
            return
        self._width = value
        self._save_geometry()
        self.widthChanged.emit()

    width = Property(int, _get_width, _set_width, notify=widthChanged)

    def _get_height(self) -> int:
        return self._height

    def _set_height(self, value: int):
        value = int(value)
        if value == self._height:
            return
        self._height = value
        self._save_geometry()
        self.heightChanged.emit()

    height = Property(int, _get_height, _set_height, notify=heightChanged)

    def _get_theme_mode(self) -> str:
        return self._theme_mode

    def _set_theme_mode(self, value: str):
        if value not in THEME_MODES or value == self._theme_mode:
            return
        self._theme_mode = value
        self._settings.setValue("theme/mode", value)
        self.themeModeChanged.emit()

    themeMode = Property(str, _get_theme_mode, _set_theme_mode, notify=themeModeChanged)

    def _get_theme_tint(self) -> str:
        return self._theme_tint

    def _set_theme_tint(self, value: str):
        if value not in THEME_TINTS or value == self._theme_tint:
            return
        self._theme_tint = value
        self._settings.setValue("theme/tint", value)
        self.themeTintChanged.emit()

    themeTint = Property(str, _get_theme_tint, _set_theme_tint, notify=themeTintChanged)

    def _get_opacity_percent(self) -> int:
        return self._opacity_percent

    def _set_opacity_percent(self, value: int):
        value = self._clamp_opacity(value)
        if value == self._opacity_percent:
            return
        self._opacity_percent = value
        self._settings.setValue("theme/opacityPercent", value)
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
        self._settings.setValue("theme/fontScale", value)
        self.fontScaleChanged.emit()

    fontScale = Property(float, _get_font_scale, _set_font_scale, notify=fontScaleChanged)

    def _get_wheel_zoom_inverted(self) -> bool:
        return self._wheel_zoom_inverted

    def _set_wheel_zoom_inverted(self, value: bool):
        value = bool(value)
        if value == self._wheel_zoom_inverted:
            return
        self._wheel_zoom_inverted = value
        self._settings.setValue("theme/wheelZoomInverted", value)
        self.wheelZoomInvertedChanged.emit()

    wheelZoomInverted = Property(
        bool, _get_wheel_zoom_inverted, _set_wheel_zoom_inverted, notify=wheelZoomInvertedChanged
    )

    # Read-only so QML can reset to these without hardcoding the values
    # itself in more than one place (the RESET button and the Ctrl+0
    # shortcut both need them).
    defaultOpacityPercent = Property(int, lambda self: DEFAULT_OPACITY_PERCENT, constant=True)
    defaultFontScale = Property(float, lambda self: DEFAULT_FONT_SCALE, constant=True)

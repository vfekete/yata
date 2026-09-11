from __future__ import annotations

from PySide6.QtCore import Property, QObject, QSettings, Signal
from PySide6.QtGui import QGuiApplication

ASPECT_WIDTH = 9
ASPECT_HEIGHT = 16
FIRST_RUN_WIDTH_RATIO = 0.20

LOCK_STATES = ("unlocked", "auto-locked", "locked")

DEFAULT_ZOOM_LEVEL = 1.0
MIN_ZOOM_LEVEL = 0.5
MAX_ZOOM_LEVEL = 200.0


def _read_bool(s: QSettings, key: str, default: bool) -> bool:
    v = s.value(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() not in ("false", "0", "no")
    return bool(v)


def monitor_signature() -> str:
    parts = []
    for screen in QGuiApplication.screens():
        geo = screen.geometry()
        parts.append(f"{geo.x()},{geo.y()},{geo.width()},{geo.height()}")
    return "|".join(sorted(parts))


def first_run_geometry() -> tuple[int, int, int, int]:
    geo = QGuiApplication.primaryScreen().geometry()
    width = int(geo.width() * FIRST_RUN_WIDTH_RATIO)
    height = int(width * ASPECT_HEIGHT / ASPECT_WIDTH)
    x = geo.x() + (geo.width() - width) // 2
    y = geo.y() + (geo.height() - height) // 2
    return x, y, width, height


def _clamp_geometry_to_virtual_desktop(
    x: int, y: int, width: int, height: int
) -> tuple[int, int, int, int]:
    virtual = QGuiApplication.primaryScreen().virtualGeometry()
    width = max(1, min(width, virtual.width()))
    height = max(1, min(height, virtual.height()))
    x = min(max(x, virtual.x()), virtual.x() + virtual.width() - width)
    y = min(max(y, virtual.y()), virtual.y() + virtual.height() - height)
    return x, y, width, height


class AppSettings(QObject):
    xChanged = Signal()
    yChanged = Signal()
    widthChanged = Signal()
    heightChanged = Signal()
    borderColorChanged = Signal()
    lockStateChanged = Signal()
    zoomLevelChanged = Signal()
    wheelZoomInvertedChanged = Signal()

    def __init__(self, settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self._settings = settings or QSettings("yata", "yata")
        self._x, self._y, self._width, self._height = self._load_geometry()
        self._border_color = str(self._settings.value("theme/borderColor", ""))
        lock_state = self._settings.value("theme/lockState", "unlocked")
        self._lock_state = lock_state if lock_state in LOCK_STATES else "unlocked"
        self._zoom_level = self._clamp_zoom_level(
            self._settings.value("window/zoomLevel", DEFAULT_ZOOM_LEVEL)
        )
        self._wheel_zoom_inverted = _read_bool(self._settings, "window/wheelZoomInverted", False)

    @staticmethod
    def _clamp_zoom_level(value) -> float:
        return max(MIN_ZOOM_LEVEL, min(MAX_ZOOM_LEVEL, float(value)))

    def _load_geometry(self) -> tuple[int, int, int, int]:
        current_signature = monitor_signature()
        stored_signature = self._settings.value("window/monitorSignature", "")
        if not self._settings.contains("window/width"):
            x, y, width, height = first_run_geometry()
            self._settings.setValue("window/monitorSignature", current_signature)
            self._settings.sync()
            return x, y, width, height

        x = int(self._settings.value("window/x"))
        y = int(self._settings.value("window/y"))
        width = int(self._settings.value("window/width"))
        height = int(self._settings.value("window/height"))
        if stored_signature != current_signature:
            x, y, width, height = _clamp_geometry_to_virtual_desktop(x, y, width, height)
            self._settings.setValue("window/monitorSignature", current_signature)
            self._settings.sync()
        return x, y, width, height

    def _save_geometry(self):
        self._settings.setValue("window/monitorSignature", monitor_signature())
        self._settings.setValue("window/x", self._x)
        self._settings.setValue("window/y", self._y)
        self._settings.setValue("window/width", self._width)
        self._settings.setValue("window/height", self._height)
        self._settings.sync()

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

    def _get_border_color(self) -> str:
        return self._border_color

    def _set_border_color(self, value: str):
        value = str(value)
        if value == self._border_color:
            return
        self._border_color = value
        self._settings.setValue("theme/borderColor", value)
        self._settings.sync()
        self.borderColorChanged.emit()

    borderColor = Property(str, _get_border_color, _set_border_color, notify=borderColorChanged)

    def _get_lock_state(self) -> str:
        return self._lock_state

    def _set_lock_state(self, value: str):
        if value not in LOCK_STATES or value == self._lock_state:
            return
        self._lock_state = value
        self._settings.setValue("theme/lockState", value)
        self._settings.sync()
        self.lockStateChanged.emit()

    lockState = Property(str, _get_lock_state, _set_lock_state, notify=lockStateChanged)

    def _get_zoom_level(self) -> float:
        return self._zoom_level

    def _set_zoom_level(self, value: float):
        value = self._clamp_zoom_level(value)
        if value == self._zoom_level:
            return
        self._zoom_level = value
        self._settings.setValue("window/zoomLevel", value)
        self._settings.sync()
        self.zoomLevelChanged.emit()

    zoomLevel = Property(float, _get_zoom_level, _set_zoom_level, notify=zoomLevelChanged)

    def _get_wheel_zoom_inverted(self) -> bool:
        return self._wheel_zoom_inverted

    def _set_wheel_zoom_inverted(self, value: bool):
        value = bool(value)
        if value == self._wheel_zoom_inverted:
            return
        self._wheel_zoom_inverted = value
        self._settings.setValue("window/wheelZoomInverted", value)
        self._settings.sync()
        self.wheelZoomInvertedChanged.emit()

    wheelZoomInverted = Property(
        bool, _get_wheel_zoom_inverted, _set_wheel_zoom_inverted, notify=wheelZoomInvertedChanged
    )

    defaultZoomLevel = Property(float, lambda self: DEFAULT_ZOOM_LEVEL, constant=True)
    minZoomLevel = Property(float, lambda self: MIN_ZOOM_LEVEL, constant=True)
    maxZoomLevel = Property(float, lambda self: MAX_ZOOM_LEVEL, constant=True)

"""Window geometry and theme persistence."""
from __future__ import annotations

from PySide6.QtCore import Property, QObject, QSettings, Signal
from PySide6.QtGui import QGuiApplication

ASPECT_WIDTH = 9
ASPECT_HEIGHT = 16
FIRST_RUN_WIDTH_RATIO = 0.20


def _read_bool(s: QSettings, key: str, default: bool) -> bool:
    """Read a boolean from QSettings, correctly handling stored 'false' strings.

    QSettings' native/INI backend round-trips bools as the literal text
    "true"/"false" — reading one back without a type hint can hand you the
    *string* "false", and `bool("false")` is True (any non-empty string is
    truthy in Python). Same helper as models.py's `_read_bool`, duplicated
    here rather than imported to avoid a settings.py -> models.py
    dependency for one 6-line utility.
    """
    v = s.value(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() not in ("false", "0", "no")
    return bool(v)

THEME_MODES = ("light", "dark")
# "none" is the safe default: it keeps the plain look. The rest recreate old
# CRT/terminal displays (green/amber phosphor, paperwhite monitor, teletype
# paper) and are handled entirely in qml/ThemeImpl.qml (exposed to the rest
# of the QML tree as the context property "Theme" — see main.py).
THEME_TINTS = ("none", "green", "goldenrod", "white", "black")

# r-8.md "The glass lock": unlocked (normal) -> auto-locked (blurred/frozen
# until the mouse is inside the window, or a task is dropped in from another
# window) -> locked (permanently blurred/frozen) -> back to unlocked, cycled
# by clicking the lock icon (Main.qml). "unlocked" is the default so a brand
# new window is never born blurred/frozen.
LOCK_STATES = ("unlocked", "auto-locked", "locked")

DEFAULT_OPACITY_PERCENT = 65
MIN_OPACITY_PERCENT = 5
MAX_OPACITY_PERCENT = 100

DEFAULT_FONT_SCALE = 1.0
MIN_FONT_SCALE = 0.5
# Not literally unbounded — Qt's font.pixelSize is still a real int under
# the hood, and an astronomically large value risks overflow/undefined
# behavior there. 200x (2800px base task text at the default 14px) is
# effectively "as far as you'd ever actually zoom" while staying nowhere
# near that ceiling — picked over true infinity per explicit user request
# ("preferably indefinitely, even if it looks ugly and unreadable").
MAX_FONT_SCALE = 200.0


def monitor_signature() -> str:
    """A string identifying the current monitor layout (position + resolution
    of every screen), independent of enumeration order.

    Sorted rather than joined in `QGuiApplication.screens()`'s own order:
    that order is decided by the platform's output-detection sequence, which
    is not guaranteed stable across a full session restart (e.g. GNOME
    "Shutdown" then log back in) even when the physical monitors and their
    resolutions haven't changed at all — confirmed directly, the same two
    monitors report in a different order depending on detection timing.
    Treating that as "layout changed" made `_load_geometry` below discard a
    perfectly good saved position/size on an unlucky boot.
    """
    parts = []
    for screen in QGuiApplication.screens():
        geo = screen.geometry()
        parts.append(f"{geo.x()},{geo.y()},{geo.width()},{geo.height()}")
    return "|".join(sorted(parts))


def first_run_geometry() -> tuple[int, int, int, int]:
    """Centered on the primary screen, 20% of its width, 9:16 aspect ratio."""
    geo = QGuiApplication.primaryScreen().geometry()
    width = int(geo.width() * FIRST_RUN_WIDTH_RATIO)
    height = int(width * ASPECT_HEIGHT / ASPECT_WIDTH)
    x = geo.x() + (geo.width() - width) // 2
    y = geo.y() + (geo.height() - height) // 2
    return x, y, width, height


def _clamp_geometry_to_virtual_desktop(
    x: int, y: int, width: int, height: int
) -> tuple[int, int, int, int]:
    """Fit a previously saved (x, y, width, height) inside the union of all
    currently connected screens, shrinking/moving it as little as possible
    instead of discarding it outright.

    Used by `_load_geometry` when the monitor signature no longer matches
    what was stored — which can mean a genuine layout change (an external
    monitor unplugged), but can just as easily be a still-fitting old
    geometry paired with a signature that changed for an unrelated reason
    (a monitor added elsewhere, or — before monitor_signature() was made
    order-independent — pure output-enumeration reordering across a reboot).
    Jumping straight to `first_run_geometry()`'s small centered box in every
    such case is needlessly destructive, and since `_save_geometry` always
    rewrites x/y/width/height together, the very next unrelated geometry
    change (e.g. Main.qml's `ensureMinimumWidth()` on startup) would bake
    that wrong box in permanently. Clamping instead preserves the saved
    geometry byte-for-byte whenever it still fits.
    """
    virtual = QGuiApplication.primaryScreen().virtualGeometry()
    width = max(1, min(width, virtual.width()))
    height = max(1, min(height, virtual.height()))
    x = min(max(x, virtual.x()), virtual.x() + virtual.width() - width)
    y = min(max(y, virtual.y()), virtual.y() + virtual.height() - height)
    return x, y, width, height


class AppSettings(QObject):
    """Backed by QSettings; QML binds to these properties two-way."""

    xChanged = Signal()
    yChanged = Signal()
    widthChanged = Signal()
    heightChanged = Signal()
    themeModeChanged = Signal()
    themeTintChanged = Signal()
    borderColorChanged = Signal()
    opacityPercentChanged = Signal()
    fontScaleChanged = Signal()
    wheelZoomInvertedChanged = Signal()
    lockStateChanged = Signal()

    def __init__(self, settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self._settings = settings or QSettings("yata", "yata")
        self._x, self._y, self._width, self._height = self._load_geometry()
        mode = self._settings.value("theme/mode", "dark")
        self._theme_mode = mode if mode in THEME_MODES else "dark"
        tint = self._settings.value("theme/tint", "none")
        self._theme_tint = tint if tint in THEME_TINTS else "none"
        self._border_color = str(self._settings.value("theme/borderColor", ""))
        self._opacity_percent = self._clamp_opacity(
            self._settings.value("theme/opacityPercent", DEFAULT_OPACITY_PERCENT)
        )
        self._font_scale = self._clamp_font_scale(
            self._settings.value("theme/fontScale", DEFAULT_FONT_SCALE)
        )
        self._wheel_zoom_inverted = _read_bool(self._settings, "theme/wheelZoomInverted", False)
        lock_state = self._settings.value("theme/lockState", "unlocked")
        self._lock_state = lock_state if lock_state in LOCK_STATES else "unlocked"

    @staticmethod
    def _clamp_opacity(value) -> int:
        return max(MIN_OPACITY_PERCENT, min(MAX_OPACITY_PERCENT, int(round(float(value)))))

    @staticmethod
    def _clamp_font_scale(value) -> float:
        return max(MIN_FONT_SCALE, min(MAX_FONT_SCALE, float(value)))

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
            # Monitor signature mismatch: clamp the saved geometry into the
            # currently available space rather than discarding it for
            # first_run_geometry()'s unrelated small centered box — see
            # _clamp_geometry_to_virtual_desktop's docstring for why.
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

    def _get_theme_mode(self) -> str:
        return self._theme_mode

    def _set_theme_mode(self, value: str):
        if value not in THEME_MODES or value == self._theme_mode:
            return
        self._theme_mode = value
        self._settings.setValue("theme/mode", value)
        self._settings.sync()
        self.themeModeChanged.emit()

    themeMode = Property(str, _get_theme_mode, _set_theme_mode, notify=themeModeChanged)

    def _get_theme_tint(self) -> str:
        return self._theme_tint

    def _set_theme_tint(self, value: str):
        if value not in THEME_TINTS or value == self._theme_tint:
            return
        self._theme_tint = value
        self._settings.setValue("theme/tint", value)
        self._settings.sync()
        self.themeTintChanged.emit()

    themeTint = Property(str, _get_theme_tint, _set_theme_tint, notify=themeTintChanged)

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

    # Empty string means "no override, follow the theme's own border color"
    # (r-4.md) — a window's border outline and tag-name text switch to this
    # color (with a glow, same treatment as the task item menu's hover
    # icons) once set. No separate bool flag needed: "" already can't be a
    # valid CSS-style color string, so it's an unambiguous sentinel.
    borderColor = Property(str, _get_border_color, _set_border_color, notify=borderColorChanged)

    def _get_opacity_percent(self) -> int:
        return self._opacity_percent

    def _set_opacity_percent(self, value: int):
        value = self._clamp_opacity(value)
        if value == self._opacity_percent:
            return
        self._opacity_percent = value
        self._settings.setValue("theme/opacityPercent", value)
        self._settings.sync()
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
        self._settings.sync()
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
        self._settings.sync()
        self.wheelZoomInvertedChanged.emit()

    wheelZoomInverted = Property(
        bool, _get_wheel_zoom_inverted, _set_wheel_zoom_inverted, notify=wheelZoomInvertedChanged
    )

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

    # Read-only so QML can reset to these without hardcoding the values
    # itself in more than one place (the RESET button and the Ctrl+0
    # shortcut both need them).
    defaultOpacityPercent = Property(int, lambda self: DEFAULT_OPACITY_PERCENT, constant=True)
    defaultFontScale = Property(float, lambda self: DEFAULT_FONT_SCALE, constant=True)
    minFontScale = Property(float, lambda self: MIN_FONT_SCALE, constant=True)
    maxFontScale = Property(float, lambda self: MAX_FONT_SCALE, constant=True)

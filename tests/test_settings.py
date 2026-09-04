from PySide6.QtCore import QSettings

from settings import (
    DEFAULT_FONT_SCALE,
    DEFAULT_OPACITY_PERCENT,
    LOCK_STATES,
    MAX_FONT_SCALE,
    MIN_FONT_SCALE,
    AppSettings,
    first_run_geometry,
    monitor_signature,
)


def ini_settings(tmp_path, name="settings.ini"):
    return QSettings(str(tmp_path / name), QSettings.IniFormat)


def test_first_run_uses_centered_20_percent_9_16_geometry(tmp_path):
    settings = AppSettings(settings=ini_settings(tmp_path))

    expected_x, expected_y, expected_width, expected_height = first_run_geometry()
    assert (settings.x, settings.y, settings.width, settings.height) == (
        expected_x,
        expected_y,
        expected_width,
        expected_height,
    )
    assert settings.height == round(settings.width * 16 / 9)


def test_geometry_persists_across_restart_on_same_monitor_layout(tmp_path):
    backing = ini_settings(tmp_path)
    settings = AppSettings(settings=backing)
    settings.x = 111
    settings.y = 222
    settings.width = 333
    settings.height = 444
    backing.sync()

    restarted = AppSettings(settings=ini_settings(tmp_path))

    assert (restarted.x, restarted.y, restarted.width, restarted.height) == (111, 222, 333, 444)


def test_geometry_clamps_into_virtual_desktop_when_monitor_layout_changed(tmp_path):
    """Regression test: a monitor-signature mismatch used to discard the
    saved geometry outright for first_run_geometry()'s small centered box —
    destructive even when the mismatch was a false alarm (see
    test_monitor_signature_ignores_screen_order below) or when the old
    geometry would still mostly fit. It's now clamped into whatever screen
    space is currently available instead, preserving as much of the saved
    position/size as still fits."""
    backing = ini_settings(tmp_path)
    backing.setValue("window/monitorSignature", "not-the-real-signature")
    backing.setValue("window/x", 999)
    backing.setValue("window/y", 999)
    backing.setValue("window/width", 999)
    backing.setValue("window/height", 999)
    backing.sync()

    settings = AppSettings(settings=ini_settings(tmp_path))

    from PySide6.QtGui import QGuiApplication
    virtual = QGuiApplication.primaryScreen().virtualGeometry()
    assert settings.width == min(999, virtual.width())
    assert settings.height == min(999, virtual.height())
    assert virtual.x() <= settings.x <= virtual.x() + virtual.width() - settings.width
    assert virtual.y() <= settings.y <= virtual.y() + virtual.height() - settings.height
    # Confirmed genuinely different from the old reset-to-default behavior.
    assert (settings.x, settings.y, settings.width, settings.height) != first_run_geometry()


def test_geometry_untouched_when_saved_position_still_fits_despite_signature_mismatch(tmp_path):
    """A monitor-signature mismatch alone shouldn't move/resize a window that
    already fits fine in the currently available space — only genuinely
    out-of-bounds geometry should be adjusted."""
    backing = ini_settings(tmp_path)
    backing.setValue("window/monitorSignature", "not-the-real-signature")
    backing.setValue("window/x", 10)
    backing.setValue("window/y", 10)
    backing.setValue("window/width", 200)
    backing.setValue("window/height", 200)
    backing.sync()

    settings = AppSettings(settings=ini_settings(tmp_path))

    assert (settings.x, settings.y, settings.width, settings.height) == (10, 10, 200, 200)


def test_monitor_signature_is_stable_between_calls():
    assert monitor_signature() == monitor_signature()


def test_monitor_signature_ignores_screen_order(monkeypatch):
    """Regression test: QGuiApplication.screens()'s enumeration order isn't
    guaranteed stable across a full session restart (confirmed: GNOME
    "Shutdown" then logging back in can report the same physical monitors in
    a different order depending on output-detection timing), even though the
    actual layout hasn't changed. monitor_signature() used to join screens in
    whatever order screens() returned them, so that reordering alone made
    _load_geometry think the monitor layout had changed and discard the
    saved window geometry."""
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QGuiApplication

    class FakeScreen:
        def __init__(self, rect):
            self._rect = rect

        def geometry(self):
            return self._rect

    a = FakeScreen(QRect(0, 0, 1920, 1080))
    b = FakeScreen(QRect(1920, 0, 1080, 1920))

    monkeypatch.setattr(QGuiApplication, "screens", staticmethod(lambda: [a, b]))
    signature_ab = monitor_signature()
    monkeypatch.setattr(QGuiApplication, "screens", staticmethod(lambda: [b, a]))
    signature_ba = monitor_signature()

    assert signature_ab == signature_ba


def test_theme_defaults(tmp_path):
    settings = AppSettings(settings=ini_settings(tmp_path))
    assert settings.themeMode == "dark"
    assert settings.themeTint == "none"


def test_theme_setters_persist(tmp_path):
    backing = ini_settings(tmp_path)
    settings = AppSettings(settings=backing)

    settings.themeMode = "light"
    settings.themeTint = "goldenrod"
    backing.sync()

    restarted = AppSettings(settings=ini_settings(tmp_path))
    assert restarted.themeMode == "light"
    assert restarted.themeTint == "goldenrod"


def test_invalid_theme_values_are_ignored(tmp_path):
    settings = AppSettings(settings=ini_settings(tmp_path))

    settings.themeMode = "psychedelic"
    settings.themeTint = "chartreuse"

    assert settings.themeMode == "dark"
    assert settings.themeTint == "none"


def test_border_color_defaults_to_empty(tmp_path):
    """Empty string means "no custom color, follow the theme" (r-4.md)."""
    settings = AppSettings(settings=ini_settings(tmp_path))
    assert settings.borderColor == ""


def test_border_color_persists(tmp_path):
    backing = ini_settings(tmp_path)
    settings = AppSettings(settings=backing)

    settings.borderColor = "#ff8800"
    backing.sync()

    restarted = AppSettings(settings=ini_settings(tmp_path))
    assert restarted.borderColor == "#ff8800"


def test_border_color_can_be_reset_to_empty(tmp_path):
    backing = ini_settings(tmp_path)
    settings = AppSettings(settings=backing)
    settings.borderColor = "#ff8800"

    settings.borderColor = ""

    assert settings.borderColor == ""


def test_opacity_and_font_scale_defaults(tmp_path):
    settings = AppSettings(settings=ini_settings(tmp_path))
    assert settings.opacityPercent == DEFAULT_OPACITY_PERCENT == 65
    assert settings.fontScale == DEFAULT_FONT_SCALE == 1.0
    assert settings.defaultOpacityPercent == DEFAULT_OPACITY_PERCENT
    assert settings.defaultFontScale == DEFAULT_FONT_SCALE


def test_opacity_and_font_scale_persist(tmp_path):
    backing = ini_settings(tmp_path)
    settings = AppSettings(settings=backing)

    settings.opacityPercent = 42
    settings.fontScale = 1.5
    backing.sync()

    restarted = AppSettings(settings=ini_settings(tmp_path))
    assert restarted.opacityPercent == 42
    assert restarted.fontScale == 1.5


def test_opacity_percent_clamps_to_5_100_and_is_integer(tmp_path):
    settings = AppSettings(settings=ini_settings(tmp_path))

    settings.opacityPercent = 200
    assert settings.opacityPercent == 100

    settings.opacityPercent = -10
    assert settings.opacityPercent == 5

    settings.opacityPercent = 50.9
    assert settings.opacityPercent == 51
    assert isinstance(settings.opacityPercent, int)


def test_font_scale_clamps_to_min_and_max(tmp_path):
    settings = AppSettings(settings=ini_settings(tmp_path))

    settings.fontScale = MAX_FONT_SCALE + 100.0
    assert settings.fontScale == MAX_FONT_SCALE

    settings.fontScale = MIN_FONT_SCALE - 0.1
    assert settings.fontScale == MIN_FONT_SCALE

    assert settings.minFontScale == MIN_FONT_SCALE
    assert settings.maxFontScale == MAX_FONT_SCALE


def test_wheel_zoom_inverted_defaults_false_and_persists(tmp_path):
    backing = ini_settings(tmp_path)
    s = AppSettings(settings=backing)

    assert s.wheelZoomInverted is False

    s.wheelZoomInverted = True
    assert s.wheelZoomInverted is True

    s2 = AppSettings(settings=backing)
    assert s2.wheelZoomInverted is True


def test_lock_state_defaults_to_unlocked_and_persists(tmp_path):
    """r-8.md: unlocked is the safe default (a brand new window must never
    be born blurred/frozen)."""
    backing = ini_settings(tmp_path)
    s = AppSettings(settings=backing)

    assert s.lockState == "unlocked"

    s.lockState = "auto-locked"
    assert s.lockState == "auto-locked"

    s2 = AppSettings(settings=backing)
    assert s2.lockState == "auto-locked"


def test_lock_state_accepts_all_three_states(tmp_path):
    assert set(LOCK_STATES) == {"unlocked", "auto-locked", "locked"}
    for state in LOCK_STATES:
        s = AppSettings(settings=ini_settings(tmp_path, name=f"{state}.ini"))
        s.lockState = state
        assert s.lockState == state


def test_invalid_lock_state_is_ignored(tmp_path):
    s = AppSettings(settings=ini_settings(tmp_path))

    s.lockState = "super-locked"

    assert s.lockState == "unlocked"


def test_settings_persist_to_disk_without_explicit_caller_sync(tmp_path):
    """Regression test: every AppSettings setter used to call setValue()
    without ever calling sync() itself, relying entirely on QSettings'
    deferred/implicit flush (periodic auto-sync or sync-on-destruction).
    That flush depends on teardown ordering that isn't guaranteed —
    Python's GC order, a killed session, or the process exiting before the
    delayed write fires can all lose the change.

    Deliberately reads the *raw file bytes* from disk rather than via a
    second QSettings pointed at the same path: Qt caches an open file's
    QConfFile process-wide, so a second QSettings instance in the same
    process sees the unsynced in-memory value regardless of whether it was
    ever actually flushed to disk — which is exactly why the previous
    version of this test (constructing a fresh AppSettings against the same
    path, with an explicit backing.sync() the setter didn't need) passed
    even against the unfixed code. Confirmed via a stash A/B: this version
    fails without the .sync() calls in AppSettings' setters and passes with
    them."""
    ini_path = tmp_path / "settings.ini"
    s = AppSettings(settings=QSettings(str(ini_path), QSettings.IniFormat))
    s.wheelZoomInverted = True

    assert ini_path.exists()
    assert "wheelZoomInverted=true" in ini_path.read_text()

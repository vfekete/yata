from PySide6.QtCore import QSettings

from settings import (
    LOCK_STATES,
    MAX_ZOOM_LEVEL,
    MIN_ZOOM_LEVEL,
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
    assert (settings.x, settings.y, settings.width, settings.height) != first_run_geometry()


def test_geometry_untouched_when_saved_position_still_fits_despite_signature_mismatch(tmp_path):
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


def test_border_color_defaults_to_empty(tmp_path):
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


def test_lock_state_defaults_to_unlocked_and_persists(tmp_path):
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
    ini_path = tmp_path / "settings.ini"
    s = AppSettings(settings=QSettings(str(ini_path), QSettings.IniFormat))
    s.borderColor = "#ff8800"

    assert ini_path.exists()
    assert "borderColor=#ff8800" in ini_path.read_text()


def test_zoom_level_defaults_to_1_and_persists(tmp_path):
    backing = ini_settings(tmp_path)
    s = AppSettings(settings=backing)

    assert s.zoomLevel == 1.0
    assert s.defaultZoomLevel == 1.0

    s.zoomLevel = 1.5
    assert s.zoomLevel == 1.5

    s2 = AppSettings(settings=backing)
    assert s2.zoomLevel == 1.5


def test_zoom_level_clamps_to_min_and_max(tmp_path):
    s = AppSettings(settings=ini_settings(tmp_path))

    s.zoomLevel = MAX_ZOOM_LEVEL + 100.0
    assert s.zoomLevel == MAX_ZOOM_LEVEL

    s.zoomLevel = MIN_ZOOM_LEVEL - 0.1
    assert s.zoomLevel == MIN_ZOOM_LEVEL

    assert s.minZoomLevel == MIN_ZOOM_LEVEL
    assert s.maxZoomLevel == MAX_ZOOM_LEVEL


def test_wheel_zoom_inverted_defaults_false_and_persists(tmp_path):
    backing = ini_settings(tmp_path)
    s = AppSettings(settings=backing)

    assert s.wheelZoomInverted is False

    s.wheelZoomInverted = True
    assert s.wheelZoomInverted is True

    s2 = AppSettings(settings=backing)
    assert s2.wheelZoomInverted is True

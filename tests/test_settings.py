from PySide6.QtCore import QSettings

from settings import (
    DEFAULT_FONT_SCALE,
    DEFAULT_OPACITY_PERCENT,
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


def test_geometry_resets_to_first_run_when_monitor_layout_changed(tmp_path):
    backing = ini_settings(tmp_path)
    backing.setValue("window/monitorSignature", "not-the-real-signature")
    backing.setValue("window/x", 999)
    backing.setValue("window/y", 999)
    backing.setValue("window/width", 999)
    backing.setValue("window/height", 999)
    backing.sync()

    settings = AppSettings(settings=ini_settings(tmp_path))

    assert (settings.x, settings.y, settings.width, settings.height) == first_run_geometry()


def test_monitor_signature_is_stable_between_calls():
    assert monitor_signature() == monitor_signature()


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


def test_font_scale_clamps_to_0_5_2_0(tmp_path):
    settings = AppSettings(settings=ini_settings(tmp_path))

    settings.fontScale = 10.0
    assert settings.fontScale == 2.0

    settings.fontScale = 0.01
    assert settings.fontScale == 0.5


def test_wheel_zoom_inverted_defaults_false_and_persists(tmp_path):
    backing = ini_settings(tmp_path)
    s = AppSettings(settings=backing)

    assert s.wheelZoomInverted is False

    s.wheelZoomInverted = True
    assert s.wheelZoomInverted is True

    s2 = AppSettings(settings=backing)
    assert s2.wheelZoomInverted is True

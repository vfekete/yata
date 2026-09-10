from PySide6.QtCore import QSettings

from plugins.simple_task_list.settings import (
    DEFAULT_OPACITY_PERCENT,
    TaskListSettings,
)


def ini_settings(tmp_path, name="legacy.ini"):
    return QSettings(str(tmp_path / name), QSettings.IniFormat)


def test_theme_defaults_with_no_file_and_no_legacy_settings(tmp_path):
    settings = TaskListSettings(str(tmp_path / "plugin-state.json"))
    assert settings.themeMode == "dark"
    assert settings.themeTint == "none"


def test_theme_setters_persist_across_instances(tmp_path):
    path = str(tmp_path / "plugin-state.json")
    settings = TaskListSettings(path)

    settings.themeMode = "light"
    settings.themeTint = "goldenrod"

    restarted = TaskListSettings(path)
    assert restarted.themeMode == "light"
    assert restarted.themeTint == "goldenrod"


def test_invalid_theme_values_are_ignored(tmp_path):
    settings = TaskListSettings(str(tmp_path / "plugin-state.json"))

    settings.themeMode = "psychedelic"
    settings.themeTint = "chartreuse"

    assert settings.themeMode == "dark"
    assert settings.themeTint == "none"


def test_opacity_defaults(tmp_path):
    settings = TaskListSettings(str(tmp_path / "plugin-state.json"))
    assert settings.opacityPercent == DEFAULT_OPACITY_PERCENT == 65
    assert settings.defaultOpacityPercent == DEFAULT_OPACITY_PERCENT


def test_opacity_persists(tmp_path):
    path = str(tmp_path / "plugin-state.json")
    settings = TaskListSettings(path)

    settings.opacityPercent = 42

    restarted = TaskListSettings(path)
    assert restarted.opacityPercent == 42


def test_opacity_percent_clamps_to_5_100_and_is_integer(tmp_path):
    settings = TaskListSettings(str(tmp_path / "plugin-state.json"))

    settings.opacityPercent = 200
    assert settings.opacityPercent == 100

    settings.opacityPercent = -10
    assert settings.opacityPercent == 5

    settings.opacityPercent = 50.9
    assert settings.opacityPercent == 51
    assert isinstance(settings.opacityPercent, int)


def test_migrates_from_legacy_qsettings_on_first_load(tmp_path):
    """r-9.md step 4: existing installs had these keys in the per-window
    QSettings .conf (settings.py's AppSettings, before this class existed)
    — must be picked up once, not reset to defaults. fontScale/
    wheelZoomInverted are no longer part of this migration (zoom moved to
    the host's own AppSettings in a later follow-up) — this class simply
    never reads those two legacy keys at all now."""
    legacy = ini_settings(tmp_path)
    legacy.setValue("theme/mode", "light")
    legacy.setValue("theme/tint", "green")
    legacy.setValue("theme/opacityPercent", 80)
    legacy.sync()

    settings = TaskListSettings(str(tmp_path / "plugin-state.json"), legacy)

    assert settings.themeMode == "light"
    assert settings.themeTint == "green"
    assert settings.opacityPercent == 80


def test_migration_writes_the_new_file_so_legacy_is_not_reread(tmp_path):
    path = str(tmp_path / "plugin-state.json")
    legacy = ini_settings(tmp_path)
    legacy.setValue("theme/mode", "light")
    legacy.sync()

    TaskListSettings(path, legacy)

    # Change the legacy file after migration -- a second instance must NOT
    # pick it up again, since the new file already exists.
    legacy.setValue("theme/mode", "dark")
    legacy.sync()

    restarted = TaskListSettings(path, legacy)
    assert restarted.themeMode == "light"


def test_no_legacy_settings_and_no_file_uses_hardcoded_defaults(tmp_path):
    settings = TaskListSettings(str(tmp_path / "plugin-state.json"), legacy_settings=None)
    assert settings.themeMode == "dark"
    assert settings.opacityPercent == DEFAULT_OPACITY_PERCENT

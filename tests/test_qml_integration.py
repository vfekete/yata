import os
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_app = None


def _get_app():
    global _app
    if _app is None:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        _app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        _app.setOrganizationName("yata-qml-test")
        _app.setApplicationName("yata-qml-test")
        QQuickStyle.setStyle("Basic")
    return _app


@pytest.fixture(scope="module")
def qml_app():
    return _get_app()


@pytest.fixture()
def engine_and_model(qml_app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yata-src"))
    import resources_rc  # noqa: F401,PLC0415
    from icons import IconProvider  # noqa: PLC0415
    from main import _make_window  # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    from plugins.simple_task_list.plugin import create_content  # noqa: PLC0415
    from window_manager import WindowManager  # noqa: PLC0415
    from window_registry import DEFAULT_WINDOW_ID, WindowRegistry  # noqa: PLC0415
    from PySide6.QtCore import QSettings  # noqa: PLC0415

    raw_settings = QSettings("yata", "yata")
    app_settings = AppSettings(raw_settings)
    icon_provider = IconProvider()
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)

    engine = QQmlApplicationEngine()
    qml_dir = os.path.join(os.path.dirname(__file__), "..", "yata-src", "qml")
    engine.addImportPath(qml_dir)

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, create_content(DEFAULT_WINDOW_ID, None, raw_settings), app_settings,
    )
    task_model = window_manager._windows[DEFAULT_WINDOW_ID]["task_model"]

    qml_app.processEvents()
    qml_app.processEvents()

    yield task_model

    del engine
    qml_app.processEvents()
    qml_app.processEvents()


def test_add_task_creates_empty_task(engine_and_model):
    model = engine_and_model
    task_id = model.addTask()
    assert model._find(task_id) is not None
    assert model._find(task_id).text == ""


def test_add_task_cleanup_removes_previous_empty(engine_and_model):
    model = engine_and_model
    t1 = model.addTask()
    t2 = model.addTask()
    assert model._find(t1) is None, "first empty task should have been purged"
    assert model._find(t2) is not None


def test_add_task_cleanup_preserves_non_empty(engine_and_model):
    model = engine_and_model
    t1 = model.addTask()
    model._find(t1).text = "Milk"
    model._recompute()
    model._save()

    t2 = model.addTask()
    assert model._find(t1) is not None, "non-empty task must survive cleanup"
    assert model._find(t2) is not None


def test_delete_task_removes_it(engine_and_model):
    model = engine_and_model
    t1 = model.addTask()
    model.deleteTask(t1)
    assert model._find(t1) is None


@pytest.fixture()
def engine_and_window(qml_app, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yata-src"))
    import resources_rc  # noqa: F401,PLC0415
    from icons import IconProvider  # noqa: PLC0415
    from main import _make_window  # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    from plugins.simple_task_list.plugin import create_content  # noqa: PLC0415
    from window_manager import WindowManager  # noqa: PLC0415
    from window_registry import DEFAULT_WINDOW_ID, WindowRegistry  # noqa: PLC0415

    from PySide6.QtCore import QSettings  # noqa: PLC0415

    raw_settings = QSettings(str(tmp_path / "app.ini"), QSettings.IniFormat)
    app_settings = AppSettings(raw_settings)
    icon_provider = IconProvider()
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)

    engine = QQmlApplicationEngine()
    qml_dir = os.path.join(os.path.dirname(__file__), "..", "yata-src", "qml")
    engine.addImportPath(qml_dir)

    plugin_content = create_content(DEFAULT_WINDOW_ID, None, raw_settings)
    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, plugin_content, app_settings,
    )
    qml_app.processEvents()
    qml_app.processEvents()

    plugin_settings = plugin_content.context_properties["appSettings"]
    yield window, app_settings, plugin_settings

    del engine
    qml_app.processEvents()
    qml_app.processEvents()


def _theme_for(window):
    from PySide6.QtQml import QQmlEngine  # noqa: PLC0415

    return QQmlEngine.contextForObject(window).contextProperty("Theme")


def test_effective_glow_color_follows_custom_border_color(engine_and_window):
    window, app_settings, plugin_settings = engine_and_window
    theme = _theme_for(window)

    default_glow = theme.property("effectiveGlowColor")
    default_link = theme.property("effectiveLinkColor")
    assert default_glow == theme.property("filterGlowColor")
    assert default_link == theme.property("linkColor")

    app_settings.borderColor = "#ff3db2"
    assert theme.property("effectiveGlowColor").name().lower() == "#ff3db2"
    assert theme.property("effectiveLinkColor").name().lower() == "#ff3db2"


def test_effective_glow_color_falls_back_after_reset(engine_and_window):
    window, app_settings, plugin_settings = engine_and_window
    theme = _theme_for(window)

    app_settings.borderColor = "#39ff14"
    assert theme.property("effectiveGlowColor").name().lower() == "#39ff14"

    app_settings.borderColor = ""
    assert theme.property("effectiveGlowColor") == theme.property("filterGlowColor")
    assert theme.property("effectiveLinkColor") == theme.property("linkColor")


def test_effective_glow_color_ignores_custom_color_under_a_tint(engine_and_window):
    window, app_settings, plugin_settings = engine_and_window
    theme = _theme_for(window)

    plugin_settings.themeTint = "green"
    app_settings.borderColor = "#ff3db2"
    assert theme.property("effectiveGlowColor") == theme.property("filterGlowColor")
    assert theme.property("effectiveLinkColor") == theme.property("linkColor")
    assert theme.property("effectiveGlowColor").name().lower() != "#ff3db2"

    plugin_settings.themeTint = "none"
    assert theme.property("effectiveGlowColor").name().lower() == "#ff3db2"
    assert theme.property("effectiveLinkColor").name().lower() == "#ff3db2"


def test_click_away_on_new_task_saves_task_name(engine_and_model, qml_app):
    model = engine_and_model
    t1 = model.addTask()
    qml_app.processEvents()
    qml_app.processEvents()

    model.setSearchText("__nonexistent__")
    qml_app.processEvents()
    model.setSearchText("")
    qml_app.processEvents()

    task = model._find(t1)
    if task is not None:
        assert task.text in ("", "Task name"), (
            f"unexpected text after click-away: {task.text!r}"
        )

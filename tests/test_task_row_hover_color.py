"""Tests for the task row's hover-on background following this window's
custom color (r-4.md, assigned via the YATAS list) instead of the generic
grey, without touching CRT tints (each already tints its own hover color).

Runs against a real QML engine (offscreen), same construction pattern as
test_qml_integration.py/test_focus_behavior.py/test_lock_feature.py, so the
actual TaskDelegate.rowHoverColor binding is exercised, not a re-implemented
equivalent.
"""
import os
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_app = None


def _get_app():
    global _app
    if _app is None:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        _app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        _app.setOrganizationName("yata-hover-color-test")
        _app.setApplicationName("yata-hover-color-test")
        QQuickStyle.setStyle("Basic")
    return _app


@pytest.fixture()
def qml_window(tmp_path, monkeypatch):
    """Yields (app, window, app_settings, task_model) with one real task
    delegate already on screen — same real construction path as the other
    QML integration test files (main._make_window), not a hand-rolled
    equivalent."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    app = _get_app()

    src = os.path.join(os.path.dirname(__file__), "..", "yata-src")
    sys.path.insert(0, src)
    import resources_rc  # noqa: F401,PLC0415 — registers qrc:/icons/*.svg etc.
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
    qml_dir = os.path.join(src, "qml")
    engine.addImportPath(qml_dir)

    plugin_content = create_content(DEFAULT_WINDOW_ID, None, raw_settings)
    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, plugin_content, app_settings,
    )
    task_model = window_manager._windows[DEFAULT_WINDOW_ID]["task_model"]

    task_id = task_model.addTask()
    task_model.setText(task_id, "Buy milk")
    app.processEvents()
    app.processEvents()
    QTest.qWait(200)
    app.processEvents()

    # app_settings: host-owned (borderColor/lockState/geometry). The
    # plugin's own settings (themeMode/themeTint/...) are a separate
    # object — see plugin_content's own "appSettings" entry.
    plugin_settings = plugin_content.context_properties["appSettings"]
    yield app, window, app_settings, task_model, plugin_settings

    del engine
    app.processEvents()
    app.processEvents()


def _find_by_class_prefix(item, prefix, results=None):
    if results is None:
        results = []
    if item.metaObject().className().startswith(prefix):
        results.append(item)
    for child in item.childItems():
        _find_by_class_prefix(child, prefix, results)
    return results


def _row(window):
    delegates = _find_by_class_prefix(window.contentItem(), "TaskDelegate")
    assert delegates, "no TaskDelegate row found"
    return delegates[0]


def test_hover_color_stays_grey_without_a_custom_color(qml_window):
    app, window, app_settings, task_model, plugin_settings = qml_window
    row = _row(window)

    assert app_settings.borderColor == ""
    # Compare against the live Theme instance's own hoverColor rather than a
    # hardcoded value, so this doesn't need updating if the palette changes.
    from PySide6.QtQml import QQmlEngine
    theme = QQmlEngine.contextForObject(window).contextProperty("Theme")
    assert row.property("rowHoverColor") == theme.property("hoverColor")


def test_hover_color_follows_custom_border_color_under_none_tint(qml_window):
    app, window, app_settings, task_model, plugin_settings = qml_window
    row = _row(window)

    app_settings.borderColor = "#2563eb"  # a distinct blue, unlikely to collide with any theme default
    app.processEvents()

    custom = row.property("effectiveBorderColor")
    hover = row.property("rowHoverColor")
    assert hover.alphaF() < 0.5, "should be a subtle wash, not a solid block"
    assert abs(hover.redF() - custom.redF()) < 0.01
    assert abs(hover.greenF() - custom.greenF()) < 0.01
    assert abs(hover.blueF() - custom.blueF()) < 0.01


def test_hover_color_ignores_custom_border_color_under_a_crt_tint(qml_window):
    """CRT/terminal tints are explicitly out of scope for this feature —
    each already tints its own Theme.hoverColor to its own phosphor color
    (ThemeImpl.qml's palettes), so a custom border color must not override
    that."""
    app, window, app_settings, task_model, plugin_settings = qml_window
    row = _row(window)

    app_settings.borderColor = "#2563eb"
    plugin_settings.themeTint = "green"
    app.processEvents()

    from PySide6.QtQml import QQmlEngine
    theme = QQmlEngine.contextForObject(window).contextProperty("Theme")
    assert row.property("rowHoverColor") == theme.property("hoverColor")

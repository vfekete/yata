"""Regression: a saved window narrower than the old 600px placeholder
minimum (applied while the plugin content hadn't loaded yet) must keep its
saved width across a restart, instead of being enlarged to 600 and
persisted."""
import os
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def _get_app():
    app = QGuiApplication.instance()
    if app is None:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        app = QGuiApplication(sys.argv)
        QQuickStyle.setStyle("Basic")
    return app


@pytest.fixture()
def restore_window(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    app = _get_app()

    src = os.path.join(os.path.dirname(__file__), "..", "yata-src")
    sys.path.insert(0, src)
    import resources_rc  # noqa: F401,PLC0415
    from icons import IconProvider  # noqa: PLC0415
    from main import _make_window, _open_settings  # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    import plugins_registry  # noqa: PLC0415
    from window_manager import WindowManager  # noqa: PLC0415
    from window_registry import DEFAULT_WINDOW_ID, WindowRegistry  # noqa: PLC0415

    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(src, "qml"))
    for plugin in plugins_registry.AVAILABLE_PLUGINS.values():
        if plugin.qml_import_dir:
            engine.addImportPath(plugin.qml_import_dir)

    icon_provider = IconProvider()

    def make(width, zoom=1.0):
        legacy_qsettings = _open_settings(DEFAULT_WINDOW_ID)
        host_settings = AppSettings(legacy_qsettings)
        host_settings.width = width
        host_settings.height = 260
        host_settings.zoomLevel = zoom
        plugin = plugins_registry.get(registry.get_plugin(DEFAULT_WINDOW_ID))
        plugin_content = plugin.create_content(DEFAULT_WINDOW_ID, None, legacy_qsettings)
        window = _make_window(
            engine, icon_provider, window_manager, QIcon(),
            DEFAULT_WINDOW_ID, plugin_content, host_settings,
        )
        app.processEvents()
        app.processEvents()
        return window, host_settings, legacy_qsettings

    yield make
    del engine


@pytest.mark.parametrize("zoom", [0.9, 1.0, 1.2])
def test_saved_narrow_width_survives_restore(restore_window, zoom):
    window, host_settings, qsettings = restore_window(448, zoom)
    real_minimum = window.minimumWidth()
    assert real_minimum < 448
    assert window.width() == 448
    assert host_settings.width == 448
    assert int(qsettings.value("window/width")) == 448


def test_width_below_real_minimum_is_still_clamped(restore_window):
    window, host_settings, _ = restore_window(100)
    assert window.width() == window.minimumWidth() > 100
    assert host_settings.width == window.minimumWidth()

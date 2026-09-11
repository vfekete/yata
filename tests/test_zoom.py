import os
import sys

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QGuiApplication, QIcon, QWheelEvent
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
        _app.setOrganizationName("yata-zoom-test")
        _app.setApplicationName("yata-zoom-test")
        QQuickStyle.setStyle("Basic")
    return _app


def _send_ctrl_wheel(window, pos, angle_delta_y):
    event = QWheelEvent(
        QPointF(pos), window.mapToGlobal(pos),
        QPoint(0, 0), QPoint(0, angle_delta_y),
        Qt.NoButton, Qt.ControlModifier, Qt.NoScrollPhase, False,
    )
    QGuiApplication.sendEvent(window, event)


@pytest.fixture()
def yata_window(tmp_path, monkeypatch):
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

    icon_provider = IconProvider()
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(src, "qml"))
    for plugin in plugins_registry.AVAILABLE_PLUGINS.values():
        if plugin.qml_import_dir:
            engine.addImportPath(plugin.qml_import_dir)

    legacy_qsettings = _open_settings(DEFAULT_WINDOW_ID)
    plugin = plugins_registry.get(registry.get_plugin(DEFAULT_WINDOW_ID))
    plugin_content = plugin.create_content(DEFAULT_WINDOW_ID, None, legacy_qsettings)
    host_settings = AppSettings(legacy_qsettings)
    host_settings.width = 700
    host_settings.height = 500

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, plugin_content, host_settings,
    )
    app.processEvents()
    app.processEvents()

    yield app, window, host_settings

    del engine
    app.processEvents()
    app.processEvents()


def test_zoom_level_defaults_to_1_per_window(yata_window):
    app, window, host_settings = yata_window
    assert host_settings.zoomLevel == 1.0


def test_ctrl_0_shortcut_resets_to_default(yata_window):
    app, window, host_settings = yata_window
    host_settings.zoomLevel = 1.7

    QTest.keyClick(window, Qt.Key_0, Qt.ControlModifier)
    app.processEvents()

    assert host_settings.zoomLevel == host_settings.defaultZoomLevel


def test_ctrl_wheel_zooms_while_plugin_content_showing(yata_window):
    app, window, host_settings = yata_window
    before = host_settings.zoomLevel

    _send_ctrl_wheel(window, QPoint(350, 250), 120)
    app.processEvents()

    assert host_settings.zoomLevel > before


def test_ctrl_wheel_zooms_while_yatas_view_showing(yata_window):
    app, window, host_settings = yata_window
    window.setProperty("yatasActive", True)
    app.processEvents()
    before = host_settings.zoomLevel

    _send_ctrl_wheel(window, QPoint(350, 250), 120)
    app.processEvents()

    assert host_settings.zoomLevel > before


def test_ctrl_0_shortcut_works_while_yatas_view_showing(yata_window):
    app, window, host_settings = yata_window
    host_settings.zoomLevel = 1.7
    window.setProperty("yatasActive", True)
    app.processEvents()

    QTest.keyClick(window, Qt.Key_0, Qt.ControlModifier)
    app.processEvents()

    assert host_settings.zoomLevel == host_settings.defaultZoomLevel


def test_wheel_zoom_inverted_flips_scroll_direction(yata_window):
    app, window, host_settings = yata_window
    host_settings.wheelZoomInverted = True
    before = host_settings.zoomLevel

    _send_ctrl_wheel(window, QPoint(350, 250), 120)
    app.processEvents()

    assert host_settings.zoomLevel < before


def test_plugin_font_size_reflects_host_zoom_level(yata_window):
    app, window, host_settings = yata_window

    def find_by_class(item, prefix, results=None):
        if results is None:
            results = []
        if item.metaObject().className().startswith(prefix):
            results.append(item)
        for child in item.childItems():
            find_by_class(child, prefix, results)
        return results

    host_settings.zoomLevel = 2.0
    app.processEvents()

    texts = find_by_class(window.contentItem(), "QQuickText")
    sizes = {t.property("font").pixelSize() for t in texts if t.property("font")}
    assert 28 in sizes, f"expected some text at round(14*2.0)=28px, got {sorted(sizes)}"


def test_yatas_view_font_size_reflects_host_zoom_level(yata_window):
    app, window, host_settings = yata_window

    def find_by_class(item, prefix, results=None):
        if results is None:
            results = []
        if item.metaObject().className().startswith(prefix):
            results.append(item)
        for child in item.childItems():
            find_by_class(child, prefix, results)
        return results

    window.setProperty("yatasActive", True)
    app.processEvents()

    yatas_view = next(
        w for w in find_by_class(window.contentItem(), "YatasView")
    )

    host_settings.zoomLevel = 1.0
    app.processEvents()
    default_sizes = {t.property("font").pixelSize() for t in find_by_class(yatas_view, "QQuickText") if t.property("font")}
    assert 14 in default_sizes, f"expected some text at 14px, got {sorted(default_sizes)}"

    host_settings.zoomLevel = 2.0
    app.processEvents()
    zoomed_sizes = {t.property("font").pixelSize() for t in find_by_class(yatas_view, "QQuickText") if t.property("font")}
    assert 28 in zoomed_sizes, f"expected some text at round(14*2.0)=28px, got {sorted(zoomed_sizes)}"

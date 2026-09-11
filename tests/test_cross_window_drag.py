import os
import sys

import pytest
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_app = None


def _get_app():
    global _app
    if _app is None:
        from PySide6.QtCore import Qt

        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        _app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        _app.setOrganizationName("yata-cross-window-drag-test")
        _app.setApplicationName("yata-cross-window-drag-test")
        QQuickStyle.setStyle("Basic")
    return _app


def _find_by_class_prefix(item, prefix, results=None):
    if results is None:
        results = []
    if item.metaObject().className().startswith(prefix):
        results.append(item)
    for child in item.childItems():
        _find_by_class_prefix(child, prefix, results)
    return results


@pytest.fixture()
def two_windows(tmp_path, monkeypatch):
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
    from window_registry import WindowRegistry  # noqa: PLC0415

    icon_provider = IconProvider()
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(src, "qml"))
    for plugin in plugins_registry.AVAILABLE_PLUGINS.values():
        if plugin.qml_import_dir:
            engine.addImportPath(plugin.qml_import_dir)

    def build(window_id, x, y, w, h):
        legacy_qsettings = _open_settings(window_id)
        plugin = plugins_registry.get(registry.get_plugin(window_id))
        plugin_content = plugin.create_content(window_id, None, legacy_qsettings)
        host_settings = AppSettings(legacy_qsettings)
        host_settings.x, host_settings.y = x, y
        host_settings.width, host_settings.height = w, h
        return _make_window(engine, icon_provider, window_manager, QIcon(), window_id, plugin_content, host_settings)

    id_a = registry.add("A")
    id_b = registry.add("B")
    window_a = build(id_a, 0, 0, 400, 400)
    window_b = build(id_b, 600, 0, 400, 400)
    app.processEvents()
    app.processEvents()

    yield app, window_manager, window_a, id_a, window_b, id_b

    del engine
    app.processEvents()
    app.processEvents()


def _list_view(window):
    views = _find_by_class_prefix(window.contentItem(), "QQuickListView")
    assert views, "ListView not found"
    return views[0]


def test_drag_hover_sets_plugin_side_list_reflow_on_target_window(two_windows):
    app, window_manager, window_a, id_a, window_b, id_b = two_windows

    point_in_b = (700, 100)
    found = window_manager.windowAt(*point_in_b)
    app.processEvents()

    assert found == id_b
    assert _list_view(window_b).property("dragHoverActive") is True, (
        "the plugin's own list reflow must react to a drag hovering over "
        "this window, independently of Main.qml's host-side border highlight"
    )
    assert _list_view(window_a).property("dragHoverActive") is False


def test_drag_hover_clears_when_leaving_the_window(two_windows):
    app, window_manager, window_a, id_a, window_b, id_b = two_windows

    window_manager.windowAt(700, 100)
    app.processEvents()
    assert _list_view(window_b).property("dragHoverActive") is True

    window_manager.windowAt(-1000, -1000)
    app.processEvents()
    assert _list_view(window_b).property("dragHoverActive") is False

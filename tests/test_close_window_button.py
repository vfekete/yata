import os
import sys

import pytest
from PySide6.QtCore import QPoint, Qt
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
        _app.setOrganizationName("yata-close-button-test")
        _app.setApplicationName("yata-close-button-test")
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


def _close_icon_box(window):
    rects = [
        r for r in _find_by_class_prefix(window.contentItem(), "QQuickRectangle")
        if r.mapToItem(window.contentItem(), 0, 0).y() < 5
        and r.mapToItem(window.contentItem(), 0, 0).x() > window.width() - 60
    ]
    assert rects, "close icon background box not found near the top-right corner"
    rects.sort(key=lambda r: -r.mapToItem(window.contentItem(), 0, 0).x())
    return rects[0]


def _center_point(window, item):
    center = item.mapToItem(window.contentItem(), item.width() / 2, item.height() / 2)
    return QPoint(round(center.x()), round(center.y()))


def _close_button_center(window):
    return _center_point(window, _close_icon_box(window))


def _close_mouse_area(box):
    areas = [c for c in box.childItems() if c.metaObject().className().startswith("QQuickMouseArea")]
    assert len(areas) == 1, f"expected exactly one MouseArea on the close icon box, found {len(areas)}"
    return areas[0]


@pytest.fixture()
def two_windows(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    app = _get_app()

    src = os.path.join(os.path.dirname(__file__), "..", "yata-src")
    sys.path.insert(0, src)
    import resources_rc  # noqa: F401,PLC0415
    from icons import IconProvider  # noqa: PLC0415
    from main import _make_window  # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    from plugins.simple_task_list.plugin import create_content  # noqa: PLC0415
    from window_manager import WindowManager  # noqa: PLC0415
    from window_registry import DEFAULT_WINDOW_ID, WindowRegistry  # noqa: PLC0415
    from PySide6.QtCore import QSettings  # noqa: PLC0415

    icon_provider = IconProvider()
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(src, "qml"))

    def window_factory(window_id, caller_state):
        raw = QSettings(str(tmp_path / f"app-{window_id}.ini"), QSettings.IniFormat)
        settings = AppSettings(raw)
        plugin_content = create_content(window_id, str(tmp_path / f"instance-{window_id}"), raw)
        _make_window(engine, icon_provider, window_manager, QIcon(), window_id, plugin_content, settings)

    window_manager = WindowManager(registry, window_factory=window_factory)

    raw_settings1 = QSettings(str(tmp_path / "app-default.ini"), QSettings.IniFormat)
    app_settings1 = AppSettings(raw_settings1)
    plugin_content1 = create_content(DEFAULT_WINDOW_ID, str(tmp_path / "instance-default"), raw_settings1)
    window1 = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, plugin_content1, app_settings1,
    )
    app.processEvents()
    app.processEvents()

    id2 = window_manager.createWindow({
        "themeMode": "dark", "themeTint": "none", "opacityPercent": 65,
        "fontScale": 1.0, "wheelZoomInverted": False,
        "x": 400, "y": 400, "width": 300, "height": 400,
    })
    app.processEvents()
    QTest.qWait(150)
    app.processEvents()
    window2 = window_manager._windows[id2]["window"]

    yield app, window_manager, window1, DEFAULT_WINDOW_ID, window2, id2

    del engine
    app.processEvents()
    app.processEvents()


def test_close_button_closes_this_window_when_another_is_open(two_windows):
    app, window_manager, window1, id1, window2, id2 = two_windows
    assert window_manager.is_open(id1)
    assert window_manager.is_open(id2)

    QTest.mouseClick(window1, Qt.LeftButton, Qt.NoModifier, _close_button_center(window1))
    app.processEvents()

    assert not window_manager.is_open(id1), "clicking close should close this window"
    assert window_manager.is_open(id2), "the other window must be untouched"


def test_close_button_is_a_noop_on_the_last_open_window(two_windows):
    app, window_manager, window1, id1, window2, id2 = two_windows

    QTest.mouseClick(window1, Qt.LeftButton, Qt.NoModifier, _close_button_center(window1))
    app.processEvents()
    assert not window_manager.is_open(id1)
    assert window_manager.is_open(id2)

    QTest.mouseClick(window2, Qt.LeftButton, Qt.NoModifier, _close_button_center(window2))
    app.processEvents()

    assert window_manager.is_open(id2), "closing the only remaining window must be a no-op"


def test_close_button_looks_disabled_once_it_is_the_only_window(two_windows):
    app, window_manager, window1, id1, window2, id2 = two_windows

    box1 = _close_icon_box(window1)
    assert box1.property("opacity") == 1.0
    assert _close_mouse_area(box1).property("enabled") is True

    QTest.mouseClick(window1, Qt.LeftButton, Qt.NoModifier, _center_point(window1, box1))
    app.processEvents()
    assert not window_manager.is_open(id1)

    box2 = _close_icon_box(window2)
    assert box2.property("opacity") < 1.0, "the remaining window's close button must look disabled"
    mouse_area2 = _close_mouse_area(box2)
    assert mouse_area2.property("enabled") is False

    QTest.mouseMove(window2, _center_point(window2, box2))
    app.processEvents()
    assert mouse_area2.property("containsMouse") is False, "must not hover-react while disabled"

"""Regression test for the tag label's double-click-to-rename gesture
(r-3.md), specifically the interaction with r-9.md step 4's new
drag-to-move handle on that same area.

Bug: Main.qml's tagLabelBg gained a MouseArea calling
Window.startSystemMove() unconditionally onPressed (needed once the
plugin's own Toolbar no longer spans host-owned space and so no longer
doubles as the drag handle). startSystemMove() hands the pointer grab to
the window manager the instant it's called, which silently ate the second
click of a double-click before the sibling TapHandler's onDoubleTapped
ever saw it -- confirmed live (double-click-to-rename simply stopped
working the moment the drag handle was added, in a real X11 session, while
working fine against the same gesture on the pre-step-4 code). Fixed by
using a DragHandler (only goes active once the press has moved past Qt's
drag threshold) instead of a MouseArea.onPressed (fires immediately, before
any movement).

Runs against a real QML engine (offscreen) using QTest.mouseDClick, same
construction pattern as test_lock_feature.py/test_focus_behavior.py.
"""
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
        _app.setOrganizationName("yata-tag-rename-test")
        _app.setApplicationName("yata-tag-rename-test")
        QQuickStyle.setStyle("Basic")
    return _app


@pytest.fixture()
def qml_window(tmp_path, monkeypatch):
    """Yields (app, window, window_manager, window_id) — same real
    construction path as test_lock_feature.py's own fixture."""
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

    raw_settings = QSettings(str(tmp_path / "app.ini"), QSettings.IniFormat)
    app_settings = AppSettings(raw_settings)
    icon_provider = IconProvider()
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)

    engine = QQmlApplicationEngine()
    qml_dir = os.path.join(src, "qml")
    engine.addImportPath(qml_dir)

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, create_content(DEFAULT_WINDOW_ID, None, raw_settings), app_settings,
    )
    app.processEvents()
    app.processEvents()

    yield app, window, window_manager, DEFAULT_WINDOW_ID

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


def _find_tag_label(window):
    texts = [
        t for t in _find_by_class_prefix(window.contentItem(), "QQuickText")
        if t.property("text") == window.property("windowTag")
    ]
    assert texts, "tag label Text not found"
    return texts[0]


def _center_point(window, item):
    center = item.mapToItem(window.contentItem(), item.width() / 2, item.height() / 2)
    return QPoint(round(center.x()), round(center.y()))


def test_double_click_tag_label_enters_rename_mode(qml_window):
    app, window, window_manager, window_id = qml_window
    point = _center_point(window, _find_tag_label(window))

    assert window.property("editingTag") is False
    QTest.mouseDClick(window, Qt.LeftButton, Qt.NoModifier, point)
    app.processEvents()
    assert window.property("editingTag") is True, (
        "double-click on the tag label must enter rename mode, even though "
        "the same area also starts a window drag on press"
    )


def test_single_click_tag_label_does_not_enter_rename_mode(qml_window):
    """A plain single click (e.g. the start of a real drag) must not be
    mistaken for a rename request."""
    app, window, window_manager, window_id = qml_window
    point = _center_point(window, _find_tag_label(window))

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    app.processEvents()
    assert window.property("editingTag") is False

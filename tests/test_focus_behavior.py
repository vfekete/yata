import os
import sys
import pytest

from PySide6.QtCore import Qt, QPoint
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
        _app.setOrganizationName("yata-focus-test")
        _app.setApplicationName("yata-focus-test")
        QQuickStyle.setStyle("Basic")
    return _app


@pytest.fixture()
def qml_window(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    app = _get_app()

    src = os.path.join(os.path.dirname(__file__), "..", "yata-src")
    sys.path.insert(0, src)
    import resources_rc  # noqa: F401,PLC0415
    from icons import IconProvider    # noqa: PLC0415
    from main import _make_window     # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    from plugins.simple_task_list.plugin import create_content     # noqa: PLC0415
    from window_manager import WindowManager  # noqa: PLC0415
    from window_registry import DEFAULT_WINDOW_ID, WindowRegistry  # noqa: PLC0415
    from PySide6.QtCore import QSettings  # noqa: PLC0415

    raw_settings = QSettings("yata", "yata")
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
    task_model = window_manager._windows[DEFAULT_WINDOW_ID]["task_model"]

    app.processEvents()
    app.processEvents()

    yield app, task_model, window

    del engine
    app.processEvents()
    app.processEvents()


def _focus_class(window):
    item = window.activeFocusItem()
    if item is None:
        return "None"
    return item.metaObject().className()


def _is_textfield_focused(window):
    cls = _focus_class(window)
    return "TextField" in cls or "TextInput" in cls


def _find_by_class_prefix(item, prefix, results=None):
    if results is None:
        results = []
    if item.metaObject().className().startswith(prefix):
        results.append(item)
    for child in item.childItems():
        _find_by_class_prefix(child, prefix, results)
    return results


def _task_row_center(window, row_index):
    delegates = _find_by_class_prefix(window.contentItem(), "TaskDelegate")
    delegates.sort(key=lambda item: item.mapToItem(window.contentItem(), 0, 0).y())
    delegate = delegates[row_index]
    center = delegate.mapToItem(window.contentItem(), delegate.width() / 2, delegate.height() / 2)
    return QPoint(round(center.x()), round(center.y()))


def test_autofocus_after_add_task(qml_window):
    app, model, window = qml_window

    assert not _is_textfield_focused(window), (
        f"Unexpected initial focus: {_focus_class(window)}"
    )

    model.addTask()
    QTest.qWait(300)

    cls = _focus_class(window)
    print(f"\n[auto-focus] activeFocusItem after addTask+300ms: {cls}")
    assert _is_textfield_focused(window), (
        f"Expected TextField focus after addTask, got: {cls}"
    )


def test_click_other_task_steals_focus(qml_window):
    app, model, window = qml_window

    from plugins.simple_task_list.storage import Task, STATUS_ACTIVE  # noqa: PLC0415
    model._tasks.append(Task(text="Target task", status=STATUS_ACTIVE))
    model._recompute()
    app.processEvents()
    app.processEvents()

    model.addTask()
    QTest.qWait(300)

    cls_before = _focus_class(window)
    print(f"\n[click-steal] focus before click: {cls_before}")
    print(f"  window size: {window.width()} x {window.height()}")

    point = _task_row_center(window, 1)
    print(f"  clicking at ({point.x()}, {point.y()})")
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    QTest.qWait(200)

    cls_after = _focus_class(window)
    print(f"  focus after click: {cls_after}")

    assert not _is_textfield_focused(window), (
        f"After clicking another task, expected focus to leave TextField, "
        f"but it is still on: {cls_after}"
    )

"""Tests for keyboard-focus behaviour: auto-focus on new task, click-away to commit.

Runs against a real QML engine (offscreen) using QTest.mouseClick so that
the actual TapHandler / TextField focus machinery is exercised.
"""
import os
import sys
import pytest

from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtTest import QTest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


# ── shared app singleton ─────────────────────────────────────────────────────

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
    """Start a fresh QML engine; yield (app, task_model, window)."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    app = _get_app()

    src = os.path.join(os.path.dirname(__file__), "..", "yata-src")
    sys.path.insert(0, src)
    import resources_rc  # noqa: F401,PLC0415 — registers qrc:/icons/*.svg etc.
    from icons import IconProvider    # noqa: PLC0415
    from models import TaskListModel   # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    from storage import TaskStore     # noqa: PLC0415

    task_model = TaskListModel(TaskStore())
    app_settings = AppSettings()
    icon_provider = IconProvider()

    engine = QQmlApplicationEngine()
    qml_dir = os.path.join(src, "qml")
    engine.addImportPath(qml_dir)
    engine.rootContext().setContextProperty("taskModel", task_model)
    engine.rootContext().setContextProperty("appSettings", app_settings)
    engine.rootContext().setContextProperty("iconProvider", icon_provider)
    engine.load(os.path.join(qml_dir, "Main.qml"))

    app.processEvents()
    app.processEvents()

    assert engine.rootObjects(), "QML engine failed to load Main.qml"
    window = engine.rootObjects()[0]

    yield app, task_model, window

    del engine
    app.processEvents()
    app.processEvents()


def _focus_class(window):
    """Return the C++ class name of the currently focused item, or 'None'."""
    item = window.activeFocusItem()
    if item is None:
        return "None"
    return item.metaObject().className()


def _is_textfield_focused(window):
    """True when a TextField/TextInput currently holds active focus."""
    cls = _focus_class(window)
    return "TextField" in cls or "TextInput" in cls


def _find_by_class_prefix(item, prefix, results=None):
    """Recursively collect QQuickItems whose C++ class name starts with prefix."""
    if results is None:
        results = []
    if item.metaObject().className().startswith(prefix):
        results.append(item)
    for child in item.childItems():
        _find_by_class_prefix(child, prefix, results)
    return results


def _task_row_center(window, row_index):
    """Map the row_index-th TaskDelegate's center to window coordinates.

    Reads the live layout instead of a hardcoded pixel offset, since the
    toolbar/sub-toolbar stack above the list (and thus where the list
    starts) has changed shape more than once (e.g. the 0.9.35 OrderBar).
    """
    delegates = _find_by_class_prefix(window.contentItem(), "TaskDelegate")
    delegates.sort(key=lambda item: item.mapToItem(window.contentItem(), 0, 0).y())
    delegate = delegates[row_index]
    center = delegate.mapToItem(window.contentItem(), delegate.width() / 2, delegate.height() / 2)
    return QPoint(round(center.x()), round(center.y()))


# ── tests ────────────────────────────────────────────────────────────────────

def test_autofocus_after_add_task(qml_window):
    """Clicking Add should give the new task's TextField active focus within ~200 ms."""
    app, model, window = qml_window

    # Sanity: focus should NOT be on a TextField before we do anything
    assert not _is_textfield_focused(window), (
        f"Unexpected initial focus: {_focus_class(window)}"
    )

    model.addTask()
    QTest.qWait(300)  # 100 ms timer + generous buffer

    cls = _focus_class(window)
    print(f"\n[auto-focus] activeFocusItem after addTask+300ms: {cls}")
    assert _is_textfield_focused(window), (
        f"Expected TextField focus after addTask, got: {cls}"
    )


def test_click_other_task_steals_focus(qml_window):
    """Clicking a non-editing task row should move focus away from the editor."""
    app, model, window = qml_window

    # Seed one existing task so the list has two rows after addTask()
    from storage import Task, STATUS_ACTIVE  # noqa: PLC0415
    model._tasks.append(Task(text="Target task", status=STATUS_ACTIVE))
    model._recompute()
    app.processEvents()
    app.processEvents()

    # Add a blank task — it lands at index 0 and auto-focuses
    model.addTask()
    QTest.qWait(300)

    cls_before = _focus_class(window)
    print(f"\n[click-steal] focus before click: {cls_before}")
    print(f"  window size: {window.width()} x {window.height()}")

    # Click the second task row (index 1, "Target task") — its position is
    # read from the live layout rather than a hardcoded pixel offset, since
    # what's stacked above the list (toolbar/sub-toolbars) has changed shape
    # more than once.
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

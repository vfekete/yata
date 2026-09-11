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
        _app.setOrganizationName("yata-order-controls-test")
        _app.setApplicationName("yata-order-controls-test")
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
    engine.addImportPath(os.path.join(src, "qml"))

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, create_content(DEFAULT_WINDOW_ID, None, raw_settings), app_settings,
    )
    task_model = window_manager._windows[DEFAULT_WINDOW_ID]["task_model"]

    app.processEvents()
    app.processEvents()

    yield app, window, task_model

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


def _center_point(window, item):
    center = item.mapToItem(window.contentItem(), item.width() / 2, item.height() / 2)
    return QPoint(round(center.x()), round(center.y()))


def _visible_task_ids(task_model):
    role_id = {v: k for k, v in task_model.roleNames().items()}[b"taskId"]
    return [
        task_model.data(task_model.index(i, 0), role_id)
        for i in range(task_model.rowCount())
    ]


def _find_qobjects_by_class_prefix(obj, prefix, results=None):
    if results is None:
        results = []
    if obj.metaObject().className().startswith(prefix):
        results.append(obj)
    for child in obj.children():
        _find_qobjects_by_class_prefix(child, prefix, results)
    return results


def _find_month_button(window):
    matches = [
        t for t in _find_by_class_prefix(window.contentItem(), "QQuickText")
        if t.property("text") == "Month"
    ]
    assert len(matches) == 1, f"expected exactly one Month button, found {len(matches)}"
    return matches[0]


def _find_sort_order_active_button(window):
    candidates = [
        t for t in _find_by_class_prefix(window.contentItem(), "QQuickText")
        if t.property("text") == "Active"
    ]
    matches = [
        t for t in candidates
        if t.parent().property("visible") is True and t.parent().property("active") is False
    ]
    assert len(matches) == 1, f"expected exactly one match, found {len(matches)}"
    return matches[0]


def test_active_sort_button_toggles_instead_of_always_selecting(qml_window):
    app, window, task_model = qml_window
    active_btn = _find_sort_order_active_button(window)
    assert task_model.statusSortMode == ""

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, active_btn))
    app.processEvents()
    assert task_model.statusSortMode == "active"
    assert active_btn.parent().property("active") is True

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, active_btn))
    app.processEvents()
    assert task_model.statusSortMode == ""
    assert active_btn.parent().property("active") is False


def test_toggling_active_sort_off_live_freezes_the_sorted_order(qml_window):
    app, window, task_model = qml_window
    d = task_model.addTask()
    task_model.setText(d, "D")
    task_model.setStatus(d, "cancelled")
    c = task_model.addTask()
    task_model.setText(c, "C")
    b = task_model.addTask()
    task_model.setText(b, "B")
    task_model.setStatus(b, "done")
    a = task_model.addTask()
    task_model.setText(a, "A")
    app.processEvents()
    QTest.qWait(200)
    app.processEvents()

    active_btn = _find_sort_order_active_button(window)
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, active_btn))
    app.processEvents()
    assert task_model.statusSortMode == "active"
    assert _visible_task_ids(task_model) == [a, c, b, d]

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, active_btn))
    app.processEvents()

    assert task_model.statusSortMode == ""
    assert _visible_task_ids(task_model) == [a, c, b, d], (
        "toggling the sort off must not reshuffle the order just shown"
    )


def test_row_down_button_moves_task_live(qml_window):
    app, window, task_model = qml_window
    a = task_model.addTask()
    task_model.setText(a, "A")
    b = task_model.addTask()
    task_model.setText(b, "B")
    app.processEvents()
    QTest.qWait(200)
    app.processEvents()

    assert _visible_task_ids(task_model) == [b, a]

    delegates = _find_by_class_prefix(window.contentItem(), "TaskDelegate")
    row_b = next(d for d in delegates if d.property("taskId") == b)

    QTest.mouseMove(window, _center_point(window, row_b))
    app.processEvents()
    QTest.qWait(100)
    app.processEvents()
    assert row_b.property("hovered") is True

    icons = [
        i for i in _find_by_class_prefix(row_b, "QQuickImage")
        if i.parent().property("canMoveDown") is not None
    ]
    assert len(icons) == 2, f"expected exactly 2 order-control icons, found {len(icons)}"
    down_icon = max(icons, key=lambda i: i.mapToItem(window.contentItem(), 0, 0).y())

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, down_icon))
    app.processEvents()

    assert _visible_task_ids(task_model) == [a, b], "clicking the down icon on B should move it below A"


def test_order_group_blocked_while_month_active(qml_window):
    app, window, task_model = qml_window
    active_text = _find_sort_order_active_button(window)
    active_btn = active_text.parent()
    order_row = active_btn.parent()
    order_group = order_row.parent()

    blockers = [c for c in order_group.childItems() if c.metaObject().className().startswith("QQuickMouseArea")]
    assert len(blockers) == 1, f"expected exactly one blocker MouseArea, found {len(blockers)}"
    order_blocker = blockers[0]

    active_hover = _find_qobjects_by_class_prefix(active_btn, "QQuickHoverHandler")[0]

    assert order_blocker.property("enabled") is False
    QTest.mouseMove(window, _center_point(window, active_btn))
    app.processEvents()
    QTest.qWait(100)
    app.processEvents()
    assert active_hover.property("hovered") is True, "hover should reach the button while Month/Year are inactive"
    QTest.mouseMove(window, QPoint(2, 2))
    app.processEvents()

    month_btn = _find_month_button(window)
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, month_btn))
    app.processEvents()
    QTest.qWait(100)
    app.processEvents()
    assert order_blocker.property("enabled") is True

    QTest.mouseMove(window, _center_point(window, active_btn))
    app.processEvents()
    QTest.qWait(100)
    app.processEvents()
    assert active_hover.property("hovered") is False, (
        "the blocker must claim hover away from the Active button while Month is active"
    )

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, active_btn))
    app.processEvents()
    assert task_model.statusSortMode == ""

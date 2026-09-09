"""Integration tests for r-7.md's task-ordering rework:
- TaskDelegate's per-row "^"/"v" buttons (replacing the old "⋮⋮" drag
  handle) manually move a task and switch ordering back to Manual.
- FilterBar's Active/Done/Cancel sort-order buttons now toggle (tapping the
  already-active one clears back to Manual) instead of always selecting
  their own value, now that there's no separate "Manual" button.

Runs against a real QML engine (offscreen) using QTest.mouseMove/mouseClick,
same construction pattern as test_lock_feature.py/test_task_row_hover_color.py
— so the actual compiled QML bindings/handlers are exercised, not just the
Python-side TaskListModel logic already covered by tests/test_models.py.
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
        _app.setOrganizationName("yata-order-controls-test")
        _app.setApplicationName("yata-order-controls-test")
        QQuickStyle.setStyle("Basic")
    return _app


@pytest.fixture()
def qml_window(tmp_path, monkeypatch):
    """Yields (app, window, task_model) — same real construction path as
    the other QML integration test files (main._make_window)."""
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

    app_settings = AppSettings(QSettings(str(tmp_path / "app.ini"), QSettings.IniFormat))
    icon_provider = IconProvider()
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)

    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(src, "qml"))

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, create_content(DEFAULT_WINDOW_ID, None, app_settings), app_settings,
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
    """Like _find_by_class_prefix, but walks QObject.children() instead of
    QQuickItem.childItems() — needed to reach attached Pointer Handlers
    (HoverHandler/TapHandler/DragHandler aren't QQuickItems, so they never
    show up via childItems(), only as plain QObject children)."""
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
    """The FilterBar has FOUR different "Active"-labelled FilterButtons
    (visibility filter, its Yatas equivalent, sort order, and ITS Yatas
    equivalent — see FilterBar.qml). Only the sort-order one we want is
    both currently visible AND, at this point (nothing has been clicked
    yet), not yet active — showActive (the visibility one) defaults to
    True, statusSortMode (the one we want) defaults to "" i.e. not
    "active". This disambiguates it without depending on icon internals;
    callers must find it before clicking anything, then reuse the same
    item reference afterwards (its own `active` will flip to True)."""
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

    # r-7.md: tapping the already-active button clears back to Manual —
    # there's no separate "Manual" button to do that with any more.
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, active_btn))
    app.processEvents()
    assert task_model.statusSortMode == ""
    assert active_btn.parent().property("active") is False


def test_toggling_active_sort_off_live_freezes_the_sorted_order(qml_window):
    """Regression test for a follow-up report: clicking Active a second
    time to toggle the sort back off (no task ever moved) must freeze the
    order just shown, same fix as moving a task while sorted (see
    tests/test_models.py's toggling-off-directly test) — verified here
    against the real compiled QML click path instead of calling
    setStatusSortMode() directly."""
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
    """Verifies the new TaskDelegate.qml wiring itself (the "v" glyph's
    TapHandler calling taskModel.moveTaskDown(root.taskId) with the right
    row) against a real compiled QML tree. The "a manual move switches
    ordering back to Manual" logic this button also relies on is exercised
    directly and thoroughly at the Python level instead (see
    tests/test_models.py's moveTaskUp/moveTaskDown tests) — chaining that
    through a second real synthetic click here (on the FilterBar's Active
    button) proved flaky under the offscreen QPA platform's event timing,
    independent of this feature's own logic, so this test stays focused on
    the one thing only a live QML tree can confirm: the click reaches the
    right handler and moves the right row."""
    app, window, task_model = qml_window
    a = task_model.addTask()
    task_model.setText(a, "A")
    b = task_model.addTask()
    task_model.setText(b, "B")
    app.processEvents()
    QTest.qWait(200)
    app.processEvents()

    # Insertion order (newest first): B, A.
    assert _visible_task_ids(task_model) == [b, a]

    delegates = _find_by_class_prefix(window.contentItem(), "TaskDelegate")
    row_b = next(d for d in delegates if d.property("taskId") == b)

    QTest.mouseMove(window, _center_point(window, row_b))
    app.processEvents()
    QTest.qWait(100)
    app.processEvents()
    assert row_b.property("hovered") is True

    # The up/down controls are real icons (Image), not text glyphs, and the
    # row has several OTHER icons too (note/done/cancel/delete) — narrow to
    # the two whose parent is orderControls itself (identifiable by its
    # canMoveDown property, unique to it), then pick whichever sits lower
    # on screen (Column stacks them top-to-bottom: up first, down second).
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
    """Regression test for a reported bug: while Month (or Year) is active,
    the ordering sub-toolbar is correctly shaded, but hovering it still
    glowed the Active/Done/Cancel buttons, AND dragging from that area
    moved the whole window — because a plain `enabled: false` on the group
    excludes it from hit-testing entirely (transparent to it) rather than
    making it inert, so events fell through to whatever's behind: this
    bar's own background "drag to move the window" MouseArea. Fixed with
    an enabled/hoverEnabled MouseArea (orderBlocker) stacked ON TOP of the
    group instead, exactly the same idiom already used by the glass lock's
    contentBlocker (Main.qml) to claim hover/press away from what's
    underneath."""
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
    QTest.mouseMove(window, QPoint(2, 2))  # away, so the next move is a real transition
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

    # The click must not reach the button either (same claim mechanism) —
    # statusSortMode stays untouched.
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, active_btn))
    app.processEvents()
    assert task_model.statusSortMode == ""

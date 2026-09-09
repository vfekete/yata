"""Integration tests for r-8.md "The glass lock": the 3-state lock icon,
content blur/blocking, and the auto-locked hover/drag/editing exceptions.

Runs against a real QML engine (offscreen) using QTest.mouseClick/mouseMove
so the actual HoverHandler/MouseArea-blocking machinery in Main.qml is
exercised, not just the Python-side AppSettings persistence (already covered
by tests/test_settings.py).
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
        _app.setOrganizationName("yata-lock-test")
        _app.setApplicationName("yata-lock-test")
        QQuickStyle.setStyle("Basic")
    return _app


@pytest.fixture()
def qml_window(tmp_path, monkeypatch):
    """Yields (app, window, app_settings, task_model) — same real
    construction path as test_qml_integration.py/test_focus_behavior.py's
    own fixtures (main._make_window), not a hand-rolled equivalent."""
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
    qml_dir = os.path.join(src, "qml")
    engine.addImportPath(qml_dir)

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, create_content(DEFAULT_WINDOW_ID, None, app_settings), app_settings,
    )
    task_model = window_manager._windows[DEFAULT_WINDOW_ID]["task_model"]

    app.processEvents()
    app.processEvents()

    yield app, window, app_settings, task_model

    del engine
    app.processEvents()
    app.processEvents()


def _find_by_class_prefix(item, prefix, results=None):
    """Same technique as test_focus_behavior.py: recursively collect
    QQuickItems whose C++ class name starts with prefix."""
    if results is None:
        results = []
    if item.metaObject().className().startswith(prefix):
        results.append(item)
    for child in item.childItems():
        _find_by_class_prefix(child, prefix, results)
    return results


def _find_lock_icon(window):
    """The lock icon is the only Image straddling the top border (y ~ 0,
    per r-8.md's "same height as the window title") — every other Image in
    this app (search lupe, note icons, ...) sits well inside the toolbar/list
    below it, so a small y threshold reliably picks it out without needing
    an objectName added just for tests (matching this test suite's existing
    "read the live layout" convention, e.g. test_focus_behavior's
    _task_row_center)."""
    images = _find_by_class_prefix(window.contentItem(), "QQuickImage")
    top_row = [
        img for img in images
        if img.mapToItem(window.contentItem(), 0, 0).y() < 20
    ]
    assert top_row, "lock icon Image not found near the top border"
    top_row.sort(key=lambda img: -img.mapToItem(window.contentItem(), 0, 0).x())
    return top_row[0]


def _center_point(window, item):
    center = item.mapToItem(window.contentItem(), item.width() / 2, item.height() / 2)
    return QPoint(round(center.x()), round(center.y()))


def _find_toolbutton(window, text):
    # Style-templated Controls types (unlike plain QtQuick items such as
    # Image) get a runtime class name like "ToolButton_QMLTYPE_NN", not the
    # C++ "QQuickToolButton" — confirmed by walking the live tree.
    for button in _find_by_class_prefix(window.contentItem(), "ToolButton"):
        if button.property("text") == text:
            return button
    raise AssertionError(f"ToolButton {text!r} not found")


# ── tests ────────────────────────────────────────────────────────────────────

def test_default_lock_state_is_unlocked_and_content_not_blocked(qml_window):
    app, window, app_settings, task_model = qml_window
    assert app_settings.lockState == "unlocked"
    assert window.property("contentLocked") is False


def test_clicking_lock_icon_cycles_unlocked_auto_locked_locked(qml_window):
    app, window, app_settings, task_model = qml_window
    point = _center_point(window, _find_lock_icon(window))

    assert app_settings.lockState == "unlocked"
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert app_settings.lockState == "auto-locked"
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert app_settings.lockState == "locked"
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert app_settings.lockState == "unlocked"


def test_lock_icon_stays_clickable_while_locked(qml_window):
    """The lock icon itself must never be blocked, or a locked window could
    never be unlocked again."""
    app, window, app_settings, task_model = qml_window
    app_settings.lockState = "locked"
    assert window.property("contentLocked") is True

    point = _center_point(window, _find_lock_icon(window))
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert app_settings.lockState == "unlocked"


def test_locked_state_blocks_toolbar_add_button(qml_window):
    app, window, app_settings, task_model = qml_window
    point = _center_point(window, _find_toolbutton(window, "Add"))

    app_settings.lockState = "locked"
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert task_model.rowCount() == 0, "Add click should have been blocked while locked"

    app_settings.lockState = "unlocked"
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert task_model.rowCount() == 1, "Add click should work once unlocked"


def test_right_click_theme_menu_blocked_while_locked(qml_window):
    """r-8.md: locked blocks 'the menu items ... too', i.e. the right-click
    background context menu, not just the toolbar's own THEME button."""
    app, window, app_settings, task_model = qml_window
    app_settings.lockState = "locked"

    # A point inside the window but outside every real control (well below
    # the toolbar/list, in the plain background) — anywhere on the window
    # background triggers the context menu when unlocked.
    point = QPoint(round(window.width() / 2), round(window.height() - 5))
    QTest.mouseClick(window, Qt.RightButton, Qt.NoModifier, point)
    app.processEvents()

    popups = [
        item for item in _find_by_class_prefix(window.contentItem(), "QQuickPopupItem")
        if item.property("visible")
    ]
    assert not popups, "theme context menu must not open while locked"


def test_auto_locked_blocked_before_hover_and_unlocked_once_hovered(qml_window):
    """Note: a real click gesture (QTest.mouseClick, and a real mouse) always
    moves the pointer onto the target first — so a click ON the Add button
    itself necessarily counts as "hovering the content" by the time it
    lands, per r-8.md's own "allowing full control as long as the mouse is
    inside the window". The genuinely-still-locked case is instead checked
    by clicking a *different* point than the eventual hover target."""
    app, window, app_settings, task_model = qml_window
    add_btn = _find_toolbutton(window, "Add")
    point = _center_point(window, add_btn)
    # Inside the window but above contentColumn's own top margin gutter —
    # i.e. genuinely outside the content area contentOverlay covers, so
    # clicking there can't itself trigger the hover-based auto-unlock.
    outside_point = QPoint(5, 2)

    app_settings.lockState = "auto-locked"
    assert window.property("contentLocked") is True

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, outside_point)
    assert task_model.rowCount() == 0, "click outside content shouldn't add a task or unlock"
    assert window.property("contentLocked") is True

    QTest.mouseMove(window, point)
    app.processEvents()
    assert window.property("contentLocked") is False, "hovering content should auto-unlock"

    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, point)
    assert task_model.rowCount() == 1, "Add click should work once hovered"


def test_auto_locked_relocks_after_mouse_leaves_content(qml_window):
    app, window, app_settings, task_model = qml_window
    add_btn = _find_toolbutton(window, "Add")
    hover_point = _center_point(window, add_btn)
    # Inside the window but above contentColumn's own top margin gutter —
    # i.e. genuinely outside the content area contentOverlay covers.
    outside_point = QPoint(5, 2)

    app_settings.lockState = "auto-locked"
    # Move away from wherever a previous test in this same process may have
    # last left the (offscreen-platform-shared) synthetic cursor position —
    # a move to the exact same absolute point as last time can be coalesced
    # away without ever reaching this fresh window's own HoverHandler.
    QTest.mouseMove(window, outside_point)
    QTest.mouseMove(window, hover_point)
    app.processEvents()
    assert window.property("contentLocked") is False

    QTest.mouseMove(window, outside_point)
    app.processEvents()
    assert window.property("contentLocked") is True


def test_auto_locked_unlocked_by_cross_window_drag_hover(qml_window):
    """dragHoverActive (broadcast by WindowManager while another window's
    task drag is over this one) should auto-unlock exactly like a real
    hover, per r-8.md's "or drops tasks from different windows"."""
    app, window, app_settings, task_model = qml_window
    app_settings.lockState = "auto-locked"
    assert window.property("contentLocked") is True

    window.setProperty("dragHoverActive", True)
    assert window.property("contentLocked") is False

    window.setProperty("dragHoverActive", False)
    assert window.property("contentLocked") is True


def test_auto_locked_stays_unlocked_while_editing_task_description(qml_window):
    """r-8.md's exception: editing a task's description keeps auto-locked
    unlocked regardless of mouse position, only re-checking once editing
    finishes. Uses the real new-task autofocus path (same timing as
    test_focus_behavior.py's test_autofocus_after_add_task), not a mocked
    focus flag, so the real Window.activeFocusItem-based check in Main.qml
    is exercised end-to-end."""
    app, window, app_settings, task_model = qml_window
    app_settings.lockState = "auto-locked"
    assert window.property("contentLocked") is True

    task_model.addTask()
    QTest.qWait(300)  # 100ms autofocus timer + generous buffer

    assert window.property("contentLocked") is False, (
        "editing a task description should override the lock even with no hover"
    )

    # Click a different toolbar button to move focus off the text field —
    # this click itself also hovers/lands on that button (see the "before
    # hover" test above for why that alone would auto-unlock), so the mouse
    # is explicitly moved off content afterward to isolate the actual
    # question: does the editing exception correctly stop applying once
    # editing genuinely ends, independent of hovering.
    reload_btn = _find_toolbutton(window, "Reload")
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, reload_btn))
    QTest.mouseMove(window, QPoint(5, 2))
    app.processEvents()

    assert window.property("contentLocked") is True, (
        "should re-lock once editing finishes and the mouse isn't hovering"
    )


def test_task_row_hover_still_works_while_unlocked(qml_window):
    """Regression test: contentHoverHandler (added for auto-locked's
    hover-to-unlock detection) was originally a sibling Item stacked on top
    of contentColumn — which, confirmed via a minimal reproduction, made it
    exclusively claim hover and blocked every hover-driven control
    underneath (TaskDelegate row highlighting, and the same mechanism in
    LinksView/YatasView) from ever seeing it, even while fully unlocked.
    Fixed by nesting contentHoverHandler as a child of contentColumn itself
    instead of a sibling overlay above it."""
    app, window, app_settings, task_model = qml_window
    assert app_settings.lockState == "unlocked"

    task_model.addTask()
    QTest.qWait(300)
    app.processEvents()

    delegates = _find_by_class_prefix(window.contentItem(), "TaskDelegate")
    assert delegates, "no TaskDelegate row found to hover"
    row = delegates[0]

    assert row.property("hovered") is False
    QTest.mouseMove(window, _center_point(window, row))
    app.processEvents()

    assert row.property("hovered") is True, (
        "task row should still react to hover while unlocked"
    )


def test_task_row_hover_suppressed_while_locked(qml_window):
    """Regression test, immediate follow-up to the fix above: user reported
    that once row hover started working again while unlocked, it *also*
    started working while fully "locked" — where it shouldn't, since r-8.md
    says a locked window "does not react on mouse movement or mouse clicks"
    at all (clicking was already correctly blocked; only the hover reaction
    was wrong). Fixed by making contentBlocker also hoverEnabled while
    plain-locked, so it claims hover away from the rows underneath exactly
    like it already claims clicks."""
    app, window, app_settings, task_model = qml_window

    task_model.addTask()
    QTest.qWait(300)
    app.processEvents()

    delegates = _find_by_class_prefix(window.contentItem(), "TaskDelegate")
    assert delegates, "no TaskDelegate row found to hover"
    row = delegates[0]
    point = _center_point(window, row)
    away = QPoint(5, 2)

    app_settings.lockState = "locked"
    QTest.mouseMove(window, away)
    app.processEvents()
    QTest.mouseMove(window, point)
    app.processEvents()

    assert row.property("hovered") is False, (
        "task row must not react to hover while locked"
    )


def test_auto_locked_hover_unlock_not_deadlocked_by_hover_blocking(qml_window):
    """Regression test: contentBlocker claiming hover to fix the test above
    must NOT apply to auto-locked — auto-locked's own enabled-ness (while
    not yet hovering) depends on contentHoverHandler detecting the mouse's
    arrival, and contentHoverHandler sits underneath contentBlocker in the
    z-stack. If contentBlocker claimed hover there too, it would
    permanently steal the hover contentHoverHandler needs to ever notice
    anything and disable itself — confirmed live: auto-locked got stuck
    locked forever, never unlocking on hover again, before this was scoped
    to plain "locked" only."""
    app, window, app_settings, task_model = qml_window
    add_btn = _find_toolbutton(window, "Add")
    point = _center_point(window, add_btn)

    app_settings.lockState = "auto-locked"
    assert window.property("contentLocked") is True

    QTest.mouseMove(window, point)
    app.processEvents()

    assert window.property("contentLocked") is False, (
        "auto-locked must still unlock on hover, not deadlock"
    )

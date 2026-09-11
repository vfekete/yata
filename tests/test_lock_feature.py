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
    task_model = window_manager._windows[DEFAULT_WINDOW_ID]["task_model"]

    app.processEvents()
    app.processEvents()

    yield app, window, app_settings, task_model

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


def _find_lock_icon(window):
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
    for button in _find_by_class_prefix(window.contentItem(), "ToolButton"):
        if button.property("text") == text:
            return button
    raise AssertionError(f"ToolButton {text!r} not found")


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
    app, window, app_settings, task_model = qml_window
    app_settings.lockState = "locked"

    point = QPoint(round(window.width() / 2), round(window.height() - 5))
    QTest.mouseClick(window, Qt.RightButton, Qt.NoModifier, point)
    app.processEvents()

    popups = [
        item for item in _find_by_class_prefix(window.contentItem(), "QQuickPopupItem")
        if item.property("visible")
    ]
    assert not popups, "theme context menu must not open while locked"


def test_auto_locked_blocked_before_hover_and_unlocked_once_hovered(qml_window):
    app, window, app_settings, task_model = qml_window
    add_btn = _find_toolbutton(window, "Add")
    point = _center_point(window, add_btn)
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
    outside_point = QPoint(5, 2)

    app_settings.lockState = "auto-locked"
    QTest.mouseMove(window, outside_point)
    QTest.mouseMove(window, hover_point)
    app.processEvents()
    assert window.property("contentLocked") is False

    QTest.mouseMove(window, outside_point)
    app.processEvents()
    assert window.property("contentLocked") is True


def test_auto_locked_unlocked_by_cross_window_drag_hover(qml_window):
    app, window, app_settings, task_model = qml_window
    app_settings.lockState = "auto-locked"
    assert window.property("contentLocked") is True

    window.setProperty("dragHoverActive", True)
    assert window.property("contentLocked") is False

    window.setProperty("dragHoverActive", False)
    assert window.property("contentLocked") is True


def test_auto_locked_stays_unlocked_while_editing_task_description(qml_window):
    app, window, app_settings, task_model = qml_window
    app_settings.lockState = "auto-locked"
    assert window.property("contentLocked") is True

    task_model.addTask()
    QTest.qWait(300)

    assert window.property("contentLocked") is False, (
        "editing a task description should override the lock even with no hover"
    )

    reload_btn = _find_toolbutton(window, "Reload")
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, reload_btn))
    QTest.mouseMove(window, QPoint(5, 2))
    app.processEvents()

    assert window.property("contentLocked") is True, (
        "should re-lock once editing finishes and the mouse isn't hovering"
    )


def test_task_row_hover_still_works_while_unlocked(qml_window):
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

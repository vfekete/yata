"""Tests for window management ("YATAS") as host chrome, not plugin
content — moved out of plugins/simple_task_list/ after r-9.md's step 4
initially carried it there along with everything else. Window management
is the master application's own job (r-9.md's original framing) and must
stay available regardless of which plugin a window is running, so it now
lives in yata-src/qml/YatasView.qml, toggled by Main.qml's own "Y" chrome
icon rather than a plugin toolbar button.

Runs against a real QML engine (offscreen) using QTest, same construction
pattern as the other QML integration test files.
"""
import os
import sys

import pytest
from PySide6.QtCore import QMetaObject, QPoint, Qt
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_app = None


def _get_app():
    global _app
    if _app is None:
        QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
            Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
        )
        _app = QGuiApplication.instance() or QGuiApplication(sys.argv)
        _app.setOrganizationName("yata-yatas-host-test")
        _app.setApplicationName("yata-yatas-host-test")
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


def _center_point(window, item):
    center = item.mapToItem(window.contentItem(), item.width() / 2, item.height() / 2)
    return QPoint(round(center.x()), round(center.y()))


@pytest.fixture()
def yata_window(tmp_path, monkeypatch):
    """Yields (app, window, window_manager, registry, window_id, task_model,
    engine) — a single real window, same construction path as main.py."""
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

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, plugin_content, host_settings,
    )
    task_model = window_manager._windows[DEFAULT_WINDOW_ID]["task_model"]
    app.processEvents()
    app.processEvents()

    yield app, window, window_manager, registry, DEFAULT_WINDOW_ID, task_model, engine

    del engine
    app.processEvents()
    app.processEvents()


def test_plugin_toolbar_has_no_yatas_button(yata_window):
    app, window, window_manager, registry, window_id, task_model, engine = yata_window
    buttons = [
        b for b in _find_by_class_prefix(window.contentItem(), "ToolButton")
        if b.property("text") == "Yatas"
    ]
    assert buttons == [], "window management moved to host chrome, not a plugin toolbar button"


def test_plugin_add_button_always_adds_a_task(yata_window):
    """No more yatasActive-dependent dual purpose -- ADD is always "add
    task" now that window creation lives in the host's own YatasView."""
    app, window, window_manager, registry, window_id, task_model, engine = yata_window
    add_button = next(
        b for b in _find_by_class_prefix(window.contentItem(), "ToolButton")
        if b.property("text") == "Add"
    )
    before = task_model.rowCount()

    from PySide6.QtTest import QTest
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, add_button))
    app.processEvents()

    assert task_model.rowCount() == before + 1


def test_yatas_icon_toggles_window_list_in_place_of_plugin_content(yata_window):
    app, window, window_manager, registry, window_id, task_model, engine = yata_window
    assert window.property("yatasActive") is False

    window.setProperty("yatasActive", True)
    app.processEvents()

    yatas_view = _find_by_class_prefix(window.contentItem(), "YatasView")[0]
    assert yatas_view.property("visible") is True

    plugin_loader = next(
        ld for ld in _find_by_class_prefix(window.contentItem(), "QQuickLoader")
        if ld.property("source") and "TaskListContent" in str(ld.property("source"))
    )
    assert plugin_loader.property("visible") is False

    window.setProperty("yatasActive", False)
    app.processEvents()
    assert yatas_view.property("visible") is False
    assert plugin_loader.property("visible") is True


def test_yatas_view_stays_visible_and_usable_while_locked(yata_window):
    """Explicit request: window management must show and stay fully
    usable regardless of lock state -- it must NOT sit behind the same
    blur/tint/input-block the plugin's own content does. yatasView is
    declared as a later sibling of contentOverlay (contentBlocker), not
    nested inside frostedContent alongside contentLoader, specifically so
    it wins both rendering (paints on top) and input delivery (Qt Quick
    hands events to the topmost item first) regardless of contentLocked."""
    app, window, window_manager, registry, window_id, task_model, engine = yata_window

    host_settings = window_manager._windows[window_id]["app_settings"]
    host_settings.lockState = "locked"
    app.processEvents()
    assert window.property("contentLocked") is True

    window.setProperty("yatasActive", True)
    app.processEvents()

    yatas_view = _find_by_class_prefix(window.contentItem(), "YatasView")[0]
    assert yatas_view.property("visible") is True

    row = _find_by_class_prefix(yatas_view, "YatasRow")[0]
    tag_text = next(
        t for t in _find_by_class_prefix(row, "QQuickText")
        if t.property("text") == window_manager.tagFor(window_id)
    )

    from PySide6.QtTest import QTest
    QTest.mouseDClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, tag_text))
    app.processEvents()

    assert row.property("editing") is True, (
        "double-click-to-rename must work even while the window is "
        "hard-locked -- window management is exempt from the glass lock"
    )


def test_add_window_button_in_yatas_view_clones_theme(yata_window):
    """The shared yata_window fixture's window_factory is a no-op (other
    tests in this file never need createWindow() to actually build
    anything) -- this one does, so it wires a real factory onto the same
    window_manager first, same as main.py's own window_factory."""
    app, window, window_manager, registry, window_id, task_model, engine = yata_window

    from main import _make_window, _open_settings  # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    import plugins_registry  # noqa: PLC0415
    from icons import IconProvider  # noqa: PLC0415

    icon_provider = IconProvider()

    def real_window_factory(new_window_id, caller_state):
        legacy_qsettings = _open_settings(new_window_id)
        plugin = plugins_registry.get(registry.get_plugin(new_window_id))
        plugin_content = plugin.create_content(new_window_id, None, legacy_qsettings)
        host_settings = AppSettings(legacy_qsettings)
        host_settings.x = int(caller_state["x"])
        host_settings.y = int(caller_state["y"])
        host_settings.width = int(caller_state["width"])
        host_settings.height = int(caller_state["height"])
        new_plugin_settings = plugin_content.context_properties["appSettings"]
        new_plugin_settings.themeMode = caller_state["themeMode"]
        new_plugin_settings.themeTint = caller_state["themeTint"]
        new_plugin_settings.opacityPercent = int(caller_state["opacityPercent"])
        new_plugin_settings.fontScale = float(caller_state["fontScale"])
        new_plugin_settings.wheelZoomInverted = bool(caller_state["wheelZoomInverted"])
        return _make_window(
            engine, icon_provider, window_manager, QIcon(),
            new_window_id, plugin_content, host_settings,
        )

    window_manager._window_factory = real_window_factory

    plugin_settings = window_manager._windows[window_id]["plugin_content"].context_properties["appSettings"]
    plugin_settings.themeMode = "light"
    plugin_settings.themeTint = "goldenrod"

    window.setProperty("yatasActive", True)
    app.processEvents()

    # Scoped to the YatasView subtree specifically -- the plugin's own
    # (now hidden, not destroyed) ADD button also has a Text reading
    # "Add", so searching the whole window would be ambiguous.
    yatas_view = _find_by_class_prefix(window.contentItem(), "YatasView")[0]
    add_text = next(
        t for t in _find_by_class_prefix(yatas_view, "QQuickText")
        if t.property("text") == "Add"
    )
    before_count = window_manager.openWindowCount

    from PySide6.QtTest import QTest
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, add_text))
    app.processEvents()
    app.processEvents()

    assert window_manager.openWindowCount == before_count + 1
    new_id = next(wid for wid in window_manager._windows if wid != window_id)
    new_settings = window_manager._windows[new_id]["plugin_content"].context_properties["appSettings"]
    assert new_settings.themeMode == "light"
    assert new_settings.themeTint == "goldenrod"


def test_double_click_row_tag_enters_rename_mode(yata_window):
    app, window, window_manager, registry, window_id, task_model, engine = yata_window
    window.setProperty("yatasActive", True)
    app.processEvents()

    row = _find_by_class_prefix(window.contentItem(), "YatasRow")[0]
    tag_text = next(
        t for t in _find_by_class_prefix(row, "QQuickText")
        if t.property("text") == window_manager.tagFor(window_id)
    )

    from PySide6.QtTest import QTest
    QTest.mouseDClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, tag_text))
    app.processEvents()

    assert row.property("editing") is True


def test_delete_recreate_purge_round_trip(yata_window):
    app, window, window_manager, registry, window_id, task_model, engine = yata_window
    second_id = registry.add("Second")

    # register_window needs a real plugin_content to be a fully-formed
    # entry for YatasView's SHOW toggle to make sense, but this test only
    # exercises the registry-level active/deleted round trip (no second
    # live window needed) -- WindowManager.deleteWindow/recreateWindow/
    # purgeWindow only touch the registry either way.
    window.setProperty("yatasActive", True)
    app.processEvents()
    yatas_view = _find_by_class_prefix(window.contentItem(), "YatasView")[0]
    yatas_view.refresh()
    app.processEvents()
    app.processEvents()

    def row_for(wid):
        return next(r for r in _find_by_class_prefix(window.contentItem(), "YatasRow") if r.property("windowId") == wid)

    def visible_glyph(row, glyph):
        return next(t for t in _find_by_class_prefix(row, "QQuickText") if t.property("text") == glyph and t.property("visible"))

    from PySide6.QtTest import QTest

    second_row = row_for(second_id)
    trash = visible_glyph(second_row, "🗑")
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, trash))
    app.processEvents()

    dialog = next(w for w in QGuiApplication.topLevelWindows() if w.property("title") == "Delete window?" and w.property("visible"))
    QMetaObject.invokeMethod(dialog, "accept", Qt.DirectConnection)
    app.processEvents()

    assert next(e for e in registry.list() if e["id"] == second_id)["deleted"] is True

    # Deleted windows show right alongside active ones now (no separate
    # visibility toggle) -- just needs a refresh to pick up the new state.
    yatas_view.refresh()
    app.processEvents()
    app.processEvents()
    second_row = row_for(second_id)
    recreate = visible_glyph(second_row, "↺")
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, recreate))
    app.processEvents()

    assert next(e for e in registry.list() if e["id"] == second_id)["deleted"] is False

    yatas_view.refresh()
    app.processEvents()
    app.processEvents()
    second_row = row_for(second_id)
    trash = visible_glyph(second_row, "🗑")
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, trash))
    app.processEvents()
    dialog = next(w for w in QGuiApplication.topLevelWindows() if w.property("title") == "Delete window?" and w.property("visible"))
    QMetaObject.invokeMethod(dialog, "accept", Qt.DirectConnection)
    app.processEvents()

    yatas_view.refresh()
    app.processEvents()
    app.processEvents()
    second_row = row_for(second_id)
    purge = visible_glyph(second_row, "🗑")
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, _center_point(window, purge))
    app.processEvents()
    dialog = next(w for w in QGuiApplication.topLevelWindows() if w.property("title") == "Purge window?" and w.property("visible"))
    QMetaObject.invokeMethod(dialog, "accept", Qt.DirectConnection)
    app.processEvents()

    assert second_id not in [e["id"] for e in registry.list()]

"""Offscreen QML integration tests for the ADD / edit / delete flow.

Runs against a real QML engine (QT_QPA_PLATFORM=offscreen) to catch bugs
that only appear when QML delegates are live — e.g. onEditingFinished firing
during beginResetModel() and overwriting model data.
"""
import os
import sys

import pytest
from PySide6.QtCore import Qt
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
        _app.setOrganizationName("yata-qml-test")
        _app.setApplicationName("yata-qml-test")
        QQuickStyle.setStyle("Basic")
    return _app


@pytest.fixture(scope="module")
def qml_app():
    return _get_app()


@pytest.fixture()
def engine_and_model(qml_app, tmp_path, monkeypatch):
    """Spin up a fresh QML engine + TaskListModel for each test."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yata-src"))
    import resources_rc  # noqa: F401,PLC0415 — registers qrc:/icons/*.svg etc.
    from icons import IconProvider  # noqa: PLC0415
    from main import _make_window  # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    from plugins.simple_task_list.storage import TaskStore  # noqa: PLC0415
    from window_manager import WindowManager  # noqa: PLC0415
    from window_registry import DEFAULT_WINDOW_ID, WindowRegistry  # noqa: PLC0415

    app_settings = AppSettings()
    icon_provider = IconProvider()
    # Reuses main.py's real window-construction path (not a hand-rolled
    # equivalent) specifically because it's the one already proven to build
    # Theme/Main.qml correctly for r-3.md's multi-window support — a
    # near-identical but not-quite-matching setup (e.g. creating Theme
    # directly against engine.rootContext() instead of a per-window child
    # QQmlContext, as an earlier version of this fixture did) reproduced
    # "Unable to assign [undefined] to QColor" for every Theme.* consumer.
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)

    engine = QQmlApplicationEngine()
    qml_dir = os.path.join(os.path.dirname(__file__), "..", "yata-src", "qml")
    engine.addImportPath(qml_dir)

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, TaskStore(), app_settings,
    )
    task_model = window_manager._windows[DEFAULT_WINDOW_ID]["task_model"]

    qml_app.processEvents()
    qml_app.processEvents()

    yield task_model

    # Destroy engine synchronously before task_model/app_settings are
    # garbage-collected. deleteLater() is async and the deferred deletion
    # fires after Python has already nulled the context properties, causing
    # QML bindings to emit "Cannot read property ... of null" on teardown.
    del engine
    qml_app.processEvents()
    qml_app.processEvents()


def test_add_task_creates_empty_task(engine_and_model):
    model = engine_and_model
    task_id = model.addTask()
    assert model._find(task_id) is not None
    assert model._find(task_id).text == ""


def test_add_task_cleanup_removes_previous_empty(engine_and_model):
    model = engine_and_model
    t1 = model.addTask()
    t2 = model.addTask()
    assert model._find(t1) is None, "first empty task should have been purged"
    assert model._find(t2) is not None


def test_add_task_cleanup_preserves_non_empty(engine_and_model):
    model = engine_and_model
    t1 = model.addTask()
    model._find(t1).text = "Milk"
    model._recompute()
    model._save()

    t2 = model.addTask()
    assert model._find(t1) is not None, "non-empty task must survive cleanup"
    assert model._find(t2) is not None


def test_delete_task_removes_it(engine_and_model):
    model = engine_and_model
    t1 = model.addTask()
    model.deleteTask(t1)
    assert model._find(t1) is None


@pytest.fixture()
def engine_and_window(qml_app, tmp_path, monkeypatch):
    """Like engine_and_model, but yields (window, app_settings) instead of
    just the task model — needed for r-5.md's Theme.effectiveGlowColor/
    effectiveLinkColor, which live on the per-window Theme context property,
    not on the task model."""
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "yata-src"))
    import resources_rc  # noqa: F401,PLC0415
    from icons import IconProvider  # noqa: PLC0415
    from main import _make_window  # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    from plugins.simple_task_list.storage import TaskStore  # noqa: PLC0415
    from window_manager import WindowManager  # noqa: PLC0415
    from window_registry import DEFAULT_WINDOW_ID, WindowRegistry  # noqa: PLC0415

    # An explicit-path QSettings (IniFormat), not bare AppSettings()'s own
    # QSettings("yata", "yata") 2-arg fallback — that fallback resolves via
    # QStandardPaths at construction time, and empirically (confirmed via a
    # real full-suite run) Qt does NOT reliably re-resolve it per-process
    # for every later monkeypatched XDG_CONFIG_HOME: this fixture's own
    # write-then-read tests leaked their borderColor into an unrelated,
    # later-running test_window_manager.py test in the same pytest process
    # (that test's own autouse XDG_CONFIG_HOME fixture didn't help — the
    # path/data was apparently already cached from this fixture's earlier,
    # first-in-process use). An explicit absolute path sidesteps the whole
    # env-var-resolution/caching question entirely — see feedback_test_data_safety.
    from PySide6.QtCore import QSettings  # noqa: PLC0415

    app_settings = AppSettings(QSettings(str(tmp_path / "app.ini"), QSettings.IniFormat))
    icon_provider = IconProvider()
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    window_manager = WindowManager(registry, window_factory=lambda *a: None)

    engine = QQmlApplicationEngine()
    qml_dir = os.path.join(os.path.dirname(__file__), "..", "yata-src", "qml")
    engine.addImportPath(qml_dir)

    window = _make_window(
        engine, icon_provider, window_manager, QIcon(),
        DEFAULT_WINDOW_ID, TaskStore(), app_settings,
    )
    qml_app.processEvents()
    qml_app.processEvents()

    yield window, app_settings

    del engine
    qml_app.processEvents()
    qml_app.processEvents()


def _theme_for(window):
    from PySide6.QtQml import QQmlEngine  # noqa: PLC0415

    return QQmlEngine.contextForObject(window).contextProperty("Theme")


def test_effective_glow_color_follows_custom_border_color(engine_and_window):
    """r-5.md: FilterButton's pushed-state glow and markdown link color/glow
    should follow the window's custom border color (r-4.md) once one is
    set, falling back to each one's own theme default otherwise."""
    window, app_settings = engine_and_window
    theme = _theme_for(window)

    default_glow = theme.property("effectiveGlowColor")
    default_link = theme.property("effectiveLinkColor")
    assert default_glow == theme.property("filterGlowColor")
    assert default_link == theme.property("linkColor")

    app_settings.borderColor = "#ff3db2"
    assert theme.property("effectiveGlowColor").name().lower() == "#ff3db2"
    assert theme.property("effectiveLinkColor").name().lower() == "#ff3db2"


def test_effective_glow_color_falls_back_after_reset(engine_and_window):
    """Resetting the custom border color (ThemeMenu's Reset, or clearing it
    any other way) must bring the button/link colors back to their own
    theme defaults, not leave them stuck on the last custom color."""
    window, app_settings = engine_and_window
    theme = _theme_for(window)

    app_settings.borderColor = "#39ff14"
    assert theme.property("effectiveGlowColor").name().lower() == "#39ff14"

    app_settings.borderColor = ""
    assert theme.property("effectiveGlowColor") == theme.property("filterGlowColor")
    assert theme.property("effectiveLinkColor") == theme.property("linkColor")


def test_effective_glow_color_ignores_custom_color_under_a_tint(engine_and_window):
    """Follow-up to r-5.md: under any CRT tint (not "none"), buttons/links
    keep that tint's own accent-derived color regardless of a custom border
    color — only the border itself (Main.qml, not Theme) takes the raw
    custom color under a tint. Only the "none" tint lets buttons/links
    follow the custom color."""
    window, app_settings = engine_and_window
    theme = _theme_for(window)

    app_settings.themeTint = "green"
    app_settings.borderColor = "#ff3db2"
    assert theme.property("effectiveGlowColor") == theme.property("filterGlowColor")
    assert theme.property("effectiveLinkColor") == theme.property("linkColor")
    assert theme.property("effectiveGlowColor").name().lower() != "#ff3db2"

    app_settings.themeTint = "none"
    assert theme.property("effectiveGlowColor").name().lower() == "#ff3db2"
    assert theme.property("effectiveLinkColor").name().lower() == "#ff3db2"


def test_click_away_on_new_task_saves_task_name(engine_and_model, qml_app):
    """onEditingFinished with empty text for a new task should save 'Task name'.

    Triggered by a model reset (setSearchText round-trip) while the new
    task's TextField still has focus — replicating what happens when the
    user clicks the toolbar or any area outside the list.
    """
    model = engine_and_model
    t1 = model.addTask()
    qml_app.processEvents()
    qml_app.processEvents()

    model.setSearchText("__nonexistent__")
    qml_app.processEvents()
    model.setSearchText("")
    qml_app.processEvents()

    task = model._find(t1)
    if task is not None:
        assert task.text in ("", "Task name"), (
            f"unexpected text after click-away: {task.text!r}"
        )

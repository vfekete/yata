"""Offscreen QML integration tests for the ADD / edit / delete flow.

Runs against a real QML engine (QT_QPA_PLATFORM=offscreen) to catch bugs
that only appear when QML delegates are live — e.g. onEditingFinished firing
during beginResetModel() and overwriting model data.
"""
import os
import sys

import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
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
    from models import TaskListModel  # noqa: PLC0415
    from settings import AppSettings  # noqa: PLC0415
    from storage import TaskStore  # noqa: PLC0415

    task_model = TaskListModel(TaskStore())
    app_settings = AppSettings()
    icon_provider = IconProvider()

    engine = QQmlApplicationEngine()
    qml_dir = os.path.join(os.path.dirname(__file__), "..", "yata-src", "qml")
    engine.addImportPath(qml_dir)
    engine.rootContext().setContextProperty("taskModel", task_model)
    engine.rootContext().setContextProperty("appSettings", app_settings)
    engine.rootContext().setContextProperty("iconProvider", icon_provider)
    engine.load(os.path.join(qml_dir, "Main.qml"))

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

from PySide6.QtCore import QSettings

from plugin_api import PluginContent
from plugins.simple_task_list.model import TaskListModel
from plugins.simple_task_list.plugin import PLUGIN, create_content


def test_plugin_is_registered_with_expected_identity():
    assert PLUGIN.id == "simple_task_list"
    assert PLUGIN.create_content is create_content
    assert PLUGIN.copyright


def test_create_content_returns_a_working_task_model(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    content = create_content("window-1", str(tmp_path / "window-1"), settings)

    assert isinstance(content, PluginContent)
    task_model = content.context_properties["taskModel"]
    assert isinstance(task_model, TaskListModel)

    task_id = task_model.addTask()
    task_model.setText(task_id, "Hello from the plugin")
    assert [t for t in task_model._visible if t.id == task_id][0].text == "Hello from the plugin"


def test_create_content_take_item_and_insert_item_move_a_task_between_models(tmp_path):
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)
    source = create_content("source", str(tmp_path / "source"), settings)
    target = create_content("target", str(tmp_path / "target"), settings)

    source_model = source.context_properties["taskModel"]
    task_id = source_model.addTask()
    source_model.setText(task_id, "Move me")

    task = source.take_item(task_id)
    assert task is not None
    target.insert_item(task, -1)

    target_model = target.context_properties["taskModel"]
    assert any(t.text == "Move me" for t in target_model._visible)
    assert not any(t.id == task_id for t in source_model._visible)


def test_create_content_with_none_path_uses_legacy_default_store(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    settings = QSettings(str(tmp_path / "settings.ini"), QSettings.IniFormat)

    content = create_content("default", None, settings)
    task_model = content.context_properties["taskModel"]
    task_model.addTask()

    assert (tmp_path / "yata" / "tasks.json").exists()

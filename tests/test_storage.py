import json
import os

from plugins.simple_task_list.storage import MODEL_VERSION, PLUGIN_ID, Task, TaskStore
from plugin_api import API_VERSION


def test_load_missing_file_returns_empty_list(tmp_path):
    store = TaskStore(path=str(tmp_path / "tasks.json"))
    assert store.load() == []


def test_save_and_load_round_trip(tmp_path):
    store = TaskStore(path=str(tmp_path / "tasks.json"))
    tasks = [Task(text="First", note="why it's done"), Task(text="Second", status="done")]

    store.save(tasks)
    loaded = store.load()

    assert [t.text for t in loaded] == ["First", "Second"]
    assert [t.status for t in loaded] == ["active", "done"]
    assert [t.id for t in loaded] == [t.id for t in tasks]
    assert [t.note for t in loaded] == ["why it's done", ""]


def test_task_note_defaults_empty():
    assert Task().note == ""


def test_save_creates_parent_directory(tmp_path):
    path = str(tmp_path / "nested" / "tasks.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    store = TaskStore(path=path)

    store.save([Task(text="A task")])

    assert os.path.exists(path)


def test_task_ids_are_unique():
    a, b = Task(), Task()
    assert a.id != b.id


def test_loads_pre_r9_bare_array_format(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps([{"text": "Legacy task", "status": "active"}]))

    loaded = TaskStore(path=str(path)).load()

    assert [t.text for t in loaded] == ["Legacy task"]


def test_save_writes_versioned_envelope(tmp_path):
    path = tmp_path / "tasks.json"
    TaskStore(path=str(path)).save([Task(text="A task")])

    doc = json.loads(path.read_text())

    assert doc["plugin_id"] == PLUGIN_ID
    assert len(doc["blocks"]) == 1
    assert doc["blocks"][0]["model_version"] == MODEL_VERSION
    assert doc["blocks"][0]["api_version"] == API_VERSION
    assert doc["blocks"][0]["data"][0]["text"] == "A task"


def test_save_after_loading_legacy_format_upgrades_it(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps([{"text": "Legacy task", "status": "active"}]))
    store = TaskStore(path=str(path))

    store.save(store.load())

    doc = json.loads(path.read_text())
    assert "blocks" in doc
    assert doc["blocks"][0]["data"][0]["text"] == "Legacy task"


def test_load_skips_block_with_incompatible_newer_model_version(tmp_path):
    path = tmp_path / "tasks.json"
    path.write_text(json.dumps({
        "plugin_id": PLUGIN_ID,
        "blocks": [{"model_version": "999.0", "api_version": API_VERSION, "data": [{"text": "Future"}]}],
    }))

    assert TaskStore(path=str(path)).load() == []

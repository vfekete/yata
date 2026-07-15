import os

from storage import Task, TaskStore


def test_load_missing_file_returns_empty_list(tmp_path):
    store = TaskStore(path=str(tmp_path / "tasks.json"))
    assert store.load() == []


def test_save_and_load_round_trip(tmp_path):
    store = TaskStore(path=str(tmp_path / "tasks.json"))
    tasks = [Task(text="First"), Task(text="Second", status="done")]

    store.save(tasks)
    loaded = store.load()

    assert [t.text for t in loaded] == ["First", "Second"]
    assert [t.status for t in loaded] == ["active", "done"]
    assert [t.id for t in loaded] == [t.id for t in tasks]


def test_save_creates_parent_directory(tmp_path):
    path = str(tmp_path / "nested" / "tasks.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    store = TaskStore(path=path)

    store.save([Task(text="A task")])

    assert os.path.exists(path)


def test_task_ids_are_unique():
    a, b = Task(), Task()
    assert a.id != b.id

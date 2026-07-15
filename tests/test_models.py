from datetime import datetime, timedelta

import pytest

from models import TaskListModel, day_label
from storage import TaskStore


@pytest.fixture
def model(tmp_path):
    return TaskListModel(TaskStore(path=str(tmp_path / "tasks.json")))


def role(model, row, name):
    index = model.index(row, 0)
    role_id = {v: k for k, v in model.roleNames().items()}[name.encode()]
    return model.data(index, role_id)


def test_add_task_inserts_at_top(model):
    first = model.addTask()
    model.setText(first, "First")
    second = model.addTask()
    model.setText(second, "Second")

    assert model.rowCount() == 2
    assert role(model, 0, "taskId") == second
    assert role(model, 1, "taskId") == first


def test_new_task_starts_active_and_empty(model):
    model.addTask()
    assert role(model, 0, "text") == ""
    assert role(model, 0, "status") == "active"


def test_set_status(model):
    task_id = model.addTask()

    model.setStatus(task_id, "done")
    assert role(model, 0, "status") == "done"

    model.setStatus(task_id, "active")
    assert role(model, 0, "status") == "active"


def test_delete_task(model):
    task_id = model.addTask()
    model.deleteTask(task_id)
    assert model.rowCount() == 0


def test_search_filters_by_text(model):
    a = model.addTask()
    model.setText(a, "Buy milk")
    b = model.addTask()
    model.setText(b, "Walk the dog")

    model.setSearchText("milk")

    assert model.rowCount() == 1
    assert role(model, 0, "taskId") == a


def test_search_is_case_insensitive(model):
    a = model.addTask()
    model.setText(a, "Buy Milk")

    model.setSearchText("milk")

    assert model.rowCount() == 1


def test_status_sort_moves_matching_status_first_and_is_stable(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    c = model.addTask()
    model.setText(c, "C")
    model.setStatus(b, "done")

    model.setStatusSortMode("done")

    assert [role(model, i, "taskId") for i in range(3)] == [b, c, a]


def test_move_task_reorders_manual_list(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    c = model.addTask()
    model.setText(c, "C")
    # Insertion order (newest first): C, B, A.

    model.moveTask(0, 2)

    # C is dropped onto A's slot, landing immediately before it.
    assert [role(model, i, "taskId") for i in range(3)] == [b, c, a]


def test_move_task_ignored_when_not_reorderable(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    model.setSearchText("a")

    model.moveTask(0, 1)

    model.setSearchText("")
    assert [role(model, i, "taskId") for i in range(model.rowCount())] == [b, a]


def test_can_reorder_false_while_filtering_or_sorting_but_not_while_grouping(model):
    assert model.canReorder is True

    model.setSearchText("x")
    assert model.canReorder is False
    model.setSearchText("")
    assert model.canReorder is True

    model.setStatusSortMode("done")
    assert model.canReorder is False
    model.setStatusSortMode("")
    assert model.canReorder is True

    # Grouping by day alone does not block manual reordering: dragging can
    # still move a task, including between day groups (see moveTask tests).
    model.setGroupByDay(True)
    assert model.canReorder is True
    model.setGroupByDay(False)


def test_group_by_day_groups_todays_task_under_its_date_label(model):
    model.addTask()

    model.setGroupByDay(True)

    assert model.rowCount() == 1
    assert role(model, 0, "dayLabel") == day_label(datetime.now().isoformat())


def test_group_by_day_respects_active_status_sort_within_a_day(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    c = model.addTask()
    model.setText(c, "C")
    model.setStatus(b, "done")

    model.setGroupByDay(True)
    model.setStatusSortMode("done")

    # All three tasks land in the same (today's) group; within it, "done"
    # sorts first instead of the day grouping ignoring status sort.
    assert [role(model, i, "taskId") for i in range(3)] == [b, c, a]


def test_move_task_across_day_groups_reassigns_its_day_keeping_time_of_day(model):
    a = model.addTask()
    model.setText(a, "Today task")
    b = model.addTask()
    model.setText(b, "Yesterday task")

    yesterday = datetime.now() - timedelta(days=1)
    yesterday_label = day_label(yesterday.isoformat())
    task_b = model._find(b)
    task_b.created_at = yesterday.replace(hour=9, minute=30, second=0, microsecond=0).isoformat()
    model._recompute()
    original_time = datetime.fromisoformat(model._find(a).created_at).time()

    model.setGroupByDay(True)
    assert [role(model, i, "taskId") for i in range(2)] == [a, b]

    model.moveTask(0, 1)  # drag "today"'s task onto "yesterday"'s slot

    moved = model._find(a)
    moved_dt = datetime.fromisoformat(moved.created_at)
    assert moved_dt.date() == yesterday.date()
    assert moved_dt.time() == original_time
    assert [t.id for t in model._tasks] == [a, b]
    assert role(model, 0, "dayLabel") == yesterday_label
    assert role(model, 1, "dayLabel") == yesterday_label


def test_day_label_always_uses_a_full_date():
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    assert day_label(today.isoformat()) == today.strftime("%A, %d %B %Y")
    assert day_label(yesterday.isoformat()) == yesterday.strftime("%A, %d %B %Y")


def test_persists_across_reload(tmp_path):
    path = str(tmp_path / "tasks.json")
    model1 = TaskListModel(TaskStore(path=path))
    task_id = model1.addTask()
    model1.setText(task_id, "Persisted")

    model2 = TaskListModel(TaskStore(path=path))

    assert model2.rowCount() == 1
    assert role(model2, 0, "text") == "Persisted"

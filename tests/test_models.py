from datetime import datetime, timedelta

import pytest
from PySide6.QtCore import QSettings

from models import TaskListModel, day_label
from storage import TaskStore


def _make_model(tmp_path, name="tasks.json", settings_name="settings.ini"):
    s = QSettings(str(tmp_path / settings_name), QSettings.IniFormat)
    return TaskListModel(TaskStore(path=str(tmp_path / name)), settings=s)


@pytest.fixture
def model(tmp_path):
    return _make_model(tmp_path)


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


def test_set_note(model):
    task_id = model.addTask()

    model.setNote(task_id, "why it's done")
    assert role(model, 0, "note") == "why it's done"


def test_new_task_starts_with_empty_note(model):
    model.addTask()
    assert role(model, 0, "note") == ""


def test_note_for_returns_set_value(model):
    task_id = model.addTask()
    model.setNote(task_id, "the reason")
    assert model.noteFor(task_id) == "the reason"


def test_note_for_returns_empty_for_unknown_or_unset_task(model):
    task_id = model.addTask()
    assert model.noteFor(task_id) == ""
    assert model.noteFor("no-such-id") == ""


def test_set_note_noop_when_unchanged(model):
    task_id = model.addTask()
    model.setNote(task_id, "reason")
    resets, changes = _signal_counters(model)

    model.setNote(task_id, "reason")

    assert not changes
    assert not resets


# --- dataChanged vs. full reset (Qt Quick best practices: avoid destroying
# delegates for non-structural mutations) --------------------------------

def _signal_counters(model):
    resets, changes = [], []
    model.modelReset.connect(lambda: resets.append(True))
    model.dataChanged.connect(lambda *a: changes.append(True))
    return resets, changes


def test_edit_without_search_or_sort_emits_data_changed_not_reset(model):
    task_id = model.addTask()
    model.setText(task_id, "Initial")
    resets, changes = _signal_counters(model)

    model.setText(task_id, "Edited")

    assert changes
    assert not resets
    assert role(model, 0, "text") == "Edited"


def test_status_change_without_sort_active_emits_data_changed_not_reset(model):
    task_id = model.addTask()
    model.setText(task_id, "Task")
    resets, changes = _signal_counters(model)

    model.setStatus(task_id, "done")

    assert changes
    assert not resets
    assert role(model, 0, "status") == "done"


def test_set_note_emits_data_changed_not_reset(model):
    task_id = model.addTask()
    model.setText(task_id, "Task")
    resets, changes = _signal_counters(model)

    model.setNote(task_id, "why")

    assert changes
    assert not resets
    assert role(model, 0, "note") == "why"


def test_search_narrowing_visibility_still_emits_reset(model):
    a = model.addTask()
    model.setText(a, "Buy milk")
    resets, _ = _signal_counters(model)

    model.setSearchText("nonexistent")

    assert resets


def test_status_sort_reordering_edit_still_emits_reset(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    model.setStatusSortMode("done")
    resets, _ = _signal_counters(model)

    model.setStatus(a, "done")  # now sorts first, reordering the visible list

    assert resets


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

    # C is dropped after A's slot — the drop placeholder renders below the
    # hovered row (see TaskDelegate.qml's showGapBelow), meaning "insert
    # right after this one", not before it.
    assert [role(model, i, "taskId") for i in range(3)] == [b, a, c]


def test_move_task_ignored_when_not_reorderable(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    model.setSearchText("a")

    model.moveTask(0, 1)

    model.setSearchText("")
    assert [role(model, i, "taskId") for i in range(model.rowCount())] == [b, a]


def test_can_reorder_false_only_while_searching(model):
    assert model.canReorder is True

    model.setSearchText("x")
    assert model.canReorder is False
    model.setSearchText("")
    assert model.canReorder is True

    # r-7.md: an active status sort no longer blocks reordering — dragging
    # (or the up/down row controls) while sorted is now allowed and jumps
    # ordering back to Manual instead (see the moveTask/moveTaskUp tests
    # below that assert statusSortMode resets to "").
    model.setStatusSortMode("done")
    assert model.canReorder is True
    model.setStatusSortMode("")

    # Grouping by day alone does not block manual reordering: dragging can
    # still move a task, including between day groups (see moveTask tests).
    model.setGroupByDay(True)
    assert model.canReorder is True
    model.setGroupByDay(False)


def test_move_task_switches_status_sort_back_to_manual(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    c = model.addTask()
    model.setText(c, "C")
    model.setStatus(b, "done")
    model.setStatusSortMode("done")
    assert model.statusSortMode == "done"

    model.moveTask(0, 1)

    assert model.statusSortMode == ""


def test_move_task_up_down_while_sorted_freezes_the_sorted_order_not_stale_manual_order(model):
    """Regression test for a reported bug: with Active-sort selected (so
    actives show first) and all three statuses visible, moving one active
    task down turned ordering back to Manual (correct) but the list jumped
    to show Cancelled/Done first — resurfacing the OLD, unrelated manual
    order from before the sort was ever turned on, rather than keeping the
    order the user was just looking at (actives first) with just the one
    move applied. "Moving a task means the CURRENT [visible] order is now
    manual," not "reshuffle to some other order."""
    d = model.addTask()
    model.setText(d, "D")
    model.setStatus(d, "cancelled")
    c = model.addTask()
    model.setText(c, "C")
    b = model.addTask()
    model.setText(b, "B")
    model.setStatus(b, "done")
    a = model.addTask()
    model.setText(a, "A")
    # Manual/insertion order (each addTask() inserts at the front): A, B, C, D.

    model.setStatusSortMode("active")
    # Actives (A, C) first in their existing relative order, then the rest
    # (B, D) in theirs.
    assert [role(model, i, "taskId") for i in range(4)] == [a, c, b, d]

    model.moveTaskDown(a)  # swap the two actives

    assert model.statusSortMode == ""
    assert [role(model, i, "taskId") for i in range(4)] == [c, a, b, d]


def test_move_task_drag_while_sorted_freezes_the_sorted_order_not_stale_manual_order(model):
    """Same regression as above, via moveTask (drag&drop) instead of the
    up/down buttons — both funnel through the same _reposition helper."""
    d = model.addTask()
    model.setText(d, "D")
    model.setStatus(d, "cancelled")
    c = model.addTask()
    model.setText(c, "C")
    b = model.addTask()
    model.setText(b, "B")
    model.setStatus(b, "done")
    a = model.addTask()
    model.setText(a, "A")
    # Manual/insertion order (each addTask() inserts at the front): A, B, C, D.

    model.setStatusSortMode("active")
    assert [role(model, i, "taskId") for i in range(4)] == [a, c, b, d]

    model.moveTask(0, 1)  # drag A (visible index 0) onto C's slot (index 1)

    assert model.statusSortMode == ""
    assert [role(model, i, "taskId") for i in range(4)] == [c, a, b, d]


def test_toggling_status_sort_off_directly_freezes_the_sorted_order_too(model):
    """Regression test for a follow-up report: the fix above covered
    turning the sort off via a MOVE, but toggling the "Active" sort button
    itself back off (setStatusSortMode("") with no move at all — e.g.
    clicking FilterBar's Active button a second time) had the exact same
    bug, resurfacing the stale pre-sort manual order instead of freezing
    the order just shown. "Visibility [filters] is not order" — turning
    ordering off must not look like a reorder in itself."""
    d = model.addTask()
    model.setText(d, "D")
    model.setStatus(d, "cancelled")
    c = model.addTask()
    model.setText(c, "C")
    b = model.addTask()
    model.setText(b, "B")
    model.setStatus(b, "done")
    a = model.addTask()
    model.setText(a, "A")
    # Manual/insertion order (each addTask() inserts at the front): A, B, C, D.

    model.setStatusSortMode("active")
    assert [role(model, i, "taskId") for i in range(4)] == [a, c, b, d]

    model.setStatusSortMode("")  # toggle back off, no move involved

    assert [role(model, i, "taskId") for i in range(4)] == [a, c, b, d]


def test_move_task_noop_does_not_switch_status_sort(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    model.setStatus(b, "done")
    model.setStatusSortMode("done")

    # from_index == to_index: dragging started but the row was dropped back
    # onto its own slot — spec: ordering must NOT jump to manual for this.
    model.moveTask(0, 0)

    assert model.statusSortMode == "done"


def test_move_task_up_and_down_swap_adjacent_visible_rows(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    c = model.addTask()
    model.setText(c, "C")
    # Insertion order (newest first): C, B, A.
    assert [role(model, i, "taskId") for i in range(3)] == [c, b, a]

    model.moveTaskDown(b)
    assert [role(model, i, "taskId") for i in range(3)] == [c, a, b]

    model.moveTaskUp(b)
    assert [role(model, i, "taskId") for i in range(3)] == [c, b, a]


def test_move_task_up_disabled_at_top_and_down_disabled_at_bottom(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    # Insertion order (newest first): B, A.

    model.moveTaskUp(b)  # already topmost — no-op
    assert [role(model, i, "taskId") for i in range(2)] == [b, a]

    model.moveTaskDown(a)  # already last — no-op
    assert [role(model, i, "taskId") for i in range(2)] == [b, a]


def test_move_task_up_down_switch_status_sort_back_to_manual(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    model.setStatus(b, "done")
    model.setStatusSortMode("done")

    model.moveTaskDown(b)

    assert model.statusSortMode == ""


def test_move_task_up_down_ignored_while_searching(model):
    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    model.setSearchText("a")

    model.moveTaskDown(b)

    model.setSearchText("")
    assert [role(model, i, "taskId") for i in range(2)] == [b, a]


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


def test_move_task_down_across_day_groups_reassigns_its_day_keeping_time_of_day(model):
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

    model.moveTaskDown(a)  # "today"'s task swaps down onto "yesterday"'s slot

    moved = model._find(a)
    moved_dt = datetime.fromisoformat(moved.created_at)
    assert moved_dt.date() == yesterday.date()
    assert moved_dt.time() == original_time
    assert role(model, 0, "dayLabel") == yesterday_label
    assert role(model, 1, "dayLabel") == yesterday_label


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
    # Inserted after b (the hovered slot), not before it — see moveTask's
    # own "insert after target_task" comment.
    assert [t.id for t in model._tasks] == [b, a]
    assert role(model, 0, "dayLabel") == yesterday_label
    assert role(model, 1, "dayLabel") == yesterday_label


def test_day_label_always_uses_a_full_date():
    today = datetime.now()
    yesterday = today - timedelta(days=1)

    assert day_label(today.isoformat()) == today.strftime("%A, %d %B %Y")
    assert day_label(yesterday.isoformat()) == yesterday.strftime("%A, %d %B %Y")


def test_persists_across_reload(tmp_path):
    model1 = _make_model(tmp_path)
    task_id = model1.addTask()
    model1.setText(task_id, "Persisted")

    model2 = _make_model(tmp_path)

    assert model2.rowCount() == 1
    assert role(model2, 0, "text") == "Persisted"


def test_set_status_records_completed_at_for_done_and_cancelled(model):
    task_id = model.addTask()
    model.setText(task_id, "Buy milk")
    assert model._find(task_id).completed_at == ""

    model.setStatus(task_id, "done")
    ts_done = model._find(task_id).completed_at
    assert ts_done != "", "completed_at must be set when status → done"

    model.setStatus(task_id, "active")
    assert model._find(task_id).completed_at == ts_done, "reset to active must not clear timestamp"

    model.setStatus(task_id, "cancelled")
    ts_cancelled = model._find(task_id).completed_at
    assert ts_cancelled != "" and ts_cancelled >= ts_done, "re-finishing updates timestamp"


def test_reload_tasks_picks_up_externally_written_file(tmp_path):
    path = str(tmp_path / "tasks.json")
    model = TaskListModel(TaskStore(path=path))
    model.addTask()
    assert model.rowCount() == 1

    # Simulate an external process replacing tasks.json entirely, bypassing
    # this model's own _tasks/_save().
    TaskStore(path=path).save([])
    assert model.rowCount() == 1  # unchanged until reloadTasks() is called

    model.reloadTasks()

    assert model.rowCount() == 0


# --- visibility filter tests -----------------------------------------------

def test_visibility_defaults_all_true(model):
    assert model.showActive is True
    assert model.showDone is True
    assert model.showCancelled is True


def test_hide_active_removes_active_tasks(model):
    a = model.addTask()
    model.setText(a, "Active task")
    d = model.addTask()
    model.setText(d, "Done task")
    model.setStatus(d, "done")

    model.setShowActive(False)

    ids = [role(model, i, "taskId") for i in range(model.rowCount())]
    assert a not in ids
    assert d in ids


def test_hide_done_removes_done_tasks(model):
    a = model.addTask()
    model.setText(a, "Active task")
    d = model.addTask()
    model.setText(d, "Done task")
    model.setStatus(d, "done")

    model.setShowDone(False)

    ids = [role(model, i, "taskId") for i in range(model.rowCount())]
    assert d not in ids
    assert a in ids


def test_hide_cancelled_removes_cancelled_tasks(model):
    a = model.addTask()
    model.setText(a, "Active task")
    c = model.addTask()
    model.setText(c, "Cancelled task")
    model.setStatus(c, "cancelled")

    model.setShowCancelled(False)

    ids = [role(model, i, "taskId") for i in range(model.rowCount())]
    assert c not in ids
    assert a in ids


def test_visibility_restoring_shows_tasks_again(model):
    a = model.addTask()
    model.setText(a, "Active task")
    model.setShowActive(False)
    assert model.rowCount() == 0

    model.setShowActive(True)
    assert model.rowCount() == 1


def test_visibility_filters_stack_with_search(model):
    a = model.addTask()
    model.setText(a, "Buy milk")
    d = model.addTask()
    model.setText(d, "Buy bread")
    model.setStatus(d, "done")

    model.setSearchText("buy")
    model.setShowDone(False)

    assert model.rowCount() == 1
    assert role(model, 0, "taskId") == a


# --- filter persistence tests -----------------------------------------------

def test_filter_state_persists_across_restart(tmp_path):
    m1 = _make_model(tmp_path)
    m1.setGroupByDay(True)
    m1.setStatusSortMode("done")
    m1.setShowActive(False)
    m1.setShowDone(False)
    # showCancelled stays True: at least one of the three must remain visible
    # (see test_visibility_last_filter_cannot_be_hidden), so it can't also be
    # set False here.

    m2 = _make_model(tmp_path)
    assert m2.groupByDay is True
    assert m2.statusSortMode == "done"
    assert m2.showActive is False
    assert m2.showDone is False
    assert m2.showCancelled is True


def test_filter_false_persists_correctly(tmp_path):
    # Explicitly tests that stored "false" values aren't read back as True.
    m1 = _make_model(tmp_path)
    m1.setShowActive(False)
    m1.setShowDone(False)

    m2 = _make_model(tmp_path)
    assert m2.showActive is False
    assert m2.showDone is False
    assert m2.showCancelled is True


def test_visibility_last_filter_cannot_be_hidden(model):
    # Active/Done/Cancelled must always leave at least one visible, so the
    # third setShowX(False) — turning off the last one still on — is a no-op.
    model.setShowActive(False)
    model.setShowDone(False)
    model.setShowCancelled(False)

    assert model.showCancelled is True

    # Same guard regardless of which one is hidden last.
    model.setShowActive(True)
    model.setShowDone(True)
    model.setShowCancelled(False)
    model.setShowActive(False)
    model.setShowDone(False)
    assert model.showDone is True


def test_filter_defaults_with_empty_settings(tmp_path):
    m = _make_model(tmp_path)
    assert m.groupByDay is False
    assert m.statusSortMode == ""
    assert m.showActive is True
    assert m.showDone is True
    assert m.showCancelled is True


# --- calendar view tests (MonthView/YearView) -------------------------------

def test_month_counts_aggregates_by_day_and_status(model):
    a = model.addTask()
    model.setText(a, "Active on the 5th")
    model._find(a).created_at = datetime(2026, 3, 5, 9, 0).isoformat()

    d = model.addTask()
    model.setText(d, "Done on the 5th")
    model._find(d).created_at = datetime(2026, 3, 5, 10, 0).isoformat()
    model.setStatus(d, "done")

    c = model.addTask()
    model.setText(c, "Cancelled on the 12th")
    model._find(c).created_at = datetime(2026, 3, 12, 8, 0).isoformat()
    model.setStatus(c, "cancelled")

    other_month = model.addTask()
    model.setText(other_month, "Different month entirely")
    model._find(other_month).created_at = datetime(2026, 4, 1, 8, 0).isoformat()

    counts = model.monthCounts(2026, 3)
    by_day = {c["day"]: c for c in counts}

    assert by_day[5] == {"day": 5, "active": 1, "done": 1, "cancelled": 0}
    assert by_day[12] == {"day": 12, "active": 0, "done": 0, "cancelled": 1}
    assert 1 not in by_day  # April's task must not leak into March's counts


def test_month_counts_empty_month_returns_empty_list(model):
    assert model.monthCounts(1999, 1) == []


def test_year_counts_aggregates_by_month_and_status(model):
    jan = model.addTask()
    model.setText(jan, "January task")
    model._find(jan).created_at = datetime(2026, 1, 15, 9, 0).isoformat()

    dec = model.addTask()
    model.setText(dec, "December task")
    model._find(dec).created_at = datetime(2026, 12, 20, 9, 0).isoformat()
    model.setStatus(dec, "done")

    other_year = model.addTask()
    model.setText(other_year, "Different year entirely")
    model._find(other_year).created_at = datetime(2025, 1, 15, 9, 0).isoformat()

    counts = model.yearCounts(2026)
    by_month = {c["month"]: c for c in counts}

    assert by_month[1] == {"month": 1, "active": 1, "done": 0, "cancelled": 0}
    assert by_month[12] == {"month": 12, "active": 0, "done": 1, "cancelled": 0}
    assert len(by_month) == 2  # 2025's task must not leak into 2026's counts


def test_index_for_date_finds_first_matching_row(model):
    older = model.addTask()
    model.setText(older, "Older day")
    model._find(older).created_at = datetime(2026, 5, 1, 9, 0).isoformat()

    newer = model.addTask()
    model.setText(newer, "Newer day")
    model._find(newer).created_at = datetime(2026, 5, 10, 9, 0).isoformat()

    model.setGroupByDay(True)  # newest day sorts first

    assert model.indexForDate(2026, 5, 10) == 0
    assert model.indexForDate(2026, 5, 1) == 1


def test_index_for_date_returns_minus_one_when_no_match(model):
    t = model.addTask()
    model.setText(t, "Some task")
    model._find(t).created_at = datetime(2026, 5, 1, 9, 0).isoformat()

    assert model.indexForDate(2026, 5, 2) == -1


# --- links view tests --------------------------------------------------------

def test_linked_tasks_finds_markdown_links_regardless_of_status(model):
    a = model.addTask()
    model.setText(a, "Check [the site](https://example.com/a)")

    d = model.addTask()
    model.setText(d, "Read [the doc](https://example.com/b)")
    model.setStatus(d, "done")

    c = model.addTask()
    model.setText(c, "Visit [somewhere](https://example.com/c)")
    model.setStatus(c, "cancelled")

    no_link = model.addTask()
    model.setText(no_link, "No links here at all")

    linked = model.linkedTasks()
    assert len(linked) == 3
    by_id = {entry["taskId"]: entry for entry in linked}
    assert by_id[a]["links"] == [{"label": "the site", "url": "https://example.com/a"}]
    assert by_id[a]["status"] == "active"
    assert by_id[d]["links"] == [{"label": "the doc", "url": "https://example.com/b"}]
    assert by_id[d]["status"] == "done"
    assert by_id[c]["links"] == [{"label": "somewhere", "url": "https://example.com/c"}]
    assert by_id[c]["status"] == "cancelled"


def test_linked_tasks_ignores_visibility_and_search_filters(model):
    t = model.addTask()
    model.setText(t, "Has a [link](https://example.com)")
    model.setStatus(t, "cancelled")

    # Hide cancelled tasks from the normal list, and search for something
    # that doesn't match — linkedTasks() must still return it.
    model.setShowCancelled(False)
    model.setSearchText("nonexistent")

    linked = model.linkedTasks()
    assert len(linked) == 1
    assert linked[0]["taskId"] == t


def test_linked_tasks_collects_multiple_urls_per_task_in_order(model):
    t = model.addTask()
    model.setText(t, "See [first](https://example.com/1) and [second](https://example.com/2)"
                      " and [third](https://example.com/3)")

    linked = model.linkedTasks()
    assert linked[0]["links"] == [
        {"label": "first", "url": "https://example.com/1"},
        {"label": "second", "url": "https://example.com/2"},
        {"label": "third", "url": "https://example.com/3"},
    ]


def test_linked_tasks_empty_when_no_task_has_a_link(model):
    t = model.addTask()
    model.setText(t, "Just plain text, no links")
    assert model.linkedTasks() == []


def test_linked_tasks_falls_back_to_url_when_label_is_empty(model):
    t = model.addTask()
    model.setText(t, "Bare link: [](https://example.com/bare)")

    linked = model.linkedTasks()
    assert linked[0]["links"] == [{"label": "https://example.com/bare", "url": "https://example.com/bare"}]


def test_index_for_task_finds_row_in_current_visible_list(model):
    a = model.addTask()
    model.setText(a, "First")
    b = model.addTask()
    model.setText(b, "Second")

    assert model.indexForTask(b) == 0  # newest first (manual order, top-insert)
    assert model.indexForTask(a) == 1


def test_index_for_task_returns_minus_one_when_not_visible(model):
    t = model.addTask()
    model.setText(t, "Some task")
    model.setStatus(t, "cancelled")
    model.setShowCancelled(False)

    assert model.indexForTask(t) == -1


def test_take_task_removes_and_returns_it(model):
    t = model.addTask()
    model.setText(t, "Take me")
    model.setStatus(t, "done")

    task = model.take_task(t)

    assert task is not None
    assert task.id == t
    assert task.text == "Take me"
    assert task.status == "done"
    assert model.rowCount() == 0
    assert model._find(t) is None


def test_take_task_returns_none_for_unknown_id(model):
    assert model.take_task("does-not-exist") is None


def test_take_task_persists_removal(tmp_path):
    model = _make_model(tmp_path)
    t = model.addTask()
    model.setText(t, "Persisted")

    model.take_task(t)

    reloaded = _make_model(tmp_path)
    assert reloaded.rowCount() == 0


def test_insert_task_adds_it_preserving_fields(model):
    from storage import Task

    task = Task(text="Imported", status="done", created_at="2026-01-02T03:04:05", id="fixed-id")

    model.insert_task(task)

    assert role(model, 0, "taskId") == "fixed-id"
    assert role(model, 0, "text") == "Imported"
    assert role(model, 0, "status") == "done"


def test_insert_task_reassigns_id_on_collision(model):
    from storage import Task

    existing = model.addTask()
    model.setText(existing, "Existing")
    colliding = Task(text="Imported", id=existing)

    model.insert_task(colliding)

    assert colliding.id != existing
    assert model.rowCount() == 2


def test_take_and_insert_moves_a_task_between_two_models(tmp_path):
    source = _make_model(tmp_path, name="source.json", settings_name="source.ini")
    dest = _make_model(tmp_path, name="dest.json", settings_name="dest.ini")
    t = source.addTask()
    source.setText(t, "Move me")

    task = source.take_task(t)
    dest.insert_task(task)

    assert source.rowCount() == 0
    assert dest.rowCount() == 1
    assert role(dest, 0, "text") == "Move me"


def test_insert_task_at_target_index_lands_right_after_that_row(model):
    from storage import Task

    a = model.addTask()
    model.setText(a, "A")
    b = model.addTask()
    model.setText(b, "B")
    # Visible order (newest first): B, A.

    incoming = Task(text="Dropped", status="active", id="dropped-id")
    model.insert_task(incoming, target_index=1)  # hovering row 1 (A)

    # Dropped right after A (the hovered row), matching moveTask()'s
    # identical "insert after, not at" semantics for the same placeholder.
    assert [role(model, i, "taskId") for i in range(3)] == [b, a, "dropped-id"]


def test_insert_task_with_out_of_range_index_falls_back_to_top(model):
    from storage import Task

    a = model.addTask()
    model.setText(a, "A")

    incoming = Task(text="Dropped", status="active", id="dropped-id")
    model.insert_task(incoming, target_index=-1)

    assert role(model, 0, "taskId") == "dropped-id"

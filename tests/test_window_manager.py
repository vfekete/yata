import os

import pytest
from PySide6.QtCore import QRect

from window_manager import WindowManager
from window_registry import DEFAULT_PLUGIN_ID, DEFAULT_TAG, DEFAULT_WINDOW_ID, WindowRegistry


@pytest.fixture(autouse=True)
def isolated_xdg(tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))


class FakeWindow:
    """Stands in for a QQuickWindow: geometry getters + a closable() flag."""

    def __init__(self, x, y, width, height):
        self._x, self._y, self._w, self._h = x, y, width, height
        self.closed = False
        self._visible_changed_handlers = []

    def x(self):
        return self._x

    def y(self):
        return self._y

    def width(self):
        return self._w

    def height(self):
        return self._h

    def geometry(self):
        return QRect(self._x, self._y, self._w, self._h)

    def close(self):
        self.closed = True
        for handler in self._visible_changed_handlers:
            handler(False)

    class _Signal:
        def __init__(self, owner):
            self._owner = owner

        def connect(self, fn):
            self._owner._visible_changed_handlers.append(fn)

    @property
    def visibleChanged(self):
        return FakeWindow._Signal(self)


def make_manager(tmp_path):
    registry = WindowRegistry(path=str(tmp_path / "windows.json"))
    created = []
    restored = []

    def factory(window_id, caller_state):
        window = FakeWindow(caller_state["x"], caller_state["y"], caller_state["width"], caller_state["height"])
        created.append((window_id, caller_state))
        manager.register_window(window_id, window)
        return window

    def restore_factory(window_id):
        window = FakeWindow(0, 0, 400, 600)
        restored.append(window_id)
        manager.register_window(window_id, window)
        return window

    manager = WindowManager(registry, factory, restore_factory)
    manager._created_log = created  # test-only introspection hook
    manager._restored_log = restored  # test-only introspection hook
    return manager


def test_list_windows_starts_with_default(tmp_path):
    manager = make_manager(tmp_path)
    windows = manager.listWindows()
    assert windows == [
        {
            "id": DEFAULT_WINDOW_ID, "tag": DEFAULT_TAG, "open": False, "deleted": False,
            "plugin": DEFAULT_PLUGIN_ID, "borderColor": "",
        }
    ]


def test_create_window_appends_registry_entry(tmp_path):
    manager = make_manager(tmp_path)
    new_id = manager.createWindow({"x": 100, "y": 100, "width": 400, "height": 600})

    tags = {e["id"] for e in manager.listWindows()}
    assert new_id in tags
    # The registry already seeds one "YATA"-tagged window (DEFAULT_WINDOW_ID)
    # before this call, so the new one gets deduped to "YATA - 2" — see
    # test_create_window_dedupes_tag_against_existing_windows below for the
    # dedup logic itself.
    assert manager.tagFor(new_id) == "YATA - 2"


def test_create_window_dedupes_tag_against_existing_windows(tmp_path):
    manager = make_manager(tmp_path)

    second_id = manager.createWindow({"x": 0, "y": 0, "width": 400, "height": 600})
    third_id = manager.createWindow({"x": 0, "y": 0, "width": 400, "height": 600})

    assert manager.tagFor(DEFAULT_WINDOW_ID) == DEFAULT_TAG
    assert manager.tagFor(second_id) == "YATA - 2"
    assert manager.tagFor(third_id) == "YATA - 3"


def test_create_window_tag_not_deduped_once_no_windows_share_it(tmp_path):
    """Renaming every "YATA"-tagged window away frees the base tag back up
    for the next ADD — dedup checks current tags, not a monotonic counter."""
    manager = make_manager(tmp_path)
    manager.renameWindow(DEFAULT_WINDOW_ID, "Personal")

    new_id = manager.createWindow({"x": 0, "y": 0, "width": 400, "height": 600})

    assert manager.tagFor(new_id) == DEFAULT_TAG


def test_create_window_avoids_overlapping_existing_open_window(tmp_path):
    manager = make_manager(tmp_path)
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(100, 100, 400, 600))

    new_id = manager.createWindow({"x": 100, "y": 100, "width": 400, "height": 600})
    _, caller_state = [e for e in manager._created_log if e[0] == new_id][0]

    # The new window must not exactly overlap the existing one at (100,100).
    assert (caller_state["x"], caller_state["y"]) != (100, 100)


def test_rename_window_updates_tag_and_emits_signal(tmp_path):
    manager = make_manager(tmp_path)
    received = []
    manager.windowsChanged.connect(lambda: received.append(True))

    manager.renameWindow(DEFAULT_WINDOW_ID, "Work")

    assert manager.tagFor(DEFAULT_WINDOW_ID) == "Work"
    assert received


def test_rename_window_ignores_blank_tag(tmp_path):
    manager = make_manager(tmp_path)
    manager.renameWindow(DEFAULT_WINDOW_ID, "   ")
    assert manager.tagFor(DEFAULT_WINDOW_ID) == DEFAULT_TAG


def test_delete_window_closes_it_if_open_and_marks_it_deleted(tmp_path):
    """deleteWindow() is a soft delete (YatasView's DELETED category) — the
    registry entry and its data both survive; only purgeWindow() actually
    discards them (see below)."""
    manager = make_manager(tmp_path)
    window = FakeWindow(0, 0, 400, 600)
    manager.register_window(DEFAULT_WINDOW_ID, window)

    manager.deleteWindow(DEFAULT_WINDOW_ID)

    assert window.closed
    assert not manager.is_open(DEFAULT_WINDOW_ID)
    assert manager.tagFor(DEFAULT_WINDOW_ID) == DEFAULT_TAG  # entry still there
    persisted = next(e for e in manager._registry.list() if e["id"] == DEFAULT_WINDOW_ID)
    assert persisted["deleted"] is True
    assert persisted["open"] is False


def test_delete_window_keeps_data_files(tmp_path):
    manager = make_manager(tmp_path)
    new_id = manager.createWindow({"x": 0, "y": 0, "width": 400, "height": 600})

    from window_registry import tasks_path_for
    tasks_path = tasks_path_for(new_id)
    os.makedirs(os.path.dirname(tasks_path), exist_ok=True)
    with open(tasks_path, "w") as f:
        f.write("[]")

    manager.deleteWindow(new_id)
    assert os.path.exists(tasks_path)


def test_recreate_window_undeletes_and_reopens_it(tmp_path):
    manager = make_manager(tmp_path)
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600))
    manager.deleteWindow(DEFAULT_WINDOW_ID)

    manager.recreateWindow(DEFAULT_WINDOW_ID)

    assert manager.is_open(DEFAULT_WINDOW_ID)
    assert DEFAULT_WINDOW_ID in manager._restored_log
    persisted = next(e for e in manager._registry.list() if e["id"] == DEFAULT_WINDOW_ID)
    assert persisted["deleted"] is False
    assert persisted["open"] is True


def test_purge_window_removes_registry_entry_and_deletes_files(tmp_path):
    manager = make_manager(tmp_path)
    new_id = manager.createWindow({"x": 0, "y": 0, "width": 400, "height": 600})

    from window_registry import tasks_path_for
    tasks_path = tasks_path_for(new_id)
    os.makedirs(os.path.dirname(tasks_path), exist_ok=True)
    with open(tasks_path, "w") as f:
        f.write("[]")

    manager.deleteWindow(new_id)
    manager.purgeWindow(new_id)

    assert manager.tagFor(new_id) == ""
    assert all(e["id"] != new_id for e in manager._registry.list())
    assert not os.path.exists(tasks_path)


def test_purge_window_closes_it_first_if_still_open(tmp_path):
    """Defensive: purging should never normally see an open window (delete
    always closes first), but must not leave a live one dangling if it does."""
    manager = make_manager(tmp_path)
    window = FakeWindow(0, 0, 400, 600)
    manager.register_window(DEFAULT_WINDOW_ID, window)

    manager.purgeWindow(DEFAULT_WINDOW_ID)

    assert window.closed
    assert not manager.is_open(DEFAULT_WINDOW_ID)
    assert all(e["id"] != DEFAULT_WINDOW_ID for e in manager._registry.list())


def test_close_window_hides_it_but_keeps_registry_entry_and_data(tmp_path):
    manager = make_manager(tmp_path)
    window = FakeWindow(0, 0, 400, 600)
    manager.register_window(DEFAULT_WINDOW_ID, window)
    second_id = manager._registry.add("Second")
    manager.register_window(second_id, FakeWindow(0, 0, 400, 600))

    manager.closeWindow(DEFAULT_WINDOW_ID)

    assert window.closed
    assert not manager.is_open(DEFAULT_WINDOW_ID)
    assert manager.tagFor(DEFAULT_WINDOW_ID) == DEFAULT_TAG
    persisted = next(e for e in manager._registry.list() if e["id"] == DEFAULT_WINDOW_ID)
    assert persisted["open"] is False


def test_close_window_emits_windows_changed(tmp_path):
    manager = make_manager(tmp_path)
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600))
    second_id = manager._registry.add("Second")
    manager.register_window(second_id, FakeWindow(0, 0, 400, 600))
    received = []
    manager.windowsChanged.connect(lambda: received.append(True))

    manager.closeWindow(DEFAULT_WINDOW_ID)

    assert received


def test_close_window_is_a_no_op_if_it_is_the_only_open_window(tmp_path):
    """Closing the last open window would leave nothing on screen and no
    YatasView left to reopen anything from — same "at least one must stay"
    guard as TaskListModel's visibility filters."""
    manager = make_manager(tmp_path)
    window = FakeWindow(0, 0, 400, 600)
    manager.register_window(DEFAULT_WINDOW_ID, window)
    received = []
    manager.windowsChanged.connect(lambda: received.append(True))

    manager.closeWindow(DEFAULT_WINDOW_ID)

    assert not window.closed
    assert manager.is_open(DEFAULT_WINDOW_ID)
    assert not received
    persisted = next(e for e in manager._registry.list() if e["id"] == DEFAULT_WINDOW_ID)
    assert persisted["open"] is True


def test_open_window_count_reflects_currently_open_windows(tmp_path):
    """Exposed for Main.qml's close ("X") button to look/behave disabled
    once it's the only window left, mirroring closeWindow()'s own guard —
    see the button's own comment for why this needs to be a real reactive
    Property rather than a plain listWindows().length call in a binding."""
    manager = make_manager(tmp_path)
    assert manager.openWindowCount == 0

    window1 = FakeWindow(0, 0, 400, 600)
    manager.register_window(DEFAULT_WINDOW_ID, window1)
    assert manager.openWindowCount == 1

    manager.createWindow({"x": 0, "y": 0, "width": 400, "height": 600})
    assert manager.openWindowCount == 2

    manager.closeWindow(DEFAULT_WINDOW_ID)
    assert manager.openWindowCount == 1


def test_open_window_count_emits_windows_changed(tmp_path):
    manager = make_manager(tmp_path)
    received = []
    manager.windowsChanged.connect(lambda: received.append(manager.openWindowCount))

    manager.createWindow({"x": 0, "y": 0, "width": 400, "height": 600})

    assert received == [1]


def test_register_window_emits_windows_changed_so_earlier_windows_see_the_final_count(tmp_path):
    """Regression test: at startup, windows are registered one at a time
    (main.py's restore loop calls register_window for each restored window
    in turn). Main.qml's canCloseThisWindow binding reads openWindowCount
    once, at the moment its own window is constructed — so if register_window
    doesn't emit windowsChanged, a window registered early (while the live
    count was still <= 1) never finds out later windows joined, and its
    close button stays stuck looking disabled. Reproduced live: with 4
    windows restored in sequence, the first two kept disabled-looking close
    buttons while the last two did not, even though all 4 were open."""
    manager = make_manager(tmp_path)
    counts_seen_by_first_window = []
    manager.windowsChanged.connect(
        lambda: counts_seen_by_first_window.append(manager.openWindowCount)
    )

    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600))
    for i in range(3):
        manager.register_window(f"extra-{i}", FakeWindow(0, 0, 400, 600))

    # The first window's listener must have been notified of every later
    # registration, ending on the true final count — not stuck at 1.
    assert counts_seen_by_first_window[-1] == 4
    assert manager.openWindowCount == 4


def test_open_window_rebuilds_it_via_restore_factory(tmp_path):
    manager = make_manager(tmp_path)
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600))
    second_id = manager._registry.add("Second")
    manager.register_window(second_id, FakeWindow(0, 0, 400, 600))
    manager.closeWindow(DEFAULT_WINDOW_ID)

    manager.openWindow(DEFAULT_WINDOW_ID)

    assert manager.is_open(DEFAULT_WINDOW_ID)
    assert DEFAULT_WINDOW_ID in manager._restored_log
    persisted = next(e for e in manager._registry.list() if e["id"] == DEFAULT_WINDOW_ID)
    assert persisted["open"] is True


def test_open_window_is_a_no_op_if_already_open(tmp_path):
    manager = make_manager(tmp_path)
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600))

    manager.openWindow(DEFAULT_WINDOW_ID)

    assert manager._restored_log == []


def _make_task_model(tmp_path, name):
    from PySide6.QtCore import QSettings

    from models import TaskListModel
    from storage import TaskStore

    settings = QSettings(str(tmp_path / f"{name}.ini"), QSettings.IniFormat)
    return TaskListModel(TaskStore(path=str(tmp_path / f"{name}.json")), settings=settings)


def test_window_at_finds_the_open_window_containing_the_point(tmp_path):
    manager = make_manager(tmp_path)
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600))
    second_id = manager._registry.add("Second")
    manager.register_window(second_id, FakeWindow(1000, 1000, 400, 600))

    assert manager.windowAt(1100, 1100) == second_id
    assert manager.windowAt(100, 100) == DEFAULT_WINDOW_ID  # including its own window now
    assert manager.windowAt(5000, 5000) == ""  # no window there


def test_window_at_broadcasts_task_drag_hover_changed_with_the_point(tmp_path):
    manager = make_manager(tmp_path)
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600))
    second_id = manager._registry.add("Second")
    manager.register_window(second_id, FakeWindow(1000, 1000, 400, 600))
    received = []
    manager.taskDragHoverChanged.connect(lambda target, x, y: received.append((target, x, y)))

    manager.windowAt(1100, 1100)
    manager.windowAt(5000, 5000)

    assert received == [(second_id, 1100, 1100), ("", 5000, 5000)]


def test_clear_drag_hover_broadcasts_empty_string(tmp_path):
    manager = make_manager(tmp_path)
    received = []
    manager.taskDragHoverChanged.connect(lambda target, x, y: received.append((target, x, y)))

    manager.clearDragHover()

    assert received == [("", 0, 0)]


def test_move_task_to_window_transfers_task_between_open_windows(tmp_path):
    manager = make_manager(tmp_path)
    source_model = _make_task_model(tmp_path, "source")
    dest_model = _make_task_model(tmp_path, "dest")
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600), task_model=source_model)
    second_id = manager._registry.add("Second")
    manager.register_window(second_id, FakeWindow(1000, 0, 400, 600), task_model=dest_model)
    task_id = source_model.addTask()
    source_model.setText(task_id, "Move me")

    moved = manager.moveTaskToWindow(DEFAULT_WINDOW_ID, task_id, second_id)

    assert moved is True
    assert source_model.rowCount() == 0
    assert dest_model.rowCount() == 1


def test_move_task_to_window_fails_gracefully_for_unknown_task_or_window(tmp_path):
    manager = make_manager(tmp_path)
    source_model = _make_task_model(tmp_path, "source")
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600), task_model=source_model)

    assert manager.moveTaskToWindow(DEFAULT_WINDOW_ID, "no-such-task", "no-such-window") is False
    assert manager.moveTaskToWindow(DEFAULT_WINDOW_ID, "no-such-task", DEFAULT_WINDOW_ID) is False


def test_move_task_to_window_is_a_no_op_for_the_same_window(tmp_path):
    manager = make_manager(tmp_path)
    source_model = _make_task_model(tmp_path, "source")
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600), task_model=source_model)
    task_id = source_model.addTask()

    assert manager.moveTaskToWindow(DEFAULT_WINDOW_ID, task_id, DEFAULT_WINDOW_ID) is False
    assert source_model.rowCount() == 1


def test_move_task_to_window_lands_at_the_reported_hover_index(tmp_path):
    """The bug this covers: moveTaskToWindow used to always insert_task() at
    the top of the destination model, ignoring wherever the destination
    window's own placeholder was actually shown — see setDragHoverIndex."""
    manager = make_manager(tmp_path)
    source_model = _make_task_model(tmp_path, "source")
    dest_model = _make_task_model(tmp_path, "dest")
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600), task_model=source_model)
    second_id = manager._registry.add("Second")
    manager.register_window(second_id, FakeWindow(1000, 0, 400, 600), task_model=dest_model)
    task_id = source_model.addTask()
    source_model.setText(task_id, "Move me")
    dest_b = dest_model.addTask()
    dest_model.setText(dest_b, "B")
    dest_a = dest_model.addTask()
    dest_model.setText(dest_a, "A")
    # dest_model's visible order (newest first): A, B.

    manager.setDragHoverIndex(1)  # hovering row 1 (B) in the dest window
    moved = manager.moveTaskToWindow(DEFAULT_WINDOW_ID, task_id, second_id)

    assert moved is True
    assert [t.id for t in dest_model._tasks] == [dest_a, dest_b, task_id]


def test_move_task_to_window_falls_back_to_top_with_no_reported_hover_index(tmp_path):
    manager = make_manager(tmp_path)
    source_model = _make_task_model(tmp_path, "source")
    dest_model = _make_task_model(tmp_path, "dest")
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600), task_model=source_model)
    second_id = manager._registry.add("Second")
    manager.register_window(second_id, FakeWindow(1000, 0, 400, 600), task_model=dest_model)
    task_id = source_model.addTask()
    dest_existing = dest_model.addTask()

    moved = manager.moveTaskToWindow(DEFAULT_WINDOW_ID, task_id, second_id)

    assert moved is True
    assert [t.id for t in dest_model._tasks] == [task_id, dest_existing]


def _make_app_settings(tmp_path, name):
    from PySide6.QtCore import QSettings

    from settings import AppSettings

    settings = QSettings(str(tmp_path / f"{name}.ini"), QSettings.IniFormat)
    return AppSettings(settings=settings)


def test_get_border_color_defaults_to_empty_for_open_window(tmp_path):
    manager = make_manager(tmp_path)
    app_settings = _make_app_settings(tmp_path, "win")
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600), app_settings=app_settings)

    assert manager.getBorderColor(DEFAULT_WINDOW_ID) == ""


def test_set_border_color_updates_live_app_settings_for_open_window(tmp_path):
    """The whole point (r-4.md): an open window's border/tag color updates
    instantly because this writes the exact same AppSettings object
    Main.qml's own bindings already read from — no extra signal plumbing."""
    manager = make_manager(tmp_path)
    app_settings = _make_app_settings(tmp_path, "win")
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600), app_settings=app_settings)

    manager.setBorderColor(DEFAULT_WINDOW_ID, "#ff8800")

    assert app_settings.borderColor == "#ff8800"
    assert manager.getBorderColor(DEFAULT_WINDOW_ID) == "#ff8800"


def test_set_border_color_emits_windows_changed(tmp_path):
    """YatasView's row for a window's tag-name text reads the color via
    windowManager.getBorderColor(), not a live binding to that window's own
    AppSettings (YatasView is a different window) — it only re-reads on
    windowsChanged, so setBorderColor must emit it like every other mutator
    in this class, or a freshly-picked color wouldn't show up there."""
    manager = make_manager(tmp_path)
    app_settings = _make_app_settings(tmp_path, "win")
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600), app_settings=app_settings)

    received = []
    manager.windowsChanged.connect(lambda: received.append(True))
    manager.setBorderColor(DEFAULT_WINDOW_ID, "#ff8800")

    assert received == [True]


def test_border_color_works_for_a_closed_window_via_its_settings_file(tmp_path):
    """YatasView lists closed windows too — picking a color for one must
    still persist, even with no live AppSettings object to write through."""
    manager = make_manager(tmp_path)
    window_id = manager._registry.add("Closed Window")

    assert manager.getBorderColor(window_id) == ""

    manager.setBorderColor(window_id, "#00ff88")

    assert manager.getBorderColor(window_id) == "#00ff88"


def test_border_color_set_while_closed_survives_reopening(tmp_path):
    from PySide6.QtCore import QSettings

    from settings import AppSettings
    from window_registry import settings_path_for

    manager = make_manager(tmp_path)
    window_id = manager._registry.add("Later Opened")
    manager.setBorderColor(window_id, "#123456")

    # Simulate actually opening it afterward: a real AppSettings backed by
    # the exact same on-disk file setBorderColor() wrote to (settings_path_for,
    # not a made-up path — same lookup WindowManager._open_settings_for uses).
    path = settings_path_for(window_id)
    reopened_settings = AppSettings(settings=QSettings(path, QSettings.IniFormat))
    manager.register_window(window_id, FakeWindow(0, 0, 400, 600), app_settings=reopened_settings)

    assert manager.getBorderColor(window_id) == "#123456"
    assert reopened_settings.borderColor == "#123456"


def test_window_at_resets_drag_hover_index_when_no_window_is_under_the_point(tmp_path):
    manager = make_manager(tmp_path)
    manager.register_window(DEFAULT_WINDOW_ID, FakeWindow(0, 0, 400, 600))
    manager.setDragHoverIndex(2)

    manager.windowAt(5000, 5000)

    assert manager._drag_hover_index == -1


def test_clear_drag_hover_resets_drag_hover_index(tmp_path):
    manager = make_manager(tmp_path)
    manager.setDragHoverIndex(2)

    manager.clearDragHover()

    assert manager._drag_hover_index == -1


class FakeGhost:
    """Stands in for the QML DragGhost.qml instance — a plain object with
    dynamic properties, driven via setProperty()/property() the same way the
    real QML-created QObject is."""

    def __init__(self):
        self._props = {}

    def setProperty(self, name, value):
        self._props[name] = value

    def property(self, name):
        return self._props.get(name)


def test_show_drag_ghost_sets_text_status_and_visible(tmp_path):
    manager = make_manager(tmp_path)
    ghost = FakeGhost()
    manager._drag_ghost = ghost

    manager.showDragGhost("Buy milk", "active")

    assert ghost.property("taskText") == "Buy milk"
    assert ghost.property("status") == "active"
    assert ghost.property("visible") is True


def test_move_drag_ghost_offsets_from_the_pointer(tmp_path):
    manager = make_manager(tmp_path)
    ghost = FakeGhost()
    manager._drag_ghost = ghost

    manager.moveDragGhost(100, 200)

    assert ghost.property("x") == 112
    assert ghost.property("y") == 212


def test_hide_drag_ghost_sets_visible_false(tmp_path):
    manager = make_manager(tmp_path)
    ghost = FakeGhost()
    manager._drag_ghost = ghost

    manager.hideDragGhost()

    assert ghost.property("visible") is False


def test_drag_ghost_slots_are_no_ops_without_a_ghost_configured(tmp_path):
    manager = make_manager(tmp_path)
    assert manager._drag_ghost is None
    # Must not raise even with no ghost ever configured — the case every
    # other test in this file (and every real WindowManager built without
    # main.py's drag_ghost=... kwarg) already exercises implicitly.
    manager.showDragGhost("x", "active")
    manager.moveDragGhost(1, 2)
    manager.hideDragGhost()

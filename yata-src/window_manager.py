"""QML-facing manager for multiple YATA windows (r-3.md "Multi instance application").

Owns the persisted WindowRegistry (id + tag) and, for windows currently
running in this process, a live QQuickWindow reference — the latter is what
lets deleteWindow() close an open window directly (no IPC needed, since
every window lives in this one process) and lets createWindow() avoid
overlapping any of them.

Actually creating a window (QQmlComponent + per-window QQmlContext, see
main.py) is injected as `window_factory` rather than done here, so this
class stays Qt-QML-plumbing-agnostic and easy to unit test without a real
QQmlEngine.
"""
from __future__ import annotations

import shutil
from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QJSValue

from window_registry import (
    DEFAULT_TAG,
    WindowRegistry,
    instance_dir_for,
    settings_path_for,
)


def _rects_overlap(ax, ay, aw, ah, bx, by, bw, bh) -> bool:
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


class WindowManager(QObject):
    windowsChanged = Signal()
    # Emits the window_id currently under the pointer while a task drag is
    # in progress (see TaskDelegate.qml's drag handle), plus the pointer's
    # own global/screen position, or "" (with x=y=0) once it isn't over any
    # window / the drag ended. Every window's Main.qml listens: it
    # highlights its own border iff it's the target, AND — being the only
    # one that actually knows its own ListView's contentY/row layout —
    # converts the given global position into its own local list coordinates
    # to drive that list's reflow-placeholder and edge auto-scroll. This is
    # what lets one window's drag show a placeholder in a *different*
    # window's list without a per-window DropArea or any direct reference
    # between the two windows' QML trees.
    taskDragHoverChanged = Signal(str, int, int)

    def __init__(
        self,
        registry: WindowRegistry,
        window_factory: Callable,
        restore_factory: Callable | None = None,
        drag_ghost=None,
        parent=None,
    ):
        super().__init__(parent)
        self._registry = registry
        self._window_factory = window_factory
        # Rebuilds a window from its own persisted tasks/settings (no
        # caller_state cloning, unlike window_factory) — used by openWindow()
        # to bring a closed window back. Optional/None in tests that never
        # exercise openWindow().
        self._restore_factory = restore_factory
        # A single app-wide DragGhost.qml instance (built once in main.py,
        # reused for every drag) — see showDragGhost/moveDragGhost/
        # hideDragGhost. Optional/None in tests that never exercise it; a
        # plain QObject with QML dynamic properties (taskText/status/
        # visible/x/y), driven via setProperty() rather than typed Python
        # attributes since it's created from QML, not a Python class.
        self._drag_ghost = drag_ghost
        # Row index (within the current drop target window's own _visible
        # list) the drag is hovering over right now, or -1 for "no specific
        # row" — reported live by whichever window's Main.qml is the current
        # target (see setDragHoverIndex below), since only that window's own
        # QML layout actually knows it. Read back by moveTaskToWindow() at
        # drop time so a cross-window move lands where its placeholder was
        # shown, instead of always at the top.
        self._drag_hover_index = -1
        # window_id -> {"window": QQuickWindow, ...keepalive refs...}
        self._windows: dict[str, dict] = {}

    def register_window(self, window_id: str, window, **extra) -> None:
        """Called by main.py right after a window is actually created."""
        self._windows[window_id] = {"window": window, **extra}
        window.visibleChanged.connect(
            lambda visible, wid=window_id: (not visible) and self._on_window_closed(wid)
        )
        # Without this, a window created earlier in a multi-window startup
        # (each restored one at a time via _make_window) has already read
        # openWindowCount's QML binding by the time later windows register
        # here, and that binding then never gets a notify signal to
        # re-evaluate against the now-larger count — so its close button
        # stays stuck looking disabled forever, even once several windows
        # are open. Confirmed live: with 4 windows restored at startup, the
        # first two (whose bindings evaluated while the live count was
        # still <= 1) kept disabled-looking close buttons while the last
        # two (evaluated once the count had already grown past 1) did not.
        self.windowsChanged.emit()

    def _on_window_closed(self, window_id: str) -> None:
        if window_id in self._windows:
            del self._windows[window_id]
            self.windowsChanged.emit()

    def is_open(self, window_id: str) -> bool:
        return window_id in self._windows

    def _get_open_window_count(self) -> int:
        return len(self._windows)

    # Reactive QML-facing count of currently open windows — same "at least
    # one must stay open" number closeWindow() itself guards on, exposed so
    # Main.qml's close ("X") button can look/behave disabled (not just
    # silently no-op) once it's the only one left. A plain
    # windowManager.listWindows().length inside a QML binding would NOT do
    # this reactively — a method call inside a binding expression doesn't
    # register as a tracked dependency (see getBorderColor's own comment on
    # listWindows(), same underlying gotcha) — hence a real Property here,
    # notified by the same windowsChanged signal every mutator already emits.
    openWindowCount = Property(int, _get_open_window_count, notify=windowsChanged)

    @Slot(result="QVariant")
    def listWindows(self):
        # "open" here is the *live* state (is it actually running right now,
        # via is_open()) — not the persisted registry field of the same name
        # (which only matters at next startup) — so the SHOW toggle in
        # YatasView always reflects reality, including for a window closed
        # or opened moments ago in this same session.
        #
        # borderColor is included here (not read via a separate
        # windowManager.getBorderColor() call from inside a QML binding) so
        # YatasRow's tag-name color is a genuine reactive property binding
        # off modelData — a plain method call inside a QML binding
        # expression doesn't register the underlying value as a tracked
        # dependency, so it would silently never re-evaluate after picking
        # a new color, even though this array gets freshly rebuilt on every
        # windowsChanged (confirmed live: exactly this symptom, color
        # picked but the list never updated).
        return [
            dict(e, open=self.is_open(e["id"]), borderColor=self.getBorderColor(e["id"]))
            for e in self._registry.list()
        ]

    @Slot(str, result=str)
    def tagFor(self, window_id: str) -> str:
        return self._registry.get_tag(window_id)

    @Slot(str)
    def closeWindow(self, window_id: str) -> None:
        """Hides a window (YatasView's SHOW toggle, off) without touching its
        registry entry or data files — unlike deleteWindow, it can be
        reopened later via openWindow().

        No-op if this is the only window currently open — same "at least one
        must stay" guard as TaskListModel's visibility filters, and for the
        same reason: closing the last one would leave nothing on screen and
        no YatasView left to reach to reopen anything.
        """
        if window_id in self._windows and len(self._windows) <= 1:
            return
        entry = self._windows.pop(window_id, None)
        if entry is not None:
            entry["window"].close()
        self._registry.set_open(window_id, False)
        self.windowsChanged.emit()

    @Slot(str)
    def openWindow(self, window_id: str) -> None:
        """Reopens a window previously closed via closeWindow() (YatasView's
        SHOW toggle, on), rebuilt fresh from its own persisted tasks/settings
        — same as at app startup."""
        if self.is_open(window_id) or self._restore_factory is None:
            return
        self._restore_factory(window_id)
        self._registry.set_open(window_id, True)
        self.windowsChanged.emit()

    @Slot(str, str)
    def renameWindow(self, window_id: str, new_tag: str) -> None:
        new_tag = new_tag.strip()
        if not new_tag:
            return
        self._registry.rename(window_id, new_tag)
        self.windowsChanged.emit()

    def _open_settings_for(self, window_id: str):
        """Same shape as main.py's own _open_settings() — reimplemented
        here rather than imported to avoid a window_manager -> main
        circular import (main.py already imports WindowManager)."""
        from PySide6.QtCore import QSettings

        from window_registry import settings_path_for

        path = settings_path_for(window_id)
        return QSettings(path, QSettings.IniFormat) if path else QSettings("yata", "yata")

    @Slot(str, result=str)
    def getBorderColor(self, window_id: str) -> str:
        """"" means "no custom color, follow the theme" (r-4.md). Reads the
        live AppSettings if the window is open (matches what's actually on
        screen right now), else opens its settings file directly — YatasView
        lists closed windows too, so this needs to work either way.

        entry.get("app_settings") rather than entry["app_settings"]: some
        callers (register_window's own test helpers, and window_factory
        results that never wire a live AppSettings) register a window
        without one — listWindows() now calls this for every window
        unconditionally (r-6, so the YATAS list's tag-name color is a real
        reactive property rather than a QML-side method call), so this
        needs to degrade gracefully to the settings-file path instead of
        crashing for those, exactly like an actually-closed window already
        does.
        """
        entry = self._windows.get(window_id)
        app_settings = entry.get("app_settings") if entry is not None else None
        if app_settings is not None:
            return app_settings.borderColor
        return str(self._open_settings_for(window_id).value("theme/borderColor", ""))

    @Slot(str, str)
    def setBorderColor(self, window_id: str, color: str) -> None:
        """Sets window_id's custom border/tag-name color (see getBorderColor).
        For an open window this goes through its live AppSettings object —
        the same one Main.qml's border/tag bindings already read from, so
        the change applies and previews instantly with no extra signal
        plumbing needed here.

        windowsChanged is emitted regardless (matching every other mutator
        in this class) so YatasView.refresh() re-reads the new color for
        that row's own tag-name text — the live-AppSettings path above
        doesn't need this for the owning window's own border/tag
        (Main.qml's binding already tracks appSettings.borderColor
        directly), but YatasView's list is a different window entirely
        with no such binding of its own.
        """
        entry = self._windows.get(window_id)
        if entry is not None:
            entry["app_settings"].borderColor = color
        else:
            settings = self._open_settings_for(window_id)
            settings.setValue("theme/borderColor", color)
            settings.sync()
        self.windowsChanged.emit()

    @Slot(str)
    def deleteWindow(self, window_id: str) -> None:
        """Soft-deletes a window (YatasView's DELETED category, the trash
        icon on an ACTIVE row): closes it if currently open and marks it
        deleted in the registry, WITHOUT touching its data files — the
        registry entry and its on-disk tasks/settings both stay put.
        Recoverable later via recreateWindow(), or permanently discarded via
        purgeWindow()."""
        entry = self._windows.pop(window_id, None)
        if entry is not None:
            entry["window"].close()
        self._registry.set_open(window_id, False)
        self._registry.set_deleted(window_id, True)
        self.windowsChanged.emit()

    @Slot(str)
    def recreateWindow(self, window_id: str) -> None:
        """Un-deletes and reopens a window previously soft-deleted via
        deleteWindow() (YatasView's DELETED category, 'Re-create') —
        rebuilt fresh from its own still-on-disk tasks/settings, same as
        openWindow() (which this delegates to once the deleted flag is
        cleared)."""
        self._registry.set_deleted(window_id, False)
        self.openWindow(window_id)

    @Slot(str)
    def purgeWindow(self, window_id: str) -> None:
        """Permanently discards a soft-deleted window: removes its registry
        entry entirely and deletes its on-disk tasks/settings (YatasView's
        DELETED category, 'Purge' — the only way any of this data actually
        gets removed; deleteWindow() above never does). Closes it first if
        somehow still open — shouldn't normally happen, since deleteWindow()
        always closes before marking deleted, but harmless/defensive either
        way (same close-then-discard shape deleteWindow itself uses)."""
        entry = self._windows.pop(window_id, None)
        if entry is not None:
            entry["window"].close()
        self._registry.remove(window_id)
        # instance_dir_for() is this window's WHOLE data directory now (not
        # just tasks.json) — a plugin can own more than one file in it (see
        # window_registry.instance_dir_for()'s own docstring, r-10.md).
        # Discarding the entire directory is what "permanently discards...
        # data" has always promised; removing only tasks.json (the original
        # behavior here) silently left every other plugin-owned file behind
        # forever, e.g. simple_task_list's own plugin-state.json.
        instance_dir = instance_dir_for(window_id)
        if instance_dir:
            shutil.rmtree(instance_dir, ignore_errors=True)
        settings_path = settings_path_for(window_id)
        if settings_path:
            _remove_file(settings_path)
        self.windowsChanged.emit()

    def _find_free_position(self, width: int, height: int, start_x: int, start_y: int):
        occupied = [
            (w["window"].x(), w["window"].y(), w["window"].width(), w["window"].height())
            for w in self._windows.values()
        ]
        screen = QGuiApplication.primaryScreen().geometry()
        step = 40
        x, y = start_x + step, start_y + step
        for _ in range(200):
            if x + width > screen.x() + screen.width():
                x = screen.x() + step
            if y + height > screen.y() + screen.height():
                y = screen.y() + step
            if not any(_rects_overlap(x, y, width, height, *r) for r in occupied):
                return x, y
            x += step
            y += step
        return x, y

    @Slot("QVariant", result=str)
    def createWindow(self, caller_state) -> str:
        # QML calls this with a JS object literal, which PySide hands over
        # as a QJSValue (not auto-converted to a Python dict) — must be
        # unwrapped via toVariant() first. Direct Python callers (tests)
        # already pass a plain dict, so only convert when needed.
        if isinstance(caller_state, QJSValue):
            caller_state = caller_state.toVariant()
        caller_state = dict(caller_state)
        window_id = self._registry.add(self._registry.next_available_tag(DEFAULT_TAG))
        width, height = int(caller_state["width"]), int(caller_state["height"])
        x, y = self._find_free_position(width, height, int(caller_state["x"]), int(caller_state["y"]))
        # The factory (main.py) is responsible for actually constructing the
        # window and calling register_window() on it (which itself emits
        # windowsChanged) — this class stays agnostic of QQmlComponent/
        # context mechanics.
        self._window_factory(window_id, dict(caller_state, x=x, y=y))
        return window_id

    @Slot(str, str)
    def showDragGhost(self, text: str, status: str) -> None:
        """Shows the app-wide floating drag preview (DragGhost.qml) — called
        once a task's drag gesture actually starts, so the user can see what
        they're moving even once the pointer leaves the source window's own
        bounds (an ordinary QML Item can't render outside its own window)."""
        if self._drag_ghost is None:
            return
        self._drag_ghost.setProperty("taskText", text)
        self._drag_ghost.setProperty("status", status)
        self._drag_ghost.setProperty("visible", True)

    @Slot(int, int)
    def moveDragGhost(self, global_x: int, global_y: int) -> None:
        """Repositions the drag preview to track the pointer — small offset
        so it trails just past the cursor rather than sitting exactly under
        it (and, incidentally, never itself gets in the way of the
        windowAt() hit-test, which uses the raw un-offset pointer position)."""
        if self._drag_ghost is None:
            return
        self._drag_ghost.setProperty("x", global_x + 12)
        self._drag_ghost.setProperty("y", global_y + 12)

    @Slot()
    def hideDragGhost(self) -> None:
        if self._drag_ghost is None:
            return
        self._drag_ghost.setProperty("visible", False)

    @Slot(int, int, result=str)
    def windowAt(self, global_x: int, global_y: int) -> str:
        """window_id of the open window (including the caller's own, if
        that's genuinely where the point is — no exclusion, unlike earlier
        versions of this method: same-window reorder and cross-window move
        are now just two cases of "which window is currently under the
        pointer") whose on-screen geometry contains the given point in
        global/screen coordinates, or "" if none. Called on every pointer
        move while dragging a task's handle (TaskDelegate.qml) to find the
        drop target. Also broadcasts taskDragHoverChanged (with this same
        point) so every window can update its own drop-target highlight and
        placeholder, sparing the caller a second round trip just for that.
        """
        target = ""
        for window_id, entry in self._windows.items():
            if entry["window"].geometry().contains(global_x, global_y):
                target = window_id
                break
        if target == "":
            self._drag_hover_index = -1
        self.taskDragHoverChanged.emit(target, global_x, global_y)
        return target

    @Slot(int)
    def setDragHoverIndex(self, index: int) -> None:
        """Called by whichever window's Main.qml is the current drop target,
        right after it computes its own listView.dragHoverIndex from the
        taskDragHoverChanged broadcast above — the connection is a direct,
        same-thread Qt signal, so this always lands before windowAt() (which
        triggered it) returns to its caller. moveTaskToWindow() reads this
        back at drop time; nothing else needs it."""
        self._drag_hover_index = index

    @Slot()
    def clearDragHover(self) -> None:
        """Called once a task drag ends (drop or cancel) so no window is left
        showing a stale drop-target highlight or placeholder."""
        self._drag_hover_index = -1
        self.taskDragHoverChanged.emit("", 0, 0)

    @Slot(str, str, str, result=bool)
    def moveTaskToWindow(self, source_window_id: str, task_id: str, target_window_id: str) -> bool:
        """Moves one item from one open window's plugin content to another's
        — TaskDelegate.qml's drag handle, dropped on a different window
        (detected via windowAt()) instead of a row in the same list. Lands
        it at self._drag_hover_index (see setDragHoverIndex), i.e. wherever
        the target window's own placeholder was last shown, not always at
        the top.

        Routed through each window's own plugin_content.take_item/insert_item
        (r-9.md step 5) rather than reaching into a hardcoded "task_model"
        entry — a cross-window move is only possible between two windows
        whose plugin both support it; either one leaving a hook None (e.g.
        a future plugin with no concept of movable items) makes this a
        no-op, same as a missing window entry."""
        if source_window_id == target_window_id:
            return False
        source_entry = self._windows.get(source_window_id)
        target_entry = self._windows.get(target_window_id)
        if source_entry is None or target_entry is None:
            return False
        take_item = source_entry["plugin_content"].take_item
        insert_item = target_entry["plugin_content"].insert_item
        if take_item is None or insert_item is None:
            return False
        item = take_item(task_id)
        if item is None:
            return False
        insert_item(item, self._drag_hover_index)
        return True


def _remove_file(path: str) -> None:
    """Used for settings_path_for()'s own file only now — the per-instance
    data directory (instance_dir_for()) is discarded wholesale via
    shutil.rmtree in purgeWindow() above instead. settings_path_for()'s
    directory (instances/, config-side) is shared across every window's
    own .conf file, so the empty-dir cleanup below is a harmless no-op in
    the common case rather than something that actually fires."""
    import os

    if os.path.isfile(path):
        os.remove(path)
    parent = os.path.dirname(path)
    try:
        if os.path.isdir(parent) and not os.listdir(parent):
            os.rmdir(parent)
    except OSError:
        pass

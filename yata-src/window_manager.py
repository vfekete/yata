from __future__ import annotations

import shutil
from typing import Callable

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtGui import QGuiApplication

import plugins_registry
from qml_interop import unwrap_qvariant
from window_registry import (
    DEFAULT_PLUGIN_ID,
    DEFAULT_TAG,
    WindowRegistry,
    instance_dir_for,
    settings_path_for,
)


def _rects_overlap(ax, ay, aw, ah, bx, by, bw, bh) -> bool:
    return ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah


class WindowManager(QObject):
    windowsChanged = Signal()
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
        self._restore_factory = restore_factory
        self._drag_ghost = drag_ghost
        self._drag_hover_index = -1
        self._windows: dict[str, dict] = {}

    def register_window(self, window_id: str, window, **extra) -> None:
        self._windows[window_id] = {"window": window, **extra}
        window.visibleChanged.connect(
            lambda visible, wid=window_id: (not visible) and self._on_window_closed(wid)
        )
        self.windowsChanged.emit()

    def _on_window_closed(self, window_id: str) -> None:
        if window_id in self._windows:
            del self._windows[window_id]
            self.windowsChanged.emit()

    def is_open(self, window_id: str) -> bool:
        return window_id in self._windows

    def _get_open_window_count(self) -> int:
        return len(self._windows)

    openWindowCount = Property(int, _get_open_window_count, notify=windowsChanged)

    @Slot(result="QVariant")
    def listWindows(self):
        return [
            dict(e, open=self.is_open(e["id"]), borderColor=self.getBorderColor(e["id"]))
            for e in self._registry.list()
        ]

    @Slot(result="QVariant")
    def listPlugins(self):
        return [
            {"id": p.id, "displayName": p.display_name}
            for p in plugins_registry.AVAILABLE_PLUGINS.values()
        ]

    @Slot(str, result=str)
    def tagFor(self, window_id: str) -> str:
        return self._registry.get_tag(window_id)

    @Slot(str)
    def closeWindow(self, window_id: str) -> None:
        if window_id in self._windows and len(self._windows) <= 1:
            return
        entry = self._windows.pop(window_id, None)
        if entry is not None:
            entry["window"].close()
        self._registry.set_open(window_id, False)
        self.windowsChanged.emit()

    @Slot(str)
    def openWindow(self, window_id: str) -> None:
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
        from PySide6.QtCore import QSettings

        from window_registry import settings_path_for

        path = settings_path_for(window_id)
        return QSettings(path, QSettings.IniFormat) if path else QSettings("yata", "yata")

    @Slot(str, result=str)
    def getBorderColor(self, window_id: str) -> str:
        entry = self._windows.get(window_id)
        app_settings = entry.get("app_settings") if entry is not None else None
        if app_settings is not None:
            return app_settings.borderColor
        return str(self._open_settings_for(window_id).value("theme/borderColor", ""))

    @Slot(str, str)
    def setBorderColor(self, window_id: str, color: str) -> None:
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
        entry = self._windows.pop(window_id, None)
        if entry is not None:
            entry["window"].close()
        self._registry.set_open(window_id, False)
        self._registry.set_deleted(window_id, True)
        self.windowsChanged.emit()

    @Slot(str)
    def recreateWindow(self, window_id: str) -> None:
        self._registry.set_deleted(window_id, False)
        self.openWindow(window_id)

    @Slot(str)
    def purgeWindow(self, window_id: str) -> None:
        entry = self._windows.pop(window_id, None)
        if entry is not None:
            entry["window"].close()
        self._registry.remove(window_id)
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
        caller_state = dict(unwrap_qvariant(caller_state))
        plugin_id = caller_state.get("plugin", DEFAULT_PLUGIN_ID)
        window_id = self._registry.add(self._registry.next_available_tag(DEFAULT_TAG), plugin=plugin_id)
        width, height = int(caller_state["width"]), int(caller_state["height"])
        x, y = self._find_free_position(width, height, int(caller_state["x"]), int(caller_state["y"]))
        self._window_factory(window_id, dict(caller_state, x=x, y=y))
        return window_id

    @Slot(str, str)
    def showDragGhost(self, text: str, status: str) -> None:
        if self._drag_ghost is None:
            return
        self._drag_ghost.setProperty("taskText", text)
        self._drag_ghost.setProperty("status", status)
        self._drag_ghost.setProperty("visible", True)

    @Slot(int, int)
    def moveDragGhost(self, global_x: int, global_y: int) -> None:
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
        self._drag_hover_index = index

    @Slot()
    def clearDragHover(self) -> None:
        self._drag_hover_index = -1
        self.taskDragHoverChanged.emit("", 0, 0)

    @Slot(str, str, str, result=bool)
    def moveTaskToWindow(self, source_window_id: str, task_id: str, target_window_id: str) -> bool:
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
    import os

    if os.path.isfile(path):
        os.remove(path)
    parent = os.path.dirname(path)
    try:
        if os.path.isdir(parent) and not os.listdir(parent):
            os.rmdir(parent)
    except OSError:
        pass

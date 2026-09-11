from __future__ import annotations

import re
import uuid
from datetime import datetime

from PySide6.QtCore import QAbstractListModel, QModelIndex, QSettings, Qt, Signal, Slot, Property

from plugins.simple_task_list.storage import STATUS_ACTIVE, STATUS_CANCELLED, STATUS_DONE, Task, TaskStore

_MARKDOWN_LINK_RE = re.compile(r"\[([^\]\n]*)\]\(([^)\n]*)\)")


def _read_bool(s: QSettings, key: str, default: bool) -> bool:
    v = s.value(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() not in ("false", "0", "no")
    return bool(v)

_ID, _TEXT, _STATUS, _DAY_LABEL, _COMPLETED_AT, _NOTE = (Qt.UserRole + i for i in range(1, 7))


def day_label(iso_timestamp: str) -> str:
    day = datetime.fromisoformat(iso_timestamp).date()
    return day.strftime("%A, %d %B %Y")


class TaskListModel(QAbstractListModel):
    canReorderChanged = Signal()
    groupByDayChanged = Signal()
    statusSortModeChanged = Signal()
    searchTextChanged = Signal()
    showActiveChanged = Signal()
    showDoneChanged = Signal()
    showCancelledChanged = Signal()
    taskAdded = Signal(str)

    def __init__(self, store: TaskStore, settings: QSettings | None = None, parent=None):
        super().__init__(parent)
        self._store = store
        self._settings = settings or QSettings("yata", "yata")
        self._tasks: list[Task] = store.load()
        self._visible: list[Task] = []
        self._search = ""
        self._status_sort = str(self._settings.value("filters/statusSortMode", ""))
        self._group_by_day = _read_bool(self._settings, "filters/groupByDay", False)
        self._show_active = _read_bool(self._settings, "filters/showActive", True)
        self._show_done = _read_bool(self._settings, "filters/showDone", True)
        self._show_cancelled = _read_bool(self._settings, "filters/showCancelled", True)
        self._recompute()

    def roleNames(self):
        return {
            _ID: b"taskId",
            _TEXT: b"text",
            _STATUS: b"status",
            _DAY_LABEL: b"dayLabel",
            _COMPLETED_AT: b"completedAt",
            _NOTE: b"note",
        }

    def rowCount(self, parent=QModelIndex()):
        if parent.isValid():
            return 0
        return len(self._visible)

    def data(self, index: QModelIndex, role: int):
        if not index.isValid():
            return None
        task = self._visible[index.row()]
        if role == _ID:
            return task.id
        if role == _TEXT:
            return task.text
        if role == _STATUS:
            return task.status
        if role == _DAY_LABEL:
            return day_label(task.created_at)
        if role == _COMPLETED_AT:
            return task.completed_at
        if role == _NOTE:
            return task.note
        return None

    def _get_can_reorder(self) -> bool:
        return not self._search

    canReorder = Property(bool, _get_can_reorder, notify=canReorderChanged)

    def _get_group_by_day(self) -> bool:
        return self._group_by_day

    groupByDay = Property(bool, _get_group_by_day, notify=groupByDayChanged)

    def _get_status_sort_mode(self) -> str:
        return self._status_sort

    statusSortMode = Property(str, _get_status_sort_mode, notify=statusSortModeChanged)

    def _get_show_active(self) -> bool:
        return self._show_active

    showActive = Property(bool, _get_show_active, notify=showActiveChanged)

    def _get_show_done(self) -> bool:
        return self._show_done

    showDone = Property(bool, _get_show_done, notify=showDoneChanged)

    def _get_show_cancelled(self) -> bool:
        return self._show_cancelled

    showCancelled = Property(bool, _get_show_cancelled, notify=showCancelledChanged)

    def _get_search_text(self) -> str:
        return self._search

    searchText = Property(str, _get_search_text, notify=searchTextChanged)

    def _recompute(self):
        old_ids = [t.id for t in self._visible]
        items = self._tasks
        if self._search:
            needle = self._search.lower()
            items = [t for t in items if needle in t.text.lower()]
        if not self._show_active:
            items = [t for t in items if t.status != STATUS_ACTIVE]
        if not self._show_done:
            items = [t for t in items if t.status != STATUS_DONE]
        if not self._show_cancelled:
            items = [t for t in items if t.status != STATUS_CANCELLED]
        if self._group_by_day:
            def day_sort_key(t: Task):
                day_ordinal = datetime.fromisoformat(t.created_at).date().toordinal()
                status_rank = 0 if not self._status_sort or t.status == self._status_sort else 1
                return (-day_ordinal, status_rank)

            items = sorted(items, key=day_sort_key)
        elif self._status_sort:
            items = sorted(items, key=lambda t: t.status != self._status_sort)

        new_ids = [t.id for t in items]
        if new_ids == old_ids:
            self._visible = items
            if items:
                self.dataChanged.emit(self.index(0), self.index(len(items) - 1), [])
        else:
            self.beginResetModel()
            self._visible = items
            self.endResetModel()

    def _save(self):
        self._store.save(self._tasks)

    def _insert(self, task: Task, at: int = 0) -> None:
        self._tasks.insert(at, task)
        was_reorderable = self._get_can_reorder()
        self._recompute()
        if was_reorderable != self._get_can_reorder():
            self.canReorderChanged.emit()
        self._save()
        self.taskAdded.emit(task.id)

    @Slot(result=str)
    def addTask(self) -> str:
        self._tasks = [t for t in self._tasks if t.text]
        task = Task(text="", status=STATUS_ACTIVE)
        self._insert(task)
        return task.id

    def insert_task(self, task: Task, target_index: int = -1) -> None:
        if self._find(task.id) is not None:
            task.id = uuid.uuid4().hex
        if 0 <= target_index < len(self._visible):
            target_task = self._visible[target_index]
            self._insert(task, at=self._tasks.index(target_task) + 1)
        else:
            self._insert(task)

    def take_task(self, task_id: str) -> Task | None:
        task = self._find(task_id)
        if task is None:
            return None
        self._tasks.remove(task)
        self._recompute()
        self._save()
        return task

    def _find(self, task_id: str) -> Task | None:
        for task in self._tasks:
            if task.id == task_id:
                return task
        return None

    @Slot(str, str)
    def setText(self, task_id: str, text: str):
        task = self._find(task_id)
        if task is None or task.text == text:
            return
        task.text = text
        self._recompute()
        self._save()

    @Slot(str, str)
    def setStatus(self, task_id: str, status: str):
        if status not in (STATUS_ACTIVE, STATUS_DONE, STATUS_CANCELLED):
            return
        task = self._find(task_id)
        if task is None:
            return
        task.status = status
        if status in (STATUS_DONE, STATUS_CANCELLED):
            task.completed_at = datetime.now().isoformat()
        self._recompute()
        self._save()

    @Slot(str, str)
    def setNote(self, task_id: str, note: str):
        task = self._find(task_id)
        if task is None or task.note == note:
            return
        task.note = note
        self._recompute()
        self._save()

    @Slot(str, result=str)
    def noteFor(self, task_id: str) -> str:
        task = self._find(task_id)
        return task.note if task is not None else ""

    @Slot(str)
    def deleteTask(self, task_id: str):
        self.take_task(task_id)

    def _rebase_manual_order(self, new_visible_order: list[Task]):
        visible_ids = {t.id for t in self._visible}
        new_order_iter = iter(new_visible_order)
        self._tasks = [
            next(new_order_iter) if t.id in visible_ids else t
            for t in self._tasks
        ]

    def _reposition(self, moved_task: Task, target_task: Task, after: bool):
        if self._status_sort:
            new_visible = [t for t in self._visible if t.id != moved_task.id]
            insert_at = next(i for i, t in enumerate(new_visible) if t.id == target_task.id)
            if after:
                insert_at += 1
            new_visible.insert(insert_at, moved_task)

            self._rebase_manual_order(new_visible)

            self._status_sort = ""
            self._settings.setValue("filters/statusSortMode", "")
            self._settings.sync()
            self.statusSortModeChanged.emit()
        else:
            self._tasks.remove(moved_task)
            pos = self._tasks.index(target_task)
            self._tasks.insert(pos + 1 if after else pos, moved_task)

    @Slot(int, int)
    def moveTask(self, from_index: int, to_index: int):
        if not self._get_can_reorder():
            return
        if from_index == to_index or not (0 <= from_index < len(self._visible)) or not (
            0 <= to_index < len(self._visible)
        ):
            return
        moved_task = self._visible[from_index]
        target_task = self._visible[to_index]

        if self._group_by_day:
            moved_day = datetime.fromisoformat(moved_task.created_at).date()
            target_day = datetime.fromisoformat(target_task.created_at).date()
            if moved_day != target_day:
                old_dt = datetime.fromisoformat(moved_task.created_at)
                moved_task.created_at = old_dt.replace(
                    year=target_day.year, month=target_day.month, day=target_day.day
                ).isoformat()

        self._reposition(moved_task, target_task, after=True)
        self._recompute()
        self._save()

    def _move_by_one(self, task_id: str, delta: int):
        if not self._get_can_reorder():
            return
        index = next((i for i, t in enumerate(self._visible) if t.id == task_id), None)
        if index is None:
            return
        new_index = index + delta
        if not (0 <= new_index < len(self._visible)):
            return
        moved_task = self._visible[index]
        neighbor_task = self._visible[new_index]

        if self._group_by_day:
            moved_day = datetime.fromisoformat(moved_task.created_at).date()
            neighbor_day = datetime.fromisoformat(neighbor_task.created_at).date()
            if moved_day != neighbor_day:
                old_dt = datetime.fromisoformat(moved_task.created_at)
                moved_task.created_at = old_dt.replace(
                    year=neighbor_day.year, month=neighbor_day.month, day=neighbor_day.day
                ).isoformat()

        self._reposition(moved_task, neighbor_task, after=delta > 0)
        self._recompute()
        self._save()

    @Slot(str)
    def moveTaskUp(self, task_id: str):
        self._move_by_one(task_id, -1)

    @Slot(str)
    def moveTaskDown(self, task_id: str):
        self._move_by_one(task_id, 1)

    @Slot(str)
    def setSearchText(self, text: str):
        if text == self._search:
            return
        was_reorderable = self._get_can_reorder()
        self._search = text
        self._recompute()
        self.searchTextChanged.emit()
        if was_reorderable != self._get_can_reorder():
            self.canReorderChanged.emit()

    @Slot(str)
    def setStatusSortMode(self, mode: str):
        if mode == self._status_sort:
            return
        was_reorderable = self._get_can_reorder()
        if mode == "" and self._status_sort:
            self._rebase_manual_order(self._visible)
        self._status_sort = mode
        self._settings.setValue("filters/statusSortMode", mode)
        self._settings.sync()
        self._recompute()
        self.statusSortModeChanged.emit()
        if was_reorderable != self._get_can_reorder():
            self.canReorderChanged.emit()

    @Slot(bool)
    def setGroupByDay(self, flag: bool):
        if flag == self._group_by_day:
            return
        was_reorderable = self._get_can_reorder()
        self._group_by_day = flag
        self._settings.setValue("filters/groupByDay", flag)
        self._settings.sync()
        self._recompute()
        self.groupByDayChanged.emit()
        if was_reorderable != self._get_can_reorder():
            self.canReorderChanged.emit()

    @Slot(bool)
    def setShowActive(self, flag: bool):
        if flag == self._show_active:
            return
        if not flag and not self._show_done and not self._show_cancelled:
            return
        self._show_active = flag
        self._settings.setValue("filters/showActive", flag)
        self._settings.sync()
        self._recompute()
        self.showActiveChanged.emit()

    @Slot(bool)
    def setShowDone(self, flag: bool):
        if flag == self._show_done:
            return
        if not flag and not self._show_active and not self._show_cancelled:
            return
        self._show_done = flag
        self._settings.setValue("filters/showDone", flag)
        self._settings.sync()
        self._recompute()
        self.showDoneChanged.emit()

    @Slot(bool)
    def setShowCancelled(self, flag: bool):
        if flag == self._show_cancelled:
            return
        if not flag and not self._show_active and not self._show_done:
            return
        self._show_cancelled = flag
        self._settings.setValue("filters/showCancelled", flag)
        self._settings.sync()
        self._recompute()
        self.showCancelledChanged.emit()

    @Slot()
    def reloadTasks(self):
        self._tasks = self._store.load()
        self._recompute()

    @Slot(int, int, result='QVariant')
    def monthCounts(self, year: int, month: int):
        counts: dict[int, dict[str, int]] = {}
        for t in self._tasks:
            d = datetime.fromisoformat(t.created_at).date()
            if d.year == year and d.month == month:
                bucket = counts.setdefault(d.day, {"active": 0, "done": 0, "cancelled": 0})
                bucket[t.status] += 1
        return [{"day": day, **c} for day, c in sorted(counts.items())]

    @Slot(int, result='QVariant')
    def yearCounts(self, year: int):
        counts: dict[int, dict[str, int]] = {}
        for t in self._tasks:
            d = datetime.fromisoformat(t.created_at).date()
            if d.year == year:
                bucket = counts.setdefault(d.month, {"active": 0, "done": 0, "cancelled": 0})
                bucket[t.status] += 1
        return [{"month": month, **c} for month, c in sorted(counts.items())]

    @Slot(int, int, int, result=int)
    def indexForDate(self, year: int, month: int, day: int) -> int:
        for i, t in enumerate(self._visible):
            d = datetime.fromisoformat(t.created_at).date()
            if d.year == year and d.month == month and d.day == day:
                return i
        return -1

    @Slot(str, result=int)
    def indexForTask(self, task_id: str) -> int:
        for i, t in enumerate(self._visible):
            if t.id == task_id:
                return i
        return -1

    @Slot(result='QVariant')
    def linkedTasks(self):
        result = []
        for t in self._tasks:
            matches = _MARKDOWN_LINK_RE.findall(t.text)
            if matches:
                links = [{"label": label or url, "url": url} for label, url in matches]
                result.append({
                    "taskId": t.id,
                    "status": t.status,
                    "completedAt": t.completed_at,
                    "links": links,
                })
        return result

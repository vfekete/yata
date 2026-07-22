"""Qt list model exposing tasks to QML."""
from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import QAbstractListModel, QModelIndex, QSettings, Qt, Signal, Slot, Property

from storage import STATUS_ACTIVE, STATUS_CANCELLED, STATUS_DONE, Task, TaskStore


def _read_bool(s: QSettings, key: str, default: bool) -> bool:
    """Read a boolean from QSettings, correctly handling stored 'false' strings."""
    v = s.value(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.lower() not in ("false", "0", "no")
    return bool(v)

_ID, _TEXT, _STATUS, _DAY_LABEL, _COMPLETED_AT = (Qt.UserRole + i for i in range(1, 6))


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
    taskAdded = Signal(str)  # emits the new task's ID after the model is ready

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

    # --- QAbstractListModel plumbing -------------------------------------

    def roleNames(self):
        return {
            _ID: b"taskId",
            _TEXT: b"text",
            _STATUS: b"status",
            _DAY_LABEL: b"dayLabel",
            _COMPLETED_AT: b"completedAt",
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
        return None

    # --- view state --------------------------------------------------------

    def _get_can_reorder(self) -> bool:
        # Grouping by day does not block manual reordering: dragging a task
        # onto a different day's section reassigns it to that day (see
        # moveTask). A search or an active status sort still does, since
        # the visible order isn't the manual order in those cases.
        return not (self._search or self._status_sort)

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
            # Day (newest first) is always the primary key; within a day,
            # respect the active status sort if any, else keep manual order
            # (both via Python's stable sort).
            def day_sort_key(t: Task):
                day_ordinal = datetime.fromisoformat(t.created_at).date().toordinal()
                status_rank = 0 if not self._status_sort or t.status == self._status_sort else 1
                return (-day_ordinal, status_rank)

            items = sorted(items, key=day_sort_key)
        elif self._status_sort:
            items = sorted(items, key=lambda t: t.status != self._status_sort)
        self.beginResetModel()
        self._visible = items
        self.endResetModel()

    # --- mutation slots, callable from QML ---------------------------------

    def _save(self):
        self._store.save(self._tasks)

    @Slot(result=str)
    def addTask(self) -> str:
        # Drop any empty tasks left over from a previous ADD that was
        # abandoned without typing anything (click-away without Enter/Esc).
        self._tasks = [t for t in self._tasks if t.text]
        task = Task(text="", status=STATUS_ACTIVE)
        self._tasks.insert(0, task)
        was_reorderable = self._get_can_reorder()
        self._recompute()
        if was_reorderable != self._get_can_reorder():
            self.canReorderChanged.emit()
        self._save()
        self.taskAdded.emit(task.id)
        return task.id

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

    @Slot(str)
    def deleteTask(self, task_id: str):
        task = self._find(task_id)
        if task is None:
            return
        self._tasks.remove(task)
        self._recompute()
        self._save()

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
                # Dropped onto a different day's section: reassign the task
                # to that day, keeping its original time of day.
                old_dt = datetime.fromisoformat(moved_task.created_at)
                moved_task.created_at = old_dt.replace(
                    year=target_day.year, month=target_day.month, day=target_day.day
                ).isoformat()

        # Reposition within the manual-order source list too, so plain
        # (non-grouped, non-sorted) view reflects the same drag.
        self._tasks.remove(moved_task)
        self._tasks.insert(self._tasks.index(target_task), moved_task)

        self._recompute()
        self._save()

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
        self._status_sort = mode
        self._settings.setValue("filters/statusSortMode", mode)
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
        self._recompute()
        self.groupByDayChanged.emit()
        if was_reorderable != self._get_can_reorder():
            self.canReorderChanged.emit()

    @Slot(bool)
    def setShowActive(self, flag: bool):
        if flag == self._show_active:
            return
        if not flag and not self._show_done and not self._show_cancelled:
            return  # at least one of Active/Done/Cancelled must stay visible
        self._show_active = flag
        self._settings.setValue("filters/showActive", flag)
        self._recompute()
        self.showActiveChanged.emit()

    @Slot(bool)
    def setShowDone(self, flag: bool):
        if flag == self._show_done:
            return
        if not flag and not self._show_active and not self._show_cancelled:
            return  # at least one of Active/Done/Cancelled must stay visible
        self._show_done = flag
        self._settings.setValue("filters/showDone", flag)
        self._recompute()
        self.showDoneChanged.emit()

    @Slot(bool)
    def setShowCancelled(self, flag: bool):
        if flag == self._show_cancelled:
            return
        if not flag and not self._show_active and not self._show_done:
            return  # at least one of Active/Done/Cancelled must stay visible
        self._show_cancelled = flag
        self._settings.setValue("filters/showCancelled", flag)
        self._recompute()
        self.showCancelledChanged.emit()

    @Slot()
    def reloadTasks(self):
        """Re-reads tasks.json from disk, discarding any in-memory state."""
        self._tasks = self._store.load()
        self._recompute()

    # --- calendar views (MonthView/YearView) --------------------------------

    @Slot(int, int, result='QVariant')
    def monthCounts(self, year: int, month: int):
        """Per-day active/done/cancelled counts for one month.

        Sparse: only days with at least one task are included. Ungrouped by
        self._search/showActive/etc. — the calendar always reflects every
        task regardless of the current visibility filters, since it's a
        navigation aid, not a filtered view.
        """
        counts: dict[int, dict[str, int]] = {}
        for t in self._tasks:
            d = datetime.fromisoformat(t.created_at).date()
            if d.year == year and d.month == month:
                bucket = counts.setdefault(d.day, {"active": 0, "done": 0, "cancelled": 0})
                bucket[t.status] += 1
        return [{"day": day, **c} for day, c in sorted(counts.items())]

    @Slot(int, result='QVariant')
    def yearCounts(self, year: int):
        """Per-month active/done/cancelled counts for one year. Sparse, see monthCounts."""
        counts: dict[int, dict[str, int]] = {}
        for t in self._tasks:
            d = datetime.fromisoformat(t.created_at).date()
            if d.year == year:
                bucket = counts.setdefault(d.month, {"active": 0, "done": 0, "cancelled": 0})
                bucket[t.status] += 1
        return [{"month": month, **c} for month, c in sorted(counts.items())]

    @Slot(int, int, int, result=int)
    def indexForDate(self, year: int, month: int, day: int) -> int:
        """Row index of the first task on the given date in the current
        (visible, day-grouped) list, or -1. Callers switch to Day/grouped
        view first (setGroupByDay(True) recomputes _visible synchronously),
        then use this to scroll the ListView to that day."""
        for i, t in enumerate(self._visible):
            d = datetime.fromisoformat(t.created_at).date()
            if d.year == year and d.month == month and d.day == day:
                return i
        return -1

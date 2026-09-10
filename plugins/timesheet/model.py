"""Qt list model exposing work items to QML, plus summary computation
(r-10.md)."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, Slot
from PySide6.QtQml import QJSValue

from . import pdf_export
from .storage import TimesheetStore, WorkItem, WorkSession


def _unwrap(value):
    """QML calls a "QVariant"-typed slot with a JS object literal, which
    PySide hands over as a QJSValue (not auto-converted to a Python dict)
    — must be unwrapped via toVariant() first. Same gotcha WindowManager.
    createWindow() already documents/handles; direct Python callers
    (tests) already pass a plain dict/None, so only convert when needed."""
    if isinstance(value, QJSValue):
        return value.toVariant()
    return value

_ID, _NAME, _NON_WORKING, _RUNNING, _DURATION_LABEL = (Qt.UserRole + i for i in range(1, 6))


def _parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def session_duration_by_day(session: WorkSession) -> dict:
    """Splits a session's duration across the calendar day(s) it actually
    spans — a session that ran past midnight contributes to each day it
    touches, not just the day it started on (explicit spec requirement).
    A still-running session (stop == "") contributes nothing yet — callers
    needing a live "so far today" total should stop-as-of-now themselves
    before calling this, same as the QML side already reads `running` to
    decide whether to keep ticking a live display.
    """
    if session.stop == "":
        return {}
    start = _parse(session.start)
    stop = _parse(session.stop)
    result: dict = {}
    cursor = start
    while cursor.date() < stop.date():
        day_end = datetime(cursor.year, cursor.month, cursor.day) + timedelta(days=1)
        result[cursor.date()] = result.get(cursor.date(), timedelta()) + (day_end - cursor)
        cursor = day_end
    result[cursor.date()] = result.get(cursor.date(), timedelta()) + (stop - cursor)
    return result


def format_duration(total: timedelta) -> str:
    total_minutes = int(total.total_seconds() // 60)
    hours, minutes = divmod(max(total_minutes, 0), 60)
    return f"{hours}h {minutes:02d}m"


def _period_bounds(period: str, reference: date) -> tuple[date, date]:
    """Inclusive [start, end] calendar-day range for `period` ("day",
    "week", "month", "year"), containing `reference`. Week starts Monday
    (ISO)."""
    if period == "day":
        return reference, reference
    if period == "week":
        start = reference - timedelta(days=reference.weekday())
        return start, start + timedelta(days=6)
    if period == "month":
        start = reference.replace(day=1)
        if start.month == 12:
            next_month = start.replace(year=start.year + 1, month=1)
        else:
            next_month = start.replace(month=start.month + 1)
        return start, next_month - timedelta(days=1)
    if period == "year":
        return date(reference.year, 1, 1), date(reference.year, 12, 31)
    raise ValueError(f"unknown period: {period!r}")


def _iter_days(start: date, end: date):
    cursor = start
    while cursor <= end:
        yield cursor
        cursor += timedelta(days=1)


def compute_summary(
    items: list[WorkItem], period: str, reference: date,
    holiday_dates: dict, daily_hours: float, day_locations: dict,
) -> dict:
    """One row per calendar day in the period, plus period totals.
    holiday_dates: {"YYYY-MM-DD": name}. A day is a "working day" (counts
    toward the target) unless it's a holiday or a weekend (Sat/Sun) — the
    spec's "8 hours per working day * number of working days" default
    target is computed the same way.
    """
    start, end = _period_bounds(period, reference)
    day_rows = []
    worked_total = timedelta()
    target_total = timedelta()
    for day in _iter_days(start, end):
        day_key = day.isoformat()
        is_weekend = day.weekday() >= 5
        holiday_name = holiday_dates.get(day_key, "")
        is_working_day = not is_weekend and not holiday_name
        day_worked = timedelta()
        for item in items:
            if item.non_working:
                continue
            for session in item.sessions:
                day_worked += session_duration_by_day(session).get(day, timedelta())
        day_target = timedelta(hours=daily_hours) if is_working_day else timedelta()
        worked_total += day_worked
        target_total += day_target
        day_rows.append({
            "date": day_key,
            "workedSeconds": day_worked.total_seconds(),
            "workedLabel": format_duration(day_worked),
            "targetSeconds": day_target.total_seconds(),
            "isWeekend": is_weekend,
            "isHoliday": bool(holiday_name),
            "holidayName": holiday_name,
            "isWorkingDay": is_working_day,
            "location": day_locations.get(day_key, ""),
        })
    remaining = target_total - worked_total
    return {
        "period": period,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "days": day_rows,
        "workedTotalLabel": format_duration(worked_total),
        "targetTotalLabel": format_duration(target_total),
        "remainingLabel": format_duration(remaining if remaining > timedelta() else timedelta()),
        "overtimeLabel": format_duration(-remaining if remaining < timedelta() else timedelta()),
    }


class TimesheetModel(QAbstractListModel):
    itemAdded = Signal(str)

    def __init__(self, store: TimesheetStore, parent=None):
        super().__init__(parent)
        self._store = store
        self._items, self._day_locations = store.load()

    # ── QAbstractListModel plumbing ──────────────────────────────────────

    def _visible(self) -> list[WorkItem]:
        return [i for i in self._items if not i.deleted]

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._visible())

    def roleNames(self):
        return {
            # "itemId", not "id" — "id" is QML's own reserved per-object
            # attribute, so a role literally named "id" can't be declared
            # as a `required property` on a delegate (same reasoning
            # TaskListModel's own "taskId" role name already documents).
            _ID: b"itemId",
            _NAME: b"name",
            _NON_WORKING: b"nonWorking",
            _RUNNING: b"running",
            _DURATION_LABEL: b"durationLabel",
        }

    def _total_duration(self, item: WorkItem) -> timedelta:
        total = timedelta()
        for session in item.sessions:
            for day_total in session_duration_by_day(session).values():
                total += day_total
        return total

    def data(self, index, role):
        items = self._visible()
        if not index.isValid() or not (0 <= index.row() < len(items)):
            return None
        item = items[index.row()]
        if role == _ID:
            return item.id
        if role == _NAME:
            return item.name
        if role == _NON_WORKING:
            return item.non_working
        if role == _RUNNING:
            return self._running_session(item) is not None
        if role == _DURATION_LABEL:
            return format_duration(self._total_duration(item))
        return None

    # ── internal helpers ──────────────────────────────────────────────

    def _find(self, item_id: str) -> WorkItem | None:
        for item in self._items:
            if item.id == item_id:
                return item
        return None

    @staticmethod
    def _running_session(item: WorkItem) -> WorkSession | None:
        for session in item.sessions:
            if session.stop == "":
                return session
        return None

    def _stop_now(self, item: WorkItem) -> None:
        session = self._running_session(item)
        if session is not None:
            session.stop = datetime.now().isoformat()

    def _save(self) -> None:
        self._store.save(self._items, self._day_locations)

    def _refresh_row(self, item: WorkItem) -> None:
        items = self._visible()
        if item in items:
            row = items.index(item)
            idx = self.index(row)
            self.dataChanged.emit(idx, idx)

    # ── QML-facing API ──────────────────────────────────────────────────

    @Slot(result=str)
    def addItem(self) -> str:
        """No-argument, empty-name creation — same convention TaskListModel.
        addTask() already established: the row starts in-place-editable
        (WorkItemRow.qml focuses its name field the moment itemAdded fires,
        mirroring TaskDelegate's own onTaskAdded handling), and any
        previous ADD abandoned without typing anything (click-away, no
        text ever entered) is dropped first rather than accumulating
        empty rows.

        Always goes through a full reset rather than begin/endInsertRows:
        the pruning step can itself remove a currently-visible row in the
        same call, and Qt's begin/end-InsertRows contract requires
        announcing a row count change BEFORE the data actually changes —
        incrementally signaling only the new row while a prune is also
        silently happening would violate that. A reset here is
        imperceptible either way (this is a fresh, still-empty row, not a
        mid-edit commit TaskListModel's own dataChanged-preferring
        _recompute() is protecting elsewhere).
        """
        self.beginResetModel()
        self._items = [i for i in self._items if i.name or i.deleted or i.sessions]
        item = WorkItem(name="")
        self._items.append(item)
        self.endResetModel()
        self._save()
        self.itemAdded.emit(item.id)
        return item.id

    @Slot(str, str)
    def renameItem(self, item_id: str, name: str) -> None:
        target = self._find(item_id)
        if target is None:
            return
        trimmed = name.strip()
        if trimmed == target.name:
            return
        target.name = trimmed
        self._save()
        self._refresh_row(target)

    @Slot(str)
    def startItem(self, item_id: str) -> None:
        """Starting an item auto-stops any OTHER currently-running
        session first — "up most one work entry traced at any time for
        given YATA window" (spec)."""
        target = self._find(item_id)
        if target is None or self._running_session(target) is not None:
            return
        for other in self._items:
            if other is not target:
                self._stop_now(other)
        target.sessions.append(WorkSession())
        self._save()
        self.layoutChanged.emit()  # any OTHER item's running/duration may have changed too

    @Slot(str)
    def stopItem(self, item_id: str) -> None:
        target = self._find(item_id)
        if target is None:
            return
        self._stop_now(target)
        self._save()
        self._refresh_row(target)

    @Slot(str)
    def deleteItem(self, item_id: str) -> None:
        """Soft-delete — see WorkItem.deleted's own docstring for why
        there's no restore/purge UI for this. Stops it first if it
        happens to be running, so a deleted item can never be left
        "tracking forever" in the background."""
        target = self._find(item_id)
        if target is None:
            return
        items_before = self._visible()
        row = items_before.index(target) if target in items_before else -1
        self._stop_now(target)
        if row >= 0:
            self.beginRemoveRows(QModelIndex(), row, row)
            target.deleted = True
            self.endRemoveRows()
        else:
            target.deleted = True
        self._save()

    @Slot(str, bool)
    def setNonWorking(self, item_id: str, non_working: bool) -> None:
        target = self._find(item_id)
        if target is None or target.non_working == non_working:
            return
        target.non_working = non_working
        self._save()
        self._refresh_row(target)

    @Slot(str, result="QVariant")
    def sessionsFor(self, item_id: str):
        """Every start/stop pair for one item, oldest first — backs
        SessionsDialog.qml's manual-edit list."""
        target = self._find(item_id)
        if target is None:
            return []
        return [
            {"id": s.id, "start": s.start, "stop": s.stop, "abandoned": s.abandoned}
            for s in target.sessions
        ]

    @Slot(str, str, str, str, result=bool)
    def updateSession(self, item_id: str, session_id: str, start_iso: str, stop_iso: str) -> bool:
        """Manual start/stop adjustment (spec: "Start / stop timestamps
        can be adjusted manually") — clears `abandoned` the moment a user
        touches it, per spec."""
        target = self._find(item_id)
        if target is None:
            return False
        for session in target.sessions:
            if session.id == session_id:
                session.start = start_iso
                session.stop = stop_iso
                session.abandoned = False
                self._save()
                self._refresh_row(target)
                return True
        return False

    @Slot(str, str)
    def setDayLocation(self, day_iso: str, location: str) -> None:
        if location not in ("on-site", "remote"):
            return
        self._day_locations[day_iso] = location
        self._save()

    @Slot(str, result=str)
    def dayLocation(self, day_iso: str) -> str:
        return self._day_locations.get(day_iso, "")

    @Slot(str, str, "QVariant", float, result="QVariant")
    def summary(self, period: str, reference_iso_date: str, holiday_dates, daily_hours: float):
        reference = date.fromisoformat(reference_iso_date)
        return compute_summary(
            self._items, period, reference, dict(_unwrap(holiday_dates)), daily_hours, self._day_locations,
        )

    @Slot(str, str, str, "QVariant", float, "QVariant", result=bool)
    def exportPdf(self, path: str, period: str, reference_iso_date: str, holiday_dates, daily_hours: float, options):
        """options: {customerName, customerAddress, contractorName,
        includeCustomer, includeContractor, includeSignatures} — a QML
        object literal, unwrapped the same "may arrive as a dict already,
        or need dict(...)" way every other QVariant-typed slot in this
        codebase already handles. Returns False (instead of raising) on
        any failure (e.g. an unwritable path) so PdfExportDialog.qml can
        show an error instead of crashing the window."""
        reference = date.fromisoformat(reference_iso_date)
        summary = compute_summary(
            self._items, period, reference, dict(_unwrap(holiday_dates)), daily_hours, self._day_locations,
        )
        options = dict(_unwrap(options))
        html = pdf_export.build_html(
            summary,
            customer_name=options.get("customerName", ""),
            customer_address=options.get("customerAddress", ""),
            contractor_name=options.get("contractorName", ""),
            include_customer=bool(options.get("includeCustomer", True)),
            include_contractor=bool(options.get("includeContractor", True)),
            include_signatures=bool(options.get("includeSignatures", True)),
        )
        try:
            pdf_export.export_pdf(path, html)
        except OSError:
            return False
        return True

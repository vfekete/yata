from __future__ import annotations

from datetime import date, datetime, timedelta

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt, Signal, Slot

from qml_interop import unwrap_qvariant

from . import pdf_export
from .storage import TimesheetStore, WorkItem, WorkSession

_ID, _NAME, _NON_WORKING, _RUNNING, _DURATION_LABEL, _ABANDONED = (Qt.UserRole + i for i in range(1, 7))


def _parse(iso: str) -> datetime:
    return datetime.fromisoformat(iso)


def session_duration_by_day(session: WorkSession) -> dict:
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
    total_seconds = int(max(total.total_seconds(), 0))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}"


def _period_bounds(period: str, reference: date) -> tuple[date, date]:
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
    searchTextChanged = Signal()

    def __init__(self, store: TimesheetStore, parent=None):
        super().__init__(parent)
        self._store = store
        self._items, self._day_locations = store.load()
        self._search = ""
        self._visible: list[WorkItem] = []
        self._recompute()

    def _matches_search(self, item: WorkItem) -> bool:
        if not self._search:
            return True
        return self._search.lower() in item.name.lower()

    def _recompute(self) -> None:
        old_ids = [i.id for i in self._visible]
        new_visible = [i for i in self._items if not i.deleted and self._matches_search(i)]
        new_ids = [i.id for i in new_visible]
        if new_ids == old_ids:
            self._visible = new_visible
            if new_visible:
                self.dataChanged.emit(self.index(0), self.index(len(new_visible) - 1))
        else:
            self.beginResetModel()
            self._visible = new_visible
            self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._visible)

    def roleNames(self):
        return {
            _ID: b"itemId",
            _NAME: b"name",
            _NON_WORKING: b"nonWorking",
            _RUNNING: b"running",
            _DURATION_LABEL: b"durationLabel",
            _ABANDONED: b"hasAbandonedSession",
        }

    def _total_duration(self, item: WorkItem) -> timedelta:
        total = timedelta()
        for session in item.sessions:
            for day_total in session_duration_by_day(session).values():
                total += day_total
        return total

    def data(self, index, role):
        if not index.isValid() or not (0 <= index.row() < len(self._visible)):
            return None
        item = self._visible[index.row()]
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
        if role == _ABANDONED:
            return any(s.abandoned for s in item.sessions)
        return None

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
        if item in self._visible:
            row = self._visible.index(item)
            idx = self.index(row)
            self.dataChanged.emit(idx, idx)

    @Slot(result=str)
    def getSearchText(self) -> str:
        return self._search

    @Slot(str)
    def setSearchText(self, text: str) -> None:
        if text == self._search:
            return
        self._search = text
        self._recompute()
        self.searchTextChanged.emit()

    @Slot(result=str)
    def addItem(self) -> str:
        self._items = [i for i in self._items if i.name or i.deleted or i.sessions]
        item = WorkItem(name="")
        self._items.append(item)
        self._recompute()
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
        self._recompute()

    @Slot(str)
    def startItem(self, item_id: str) -> None:
        target = self._find(item_id)
        if target is None or self._running_session(target) is not None:
            return
        for other in self._items:
            if other is not target:
                self._stop_now(other)
        target.sessions.append(WorkSession())
        self._save()
        if self._visible:
            self.dataChanged.emit(self.index(0), self.index(len(self._visible) - 1))

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
        target = self._find(item_id)
        if target is None:
            return
        self._stop_now(target)
        target.deleted = True
        self._save()
        self._recompute()

    @Slot(str, bool)
    def setNonWorking(self, item_id: str, non_working: bool) -> None:
        target = self._find(item_id)
        if target is None or target.non_working == non_working:
            return
        target.non_working = non_working
        self._save()
        self._refresh_row(target)

    @Slot(str, result=str)
    def liveDurationLabel(self, item_id: str) -> str:
        target = self._find(item_id)
        if target is None:
            return format_duration(timedelta())
        total = self._total_duration(target)
        running = self._running_session(target)
        if running is not None:
            total += datetime.now() - _parse(running.start)
        return format_duration(total)

    @Slot(str, result="QVariant")
    def sessionsFor(self, item_id: str):
        target = self._find(item_id)
        if target is None:
            return []
        return [
            {"id": s.id, "start": s.start, "stop": s.stop, "abandoned": s.abandoned}
            for s in target.sessions
        ]

    @Slot(str, str, str, str, result=bool)
    def updateSession(self, item_id: str, session_id: str, start_iso: str, stop_iso: str) -> bool:
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
            self._items, period, reference, dict(unwrap_qvariant(holiday_dates)), daily_hours, self._day_locations,
        )

    @Slot(str, str, str, "QVariant", float, "QVariant", result=bool)
    def exportPdf(self, path: str, period: str, reference_iso_date: str, holiday_dates, daily_hours: float, options):
        try:
            reference = date.fromisoformat(reference_iso_date)
            summary = compute_summary(
                self._items, period, reference, dict(unwrap_qvariant(holiday_dates)), daily_hours, self._day_locations,
            )
            options = dict(unwrap_qvariant(options))
            html = pdf_export.build_html(
                summary,
                customer_name=options.get("customerName", ""),
                customer_address=options.get("customerAddress", ""),
                contractor_name=options.get("contractorName", ""),
                include_customer=bool(options.get("includeCustomer", True)),
                include_contractor=bool(options.get("includeContractor", True)),
                include_signatures=bool(options.get("includeSignatures", True)),
            )
            pdf_export.export_pdf(path, html)
        except Exception:
            import traceback  # noqa: PLC0415
            traceback.print_exc()
            return False
        return True

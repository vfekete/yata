"""Undoes window geometry that Qt rewrites on its own when the scale changes.

When the device pixel ratio changes under a live window (e.g. GNOME
publishing the real X11 scale only after YATA has started), Qt keeps the
native window where it is and re-expresses its geometry in the new logical
units -- halved when going from 1 to 2. AppSettings saves every geometry
change immediately (deliberately: nothing may be lost on a crash), so
those bogus values hit the disk at once. The guard doesn't delay saving;
it rolls back afterwards: on a DPR change that wasn't caused by the window
moving to another screen, it restores the geometry from just before the
writes around that change (saved immediately again) and re-applies it.
"""
from __future__ import annotations

import time
from typing import Callable

from PySide6.QtCore import QEvent, QObject, QRect, QTimer

# Writes this long before the DPR-change event still count as caused by it:
# the order in which Qt delivers the geometry change vs. the event isn't
# guaranteed.
ROLLBACK_WINDOW = 1.0
# Give Qt/the window manager a moment to deliver every geometry change the
# scale switch causes before correcting.
CORRECTION_DELAY_MS = 250


class GeometryHistory:
    """Recent (time, geometry-before-write) pairs for one window."""

    def __init__(self, max_age: float = 10.0):
        self._entries: list[tuple[float, tuple[int, int, int, int]]] = []
        self._max_age = max_age

    def record(self, now: float, previous: tuple[int, int, int, int]) -> None:
        self._entries.append((now, previous))
        self._entries = [e for e in self._entries if now - e[0] <= self._max_age]

    def rollback_target(self, since: float) -> tuple[int, int, int, int] | None:
        """Geometry from before the earliest write at or after `since`."""
        for when, previous in self._entries:
            if when >= since:
                return previous
        return None

    def clear(self) -> None:
        self._entries.clear()


class ScaleChangeGuard(QObject):
    def __init__(
        self,
        window,
        settings,
        *,
        dpr_source: Callable[[], float] | None = None,
        screen_source: Callable[[], object] | None = None,
        clock: Callable[[], float] = time.monotonic,
        parent=None,
    ):
        super().__init__(parent)
        self._window = window
        self._settings = settings
        self._dpr_source = dpr_source or window.devicePixelRatio
        self._screen_source = screen_source or (
            lambda: window.screen().name() if window.screen() else None
        )
        self._clock = clock
        self._history = GeometryHistory()
        self._dpr = self._dpr_source()
        self._screen = self._screen_source()
        self._event_time: float | None = None
        self.corrections = 0

        settings.add_geometry_listener(self._on_geometry_written)
        # Two independent notifications, whichever Qt delivers: the
        # per-window event, and the screen's logical DPI change (what an
        # Xft.dpi change turns into on xcb).
        window.installEventFilter(self)
        self._watched_screen = None
        if hasattr(window, "screenChanged"):
            window.screenChanged.connect(self._watch_screen)
            self._watch_screen(window.screen())

    def _watch_screen(self, screen) -> None:
        if self._watched_screen is not None:
            try:
                self._watched_screen.logicalDotsPerInchChanged.disconnect(self._on_dpi_changed)
            except (RuntimeError, TypeError):
                pass
        self._watched_screen = screen
        if screen is not None:
            screen.logicalDotsPerInchChanged.connect(self._on_dpi_changed)

    def _on_dpi_changed(self, *_args) -> None:
        self.scale_changed()

    def eventFilter(self, obj, event):
        if obj is self._window and event.type() == QEvent.Type.DevicePixelRatioChange:
            self.scale_changed()
        return False

    def _on_geometry_written(self, previous) -> None:
        self._history.record(self._clock(), previous)

    def scale_changed(self) -> None:
        if self._event_time is None:
            self._event_time = self._clock()
            QTimer.singleShot(CORRECTION_DELAY_MS, self.correct)

    def correct(self) -> None:
        event_time, self._event_time = self._event_time, None
        dpr, screen = self._dpr_source(), self._screen_source()
        old_dpr, old_screen = self._dpr, self._screen
        self._dpr, self._screen = dpr, screen
        if event_time is None or dpr == old_dpr or screen != old_screen:
            # No real change, or the window moved to a monitor with another
            # scale -- a genuine geometry change, keep it.
            return
        target = self._history.rollback_target(event_time - ROLLBACK_WINDOW)
        self._history.clear()
        if target is None:
            return
        self.corrections += 1
        self._settings.restore_geometry(*target)
        self._window.setGeometry(QRect(*target))

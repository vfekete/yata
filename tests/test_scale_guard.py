from PySide6.QtCore import QEvent, QSettings
from PySide6.QtGui import QWindow

from scale_guard import GeometryHistory, ScaleChangeGuard
from settings import AppSettings


def ini_settings(tmp_path, name="settings.ini"):
    return QSettings(str(tmp_path / name), QSettings.IniFormat)


class FakeClock:
    def __init__(self):
        self.now = 100.0

    def __call__(self):
        return self.now


def _saved_geometry(tmp_path):
    s = ini_settings(tmp_path)
    return tuple(int(s.value(f"window/{k}")) for k in ("x", "y", "width", "height"))


def _make(tmp_path, geometry=(3041, 342, 712, 306)):
    settings = AppSettings(settings=ini_settings(tmp_path))
    settings.restore_geometry(*geometry)
    window = QWindow()
    state = {"dpr": 1.0, "screen": "DP-2"}
    clock = FakeClock()
    guard = ScaleChangeGuard(
        window, settings,
        dpr_source=lambda: state["dpr"], screen_source=lambda: state["screen"], clock=clock,
    )
    return settings, window, state, clock, guard


def _qt_halves_geometry(settings, clock):
    # What Qt does when the DPR flips 1 -> 2 under a live window: the same
    # native window re-expressed in new logical units, each write saved
    # immediately by AppSettings.
    clock.now += 0.1
    settings.x = settings.x // 2
    settings.y = settings.y // 2
    settings.width = settings.width // 2
    settings.height = settings.height // 2


def test_history_rollback_target_is_state_before_first_recent_write():
    h = GeometryHistory()
    h.record(1.0, (1, 1, 1, 1))
    h.record(5.0, (2, 2, 2, 2))
    h.record(5.1, (3, 3, 3, 3))
    assert h.rollback_target(4.0) == (2, 2, 2, 2)
    assert h.rollback_target(6.0) is None


def test_scale_flip_rolls_back_halved_geometry_on_disk_and_window(tmp_path):
    # Regression (2026-10-10, 2026-10-18): Qt started at DPR 1, the scale
    # flipped to 2, and every window was saved at half its geometry.
    settings, window, state, clock, guard = _make(tmp_path)
    clock.now += 30
    _qt_halves_geometry(settings, clock)
    assert _saved_geometry(tmp_path) == (1520, 171, 356, 153)

    state["dpr"] = 2.0
    guard.scale_changed()
    clock.now += 0.25
    guard.correct()

    assert (settings.x, settings.y, settings.width, settings.height) == (3041, 342, 712, 306)
    assert _saved_geometry(tmp_path) == (3041, 342, 712, 306)
    g = window.geometry()
    assert (g.x(), g.y(), g.width(), g.height()) == (3041, 342, 712, 306)
    assert guard.corrections == 1


def test_writes_before_the_flip_event_are_also_rolled_back(tmp_path):
    # Qt may deliver the geometry change before the DPR-change notification.
    settings, window, state, clock, guard = _make(tmp_path)
    clock.now += 30
    _qt_halves_geometry(settings, clock)
    clock.now += 0.5
    state["dpr"] = 2.0
    guard.scale_changed()
    guard.correct()
    assert _saved_geometry(tmp_path) == (3041, 342, 712, 306)


def test_user_moves_long_before_the_flip_are_kept(tmp_path):
    settings, window, state, clock, guard = _make(tmp_path)
    clock.now += 30
    settings.x = 3100  # genuine user move, saved immediately
    clock.now += 30
    state["dpr"] = 2.0
    guard.scale_changed()
    guard.correct()
    assert guard.corrections == 0
    assert _saved_geometry(tmp_path)[0] == 3100


def test_moving_to_a_screen_with_another_scale_is_not_rolled_back(tmp_path):
    settings, window, state, clock, guard = _make(tmp_path)
    clock.now += 30
    settings.x = 8300
    state["dpr"] = 2.0
    state["screen"] = "HDMI-1"
    guard.scale_changed()
    guard.correct()
    assert guard.corrections == 0
    assert _saved_geometry(tmp_path)[0] == 8300


def test_no_rollback_when_dpr_did_not_actually_change(tmp_path):
    settings, window, state, clock, guard = _make(tmp_path)
    clock.now += 30
    _qt_halves_geometry(settings, clock)
    guard.scale_changed()
    guard.correct()
    assert guard.corrections == 0


def test_dpr_change_event_on_window_triggers_guard(tmp_path):
    settings, window, state, clock, guard = _make(tmp_path)
    assert guard._event_time is None
    guard.eventFilter(window, QEvent(QEvent.Type.DevicePixelRatioChange))
    assert guard._event_time is not None


def test_restore_geometry_saves_once_and_notifies_previous(tmp_path):
    settings = AppSettings(settings=ini_settings(tmp_path))
    settings.restore_geometry(10, 20, 300, 400)
    seen = []
    settings.add_geometry_listener(seen.append)
    settings.restore_geometry(11, 21, 301, 401)
    assert seen == [(10, 20, 300, 400)]
    assert _saved_geometry(tmp_path) == (11, 21, 301, 401)
    settings.restore_geometry(11, 21, 301, 401)
    assert len(seen) == 1


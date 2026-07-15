from PySide6.QtGui import QWindow

from x11_stacking import enable_always_below


def test_enable_always_below_is_noop_off_x11(qt_app):
    # Tests run under QT_QPA_PLATFORM=offscreen (see conftest.py), so
    # platformName() is "offscreen", not "xcb" -- enable_always_below must
    # return immediately without touching X11 (there is no real X server
    # here, so any attempt would raise).
    window = QWindow()
    enable_always_below(window)

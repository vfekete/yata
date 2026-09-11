from PySide6.QtGui import QWindow

from x11_stacking import enable_always_below


def test_enable_always_below_is_noop_off_x11(qt_app):
    window = QWindow()
    enable_always_below(window)

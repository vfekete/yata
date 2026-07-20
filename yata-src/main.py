"""YATA entry point."""
import os
import signal
import sys

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QFontDatabase, QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

import resources_rc  # noqa: F401 — registers :/fonts/VT323-Regular.ttf with Qt
from models import TaskListModel
from settings import AppSettings
from storage import TaskStore
from x11_stacking import enable_always_below

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")


def main() -> int:
    # Must be set before QGuiApplication is constructed. PassThrough keeps
    # pixel sizes matching each monitor's actual reported scale factor
    # (rather than rounding to the nearest integer), so the app looks the
    # same size across differently-scaled monitors.
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QGuiApplication(sys.argv)
    app.setOrganizationName("yata")
    app.setApplicationName("yata")
    QQuickStyle.setStyle("Basic")

    QFontDatabase.addApplicationFont(":/fonts/VT323-Regular.ttf")

    task_model = TaskListModel(TaskStore())
    app_settings = AppSettings()

    engine = QQmlApplicationEngine()
    engine.addImportPath(QML_DIR)
    engine.rootContext().setContextProperty("taskModel", task_model)
    engine.rootContext().setContextProperty("appSettings", app_settings)
    engine.load(os.path.join(QML_DIR, "Main.qml"))

    if not engine.rootObjects():
        return 1

    window = engine.rootObjects()[0]
    # Deferred so the platform window is actually mapped by the time we
    # send the EWMH client message (winId()/send_event too early can be
    # ignored by the window manager).
    QTimer.singleShot(0, lambda: enable_always_below(window))

    # Qt's event loop runs entirely in C++ and never hands control back to
    # the Python interpreter, so Python's own SIGINT handler (installed
    # below) would otherwise never actually run when Ctrl+C is pressed.
    # This timer's only job is to wake the interpreter up periodically so a
    # pending signal gets delivered.
    signal.signal(signal.SIGINT, lambda *_: app.quit())
    interrupt_pump = QTimer()
    interrupt_pump.timeout.connect(lambda: None)
    interrupt_pump.start(200)

    exit_code = app.exec()

    # Explicitly tear down the QML engine (and everything it owns: windows,
    # bindings, the Theme singleton) now, while task_model/app_settings are
    # still alive. Without this, Python's own cleanup at function return can
    # collect task_model/app_settings first, and the QML engine's teardown
    # then trips over bindings reading now-dead context properties, printing
    # "TypeError: Cannot read property ... of null" on quit.
    del engine

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

"""YATA entry point."""
import os
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, Qt, QTimer
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle

import resources_rc  # noqa: F401 — registers :/fonts/VT323-Regular.ttf and :/icon/icon.png
from models import TaskListModel
from settings import AppSettings
from storage import TaskStore
from x11_stacking import enable_always_below

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
APP_VERSION = "0.9.30"


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def _compute_exec_cmd() -> str:
    """Return the command for the .desktop Exec= field.

    For a source checkout this is run.sh (sits two dirs up from this file).
    For a compiled standalone binary run.sh doesn't exist next to __file__, so
    we fall back to the binary itself, resolved via PATH if needed.
    """
    run_sh = Path(__file__).parent.parent / "run.sh"
    if run_sh.is_file():
        return str(run_sh)
    import shutil
    cmd = sys.argv[0]
    if not os.path.isabs(cmd):
        cmd = shutil.which(cmd) or os.path.abspath(cmd)
    return str(Path(cmd).resolve())


def _ensure_desktop_entry(
    app_version: str,
    *,
    home: Path | None = None,
    exec_cmd: str | None = None,
) -> None:
    """Install or update the XDG .desktop entry when missing or stale.

    Skips only when both the installed version is current-or-newer AND the
    Exec= path matches — so switching from run.sh to a compiled binary (or
    moving the binary) triggers a re-install automatically.
    """
    import subprocess

    if home is None:
        home = Path.home()
    if exec_cmd is None:
        exec_cmd = _compute_exec_cmd()

    desktop_path = home / ".local/share/applications/yata.desktop"
    icon_dir = home / ".local/share/icons/hicolor/256x256/apps"
    icon_path = icon_dir / "yata.png"

    installed_version: str | None = None
    installed_exec: str | None = None
    if desktop_path.exists():
        for line in desktop_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("X-AppVersion="):
                installed_version = line.split("=", 1)[1].strip()
            elif line.startswith("Exec="):
                installed_exec = line.split("=", 1)[1].strip()

    version_ok = (
        installed_version is not None
        and _version_tuple(installed_version) >= _version_tuple(app_version)
    )
    if version_ok and installed_exec == exec_cmd:
        return

    icon_dir.mkdir(parents=True, exist_ok=True)
    qf = QFile(":/icon/icon.png")
    if qf.open(QIODevice.OpenModeFlag.ReadOnly):
        icon_path.write_bytes(bytes(qf.readAll()))
        qf.close()

    desktop_path.parent.mkdir(parents=True, exist_ok=True)
    desktop_path.write_text(
        "[Desktop Entry]\n"
        "Name=YATA\n"
        "Comment=Yet Another Todo Application — a minimal always-on-desktop task list\n"
        "Type=Application\n"
        "Categories=Utility;\n"
        f"Exec={exec_cmd}\n"
        "StartupWMClass=yata\n"
        "Icon=yata\n"
        "NoDisplay=false\n"
        f"X-AppVersion={app_version}\n",
        encoding="utf-8",
    )

    subprocess.run(
        ["gtk-update-icon-cache", "-f", "-t", str(icon_dir.parent.parent)],
        check=False, capture_output=True,
    )
    subprocess.run(
        ["update-desktop-database", str(desktop_path.parent)],
        check=False, capture_output=True,
    )


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
    app.setWindowIcon(QIcon(":/icon/icon.png"))
    _ensure_desktop_entry(APP_VERSION)
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
    app_icon = QIcon(":/icon/icon.png")
    # Deferred so the platform window is actually mapped before we touch WM
    # properties. enable_always_below sends _NET_WM_STATE_BELOW; setIcon
    # writes _NET_WM_ICON so GNOME's Alt+Tab switcher picks up the icon.

    def _setup_window():
        enable_always_below(window)
        window.setIcon(app_icon)
    QTimer.singleShot(0, _setup_window)

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

"""YATA entry point."""
import os
import signal
import sys
from pathlib import Path

from PySide6.QtCore import QFile, QIODevice, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlContext, QQmlEngine
from PySide6.QtQuickControls2 import QQuickStyle

import resources_rc  # noqa: F401 — registers :/fonts/VT323-Regular.ttf and :/icon/icon.png
from icons import IconProvider
from models import TaskListModel
from settings import AppSettings
from storage import TaskStore
from window_manager import WindowManager
from window_registry import (
    DEFAULT_TAG,
    WindowRegistry,
    settings_path_for,
    tasks_path_for,
)
from x11_stacking import enable_always_below

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
APP_VERSION = "0.9.31"


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

    version_ok = (installed_version is not None and
                  _version_tuple(installed_version) >= _version_tuple(app_version))
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


def _make_window(engine, icon_provider, window_manager, app_icon, window_id, task_store, app_settings):
    """Builds one fully independent window: its own QQmlContext with its own
    taskModel/appSettings/Theme (see window_manager.py's module docstring
    and ThemeImpl.qml's own comment for why Theme can no longer be a
    pragma-Singleton once multiple windows exist in one engine, and why that
    file specifically isn't named Theme.qml). Used for both the very first
    window and every window created later via YATAS.
    """
    task_model = TaskListModel(task_store)

    context = QQmlContext(engine.rootContext())
    context.setContextProperty("taskModel", task_model)
    context.setContextProperty("appSettings", app_settings)
    context.setContextProperty("iconProvider", icon_provider)
    context.setContextProperty("windowManager", window_manager)
    context.setContextProperty("windowId", window_id)

    # Theme must be created (and set as a context property) before Main.qml,
    # since Main.qml's whole tree references the bare "Theme" identifier
    # from the moment it's constructed.
    #
    # IMPORTANT: the QQmlComponent objects themselves (theme_component,
    # main_component below) must stay alive for as long as the objects they
    # created (theme, window) are in use — not just the QQmlContext, and not
    # just the created object with CppOwnership set. Empirically confirmed
    # (via a minimal reproduction outside this codebase) that letting a
    # QQmlComponent get Python-garbage-collected after create() tears down
    # the object it created too, surfacing as "libshiboken: Internal C++
    # object (QQuickWindow) already deleted" the next time anything touches
    # it — even with the context and the created object both still
    # referenced elsewhere. register_window() below is what keeps every one
    # of these alive for the window's whole lifetime.
    theme_component = QQmlComponent(engine, QUrl.fromLocalFile(os.path.join(QML_DIR, "ThemeImpl.qml")))
    theme = theme_component.create(context)
    if theme is None:
        raise RuntimeError(f"ThemeImpl.qml failed to load: {theme_component.errorString()}")
    QQmlEngine.setObjectOwnership(theme, QQmlEngine.CppOwnership)
    context.setContextProperty("Theme", theme)

    main_component = QQmlComponent(engine, QUrl.fromLocalFile(os.path.join(QML_DIR, "Main.qml")))
    window = main_component.create(context)
    if window is None:
        raise RuntimeError(f"Main.qml failed to load: {main_component.errorString()}")
    QQmlEngine.setObjectOwnership(window, QQmlEngine.CppOwnership)

    # Deferred so the platform window is actually mapped before we touch WM
    # properties. enable_always_below sends _NET_WM_STATE_BELOW; setIcon
    # writes _NET_WM_ICON so GNOME's Alt+Tab switcher picks up the icon.
    def _setup_window():
        enable_always_below(window)
        window.setIcon(app_icon)
    QTimer.singleShot(0, _setup_window)

    # register_window keeps Python references to everything above alive for
    # the window's lifetime (nothing else holds them — see the comment above
    # theme_component for why theme_component/main_component specifically
    # must be included, not just context/theme/window) and lets
    # WindowManager close this window again from deleteWindow(), including
    # when it's the window that requested its own deletion.
    window_manager.register_window(
        window_id, window,
        task_model=task_model, app_settings=app_settings, context=context, theme=theme,
        theme_component=theme_component, main_component=main_component,
    )
    return window


def _make_drag_ghost(engine):
    """Builds the single, app-wide floating drag preview (DragGhost.qml) —
    an independent top-level window, not parented under any one YATA
    window's own context, since it isn't owned by any window in particular
    (see that file's own comment on why it's deliberately theme-independent
    for the same reason). Kept alive for the app's whole lifetime by main()
    holding onto both return values, same reasoning as _make_window's own
    theme_component/main_component comment.
    """
    component = QQmlComponent(engine, QUrl.fromLocalFile(os.path.join(QML_DIR, "DragGhost.qml")))
    ghost = component.create()
    if ghost is None:
        raise RuntimeError(f"DragGhost.qml failed to load: {component.errorString()}")
    QQmlEngine.setObjectOwnership(ghost, QQmlEngine.CppOwnership)
    return ghost, component


def _open_settings(window_id: str) -> QSettings:
    path = settings_path_for(window_id)
    return QSettings(path, QSettings.IniFormat) if path else QSettings("yata", "yata")


def _windows_to_restore(registry: WindowRegistry) -> list[dict]:
    """Every window to (re)open at startup.

    Every non-deleted registry entry marked "open" gets reopened — not just
    the default window — so a window created via YATAS is still there next
    time the app starts, at its own persisted position/theme/content. One
    marked closed (via YatasView's SHOW toggle) stays closed across a
    restart, same as the user left it. A soft-deleted one (YatasView's
    DELETED category — see WindowManager.deleteWindow) never gets restored
    here regardless of its "open" field — it stays hidden until explicitly
    recreated or purged.

    Falls back to seeding a fresh default entry if there are no non-deleted
    entries at all (the registry is completely empty, or the user soft-
    deleted every window including "default"), and falls back to reopening
    every non-deleted entry if none of them are marked open (the user closed
    every window individually) — either way, the app never launches with
    nothing to show and no way to reach YATAS again.
    """
    def live(entries: list[dict]) -> list[dict]:
        return [e for e in entries if not e.get("deleted", False)]

    entries = live(registry.list())
    if not entries:
        registry.add(DEFAULT_TAG)
        entries = live(registry.list())
    open_entries = [e for e in entries if e.get("open", True)]
    if not open_entries:
        for e in entries:
            registry.set_open(e["id"], True)
        open_entries = live(registry.list())
    return open_entries


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

    icon_provider = IconProvider()
    app_icon = QIcon(":/icon/icon.png")

    engine = QQmlApplicationEngine()
    engine.addImportPath(QML_DIR)

    registry = WindowRegistry()

    def window_factory(window_id, caller_state):
        # Used for windows created via the YATAS view's ADD button — clones
        # the creating window's theme (explicit requirement: "new window has
        # same theme as the actual window") and a non-overlapping position
        # WindowManager already computed into caller_state's x/y.
        task_store = TaskStore(tasks_path_for(window_id))
        app_settings = AppSettings(_open_settings(window_id))
        app_settings.themeMode = caller_state["themeMode"]
        app_settings.themeTint = caller_state["themeTint"]
        app_settings.opacityPercent = int(caller_state["opacityPercent"])
        app_settings.fontScale = float(caller_state["fontScale"])
        app_settings.wheelZoomInverted = bool(caller_state["wheelZoomInverted"])
        app_settings.width = int(caller_state["width"])
        app_settings.height = int(caller_state["height"])
        app_settings.x = int(caller_state["x"])
        app_settings.y = int(caller_state["y"])
        return _make_window(
            engine, icon_provider, window_manager, app_icon,
            window_id, task_store, app_settings,
        )

    def restore_factory(window_id):
        # No theme/geometry cloning here (that's only for windows created
        # live via YATAS, in window_factory above) — a restored window
        # already has its own persisted position/theme/content. Used both
        # for every window at startup and for WindowManager.openWindow()
        # (YatasView's SHOW toggle, on) reopening one later in the session.
        task_store = TaskStore(tasks_path_for(window_id))
        app_settings = AppSettings(_open_settings(window_id))
        _make_window(
            engine, icon_provider, window_manager, app_icon,
            window_id, task_store, app_settings,
        )

    drag_ghost, drag_ghost_component = _make_drag_ghost(engine)
    window_manager = WindowManager(registry, window_factory, restore_factory, drag_ghost=drag_ghost)

    try:
        for entry in _windows_to_restore(registry):
            restore_factory(entry["id"])
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

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
    # bindings, every window's Theme instance) now, while window_manager
    # (and the task_model/app_settings/... it's keeping alive for every
    # window) is still alive. Without this, Python's own cleanup at function
    # return can collect those first, and the QML engine's teardown then
    # trips over bindings reading now-dead context properties, printing
    # "TypeError: Cannot read property ... of null" on quit.
    del engine

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

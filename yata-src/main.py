import argparse
import builtins
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PySide6.QtCore import QFile, QIODevice, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlContext, QQmlEngine
from PySide6.QtQuickControls2 import QQuickStyle

import resources_rc  # noqa: F401
import plugins_registry
from icons import IconProvider
from settings import AppSettings
from window_manager import WindowManager
from window_registry import (
    DEFAULT_TAG,
    WindowRegistry,
    config_dir,
    data_dir,
    instance_dir_for,
    settings_path_for,
)
from x11_stacking import enable_always_below

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
APP_VERSION = "0.49.1"

_IS_COMPILED = "__compiled__" in globals()


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def _compute_exec_cmd(*, source_dir: Path | None = None) -> str:
    source_dir = source_dir or Path(__file__).parent
    run_sh = source_dir.parent / "run.sh"
    if run_sh.is_file():
        return str(run_sh)
    import shutil
    cmd = sys.argv[0]
    if not os.path.isabs(cmd):
        cmd = shutil.which(cmd) or os.path.abspath(cmd)
    return str(Path(cmd).resolve())


def _maybe_launch_bundled_loader() -> None:
    if not _IS_COMPILED or os.environ.get("YATA_LOADER_SOCKET"):
        return
    binary_dir = getattr(builtins, "__nuitka_binary_dir", None)
    if not binary_dir:
        return
    loader_binary = Path(binary_dir) / "x-loader-loader"
    if not loader_binary.is_file():
        return
    os.chmod(loader_binary, 0o755)
    socket_path = tempfile.mktemp(
        dir=os.environ.get("XDG_RUNTIME_DIR") or tempfile.gettempdir(),
        prefix="yata-loader-", suffix=".sock",
    )
    try:
        subprocess.Popen(
            [str(loader_binary)],
            env={**os.environ, "YATA_LOADER_SOCKET": socket_path},
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
        )
    except OSError:
        return
    os.environ["YATA_LOADER_SOCKET"] = socket_path


def _ensure_desktop_entry(
    app_version: str,
    *,
    home: Path | None = None,
    exec_cmd: str | None = None,
) -> None:
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


def _make_window(engine, icon_provider, window_manager, app_icon, window_id, plugin_content, host_settings):
    context = QQmlContext(engine.rootContext())
    for name, obj in plugin_content.context_properties.items():
        context.setContextProperty(name, obj)
    context.setContextProperty("hostSettings", host_settings)
    context.setContextProperty("iconProvider", icon_provider)
    context.setContextProperty("windowManager", window_manager)
    context.setContextProperty("windowId", window_id)

    theme_component = QQmlComponent(engine, QUrl.fromLocalFile(plugin_content.theme_qml_source))
    theme = theme_component.create(context)
    if theme is None:
        raise RuntimeError(f"{plugin_content.theme_qml_source} failed to load: {theme_component.errorString()}")
    QQmlEngine.setObjectOwnership(theme, QQmlEngine.CppOwnership)
    context.setContextProperty("Theme", theme)

    context.setContextProperty("pluginContentUrl", QUrl.fromLocalFile(plugin_content.qml_source))

    main_component = QQmlComponent(engine, QUrl.fromLocalFile(os.path.join(QML_DIR, "Main.qml")))
    window = main_component.create(context)
    if window is None:
        raise RuntimeError(f"Main.qml failed to load: {main_component.errorString()}")
    QQmlEngine.setObjectOwnership(window, QQmlEngine.CppOwnership)

    if plugin_content.on_lock_state_changed:
        host_settings.lockStateChanged.connect(
            lambda: plugin_content.on_lock_state_changed(host_settings.lockState)
        )
    if plugin_content.on_window_closing:
        window.visibleChanged.connect(
            lambda visible: (not visible) and plugin_content.on_window_closing()
        )

    def _setup_window():
        enable_always_below(window)
        window.setIcon(app_icon)
    QTimer.singleShot(0, _setup_window)

    window_manager.register_window(
        window_id, window,
        task_model=plugin_content.context_properties.get("taskModel"),
        app_settings=host_settings, context=context, theme=theme,
        theme_component=theme_component, main_component=main_component,
        plugin_content=plugin_content,
    )
    return window


def _make_drag_ghost(engine):
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


def _unique_backup_path(dest_dir: Path, stamp: str) -> Path:
    candidate = dest_dir / f"yb-{stamp}.zip"
    n = 1
    while candidate.exists():
        candidate = dest_dir / f"yb-{stamp}-{n}.zip"
        n += 1
    return candidate


def _create_backup(dest_dir: Path | None = None) -> Path:
    dest_dir = dest_dir or Path.cwd()
    stamp = datetime.now().strftime("%Y-%m-%d-%H-%M")
    dest = _unique_backup_path(dest_dir, stamp)

    with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as zf:
        for root_dir, arc_root in ((config_dir(), "config"), (data_dir(), "data")):
            root_path = Path(root_dir)
            for file_path in root_path.rglob("*"):
                if file_path.is_file():
                    zf.write(file_path, str(Path(arc_root) / file_path.relative_to(root_path)))

    return dest


def _connect_to_loader() -> socket.socket | None:
    path = os.environ.get("YATA_LOADER_SOCKET")
    if not path:
        return None
    for _ in range(50):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(path)
            return sock
        except OSError:
            sock.close()
            time.sleep(0.02)
    return None


def _send_loader_message(sock: socket.socket, message: str) -> None:
    try:
        sock.sendall((message + "\n").encode("ascii"))
    except OSError:
        pass


def main() -> int:
    parser = argparse.ArgumentParser(prog="yata", description="Yet Another Todo Application")
    parser.add_argument("-b", "--backup", action="store_true",
                         help="Back up YATA's config/data folders to a zip file and exit, without starting the app.")
    args, _ = parser.parse_known_args()
    if args.backup:
        dest = _create_backup()
        print(f"Backup written to {dest}")
        return 0

    _maybe_launch_bundled_loader()
    loader_socket = _connect_to_loader()
    if loader_socket:
        _send_loader_message(loader_socket, "starting")

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
    for plugin in plugins_registry.AVAILABLE_PLUGINS.values():
        if plugin.qml_import_dir:
            engine.addImportPath(plugin.qml_import_dir)

    registry = WindowRegistry()

    def _plugin_content_for(window_id, legacy_qsettings):
        plugin = plugins_registry.get(registry.get_plugin(window_id))
        return plugin.create_content(window_id, instance_dir_for(window_id), legacy_qsettings)

    def window_factory(window_id, caller_state):
        legacy_qsettings = _open_settings(window_id)
        app_settings = AppSettings(legacy_qsettings)
        app_settings.width = int(caller_state["width"])
        app_settings.height = int(caller_state["height"])
        app_settings.x = int(caller_state["x"])
        app_settings.y = int(caller_state["y"])
        app_settings.zoomLevel = float(caller_state["zoomLevel"])
        app_settings.wheelZoomInverted = bool(caller_state["wheelZoomInverted"])
        plugin_content = _plugin_content_for(window_id, legacy_qsettings)
        plugin_settings = plugin_content.context_properties.get("appSettings")
        if plugin_settings is not None:
            plugin_settings.themeMode = caller_state["themeMode"]
            plugin_settings.themeTint = caller_state["themeTint"]
            plugin_settings.opacityPercent = int(caller_state["opacityPercent"])
        return _make_window(
            engine, icon_provider, window_manager, app_icon,
            window_id, plugin_content, app_settings,
        )

    def restore_factory(window_id):
        legacy_qsettings = _open_settings(window_id)
        app_settings = AppSettings(legacy_qsettings)
        plugin_content = _plugin_content_for(window_id, legacy_qsettings)
        _make_window(
            engine, icon_provider, window_manager, app_icon,
            window_id, plugin_content, app_settings,
        )

    drag_ghost, drag_ghost_component = _make_drag_ghost(engine)
    window_manager = WindowManager(registry, window_factory, restore_factory, drag_ghost=drag_ghost)

    try:
        for entry in _windows_to_restore(registry):
            restore_factory(entry["id"])
    except RuntimeError as exc:
        print(exc, file=sys.stderr)
        return 1

    if loader_socket:
        app.processEvents()
        app.processEvents()
        _send_loader_message(loader_socket, "running")
        loader_socket.close()

    signal.signal(signal.SIGINT, lambda *_: app.quit())
    interrupt_pump = QTimer()
    interrupt_pump.timeout.connect(lambda: None)
    interrupt_pump.start(200)

    exit_code = app.exec()

    del engine

    return exit_code


if __name__ == "__main__":
    sys.exit(main())

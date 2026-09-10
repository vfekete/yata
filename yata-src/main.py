"""YATA entry point."""
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

# Repo root, so `plugins.simple_task_list...` (r-9.md) is importable
# alongside this file's own directory (yata-src, Python's default
# sys.path[0] for a script run directly), which every other import below
# already relies on for its own flat imports (icons, settings, ...).
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from PySide6.QtCore import QFile, QIODevice, QSettings, Qt, QTimer, QUrl
from PySide6.QtGui import QFontDatabase, QGuiApplication, QIcon
from PySide6.QtQml import QQmlApplicationEngine, QQmlComponent, QQmlContext, QQmlEngine
from PySide6.QtQuickControls2 import QQuickStyle

import resources_rc  # noqa: F401 — registers :/fonts/VT323-Regular.ttf and :/icon/icon.png
import plugins_registry
from icons import IconProvider
from settings import AppSettings
from window_manager import WindowManager
from window_registry import (
    DEFAULT_TAG,
    WindowRegistry,
    config_dir,
    data_dir,
    settings_path_for,
    tasks_path_for,
)
from x11_stacking import enable_always_below

QML_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qml")
APP_VERSION = "0.45.0"

# Nuitka injects a module-level "__compiled__" global into every compiled
# module -- this is the standard way to tell a packaged build.sh binary
# apart from `uv run python yata-src/main.py`. Read once into a plain
# module attribute (rather than checking "__compiled__" in globals() at
# call time) so tests can monkeypatch it without needing an actual Nuitka
# build.
_IS_COMPILED = "__compiled__" in globals()


def _version_tuple(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def _compute_exec_cmd(*, source_dir: Path | None = None) -> str:
    """Return the command for the .desktop Exec= field.

    For a source checkout this is run.sh (sits two dirs up from this file,
    and itself launches the startup splash in front of YATA -- see
    x-loader/ and run.sh's own comment). For a compiled standalone binary
    run.sh doesn't exist next to __file__, so we fall back to the binary
    itself, resolved via PATH if needed -- build.sh's packaged binary is
    the only thing that needs pointing at, since it launches its own
    sibling splash binary internally (see _maybe_launch_bundled_loader)
    rather than needing a separate Exec= target for it.

    source_dir defaults to this file's own directory; overridable so tests
    can exercise the "compiled binary" branch without needing a fake
    checkout where run.sh genuinely doesn't exist next to a real main.py.
    """
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
    """build.sh bundles x-loader INSIDE the packaged binary itself, as a
    Nuitka onefile data file (`--include-data-files=...=x-loader-loader`)
    rather than shipping it as a separate file next to the binary -- one
    file for a user to run, not two. Nuitka's onefile bootstrap self-
    extracts included data files into a private temp directory at startup
    and exposes that directory to the running program via a
    "__nuitka_binary_dir" name it injects into `builtins` (confirmed
    directly against Nuitka's own runtime source, not just docs --
    CompiledCodeHelpers.c seeds exactly this name for standalone/onefile
    EXE mode; empirically verified live too: a minimal onefile build with
    an included data file reported this path and the file was really
    there). Extracts (chmods it executable -- onefile extraction doesn't
    promise the source file's own exec bit survived) and launches it with
    a fresh YATA_LOADER_SOCKET, then sets that env var for this process's
    own _connect_to_loader() (called right after this) to pick up -- same
    socket protocol run.sh already uses for a source checkout, just self-
    orchestrated instead of shell-scripted.

    A no-op for `uv run python yata-src/main.py` (not compiled -- no
    "__nuitka_binary_dir" exists at all) and for run.sh's own dev-mode
    orchestration (YATA_LOADER_SOCKET already set externally in that case
    -- launching a second loader on top of it would just leave an
    orphaned extra splash window).
    """
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


def _make_window(engine, icon_provider, window_manager, app_icon, window_id, plugin_content, host_settings):
    """Builds one fully independent window: its own QQmlContext with its own
    plugin content/Theme (see window_manager.py's module docstring and
    ThemeImpl.qml's own comment for why Theme can no longer be a
    pragma-Singleton once multiple windows exist in one engine, and why
    that file specifically isn't named Theme.qml). Used for both the very
    first window and every window created later via YATAS.

    plugin_content: a plugin_api.PluginContent, built by the window's own
    plugin (see plugins_registry.py) — its context_properties (e.g.
    "taskModel", "appSettings") are set here alongside the host's own
    ("hostSettings", "windowManager", ...). host_settings: this window's
    trimmed, host-owned settings.AppSettings (geometry/borderColor/
    lockState only — see that module's own docstring for why the rest
    moved to the plugin).
    """
    context = QQmlContext(engine.rootContext())
    for name, obj in plugin_content.context_properties.items():
        context.setContextProperty(name, obj)
    context.setContextProperty("hostSettings", host_settings)
    context.setContextProperty("iconProvider", icon_provider)
    context.setContextProperty("windowManager", window_manager)
    context.setContextProperty("windowId", window_id)

    # Theme must be created (and set as a context property) before Main.qml,
    # since the plugin's whole content tree references the bare "Theme"
    # identifier from the moment it's constructed — see plugin_api.py's
    # PluginContent.theme_qml_source docstring for why this has to stay a
    # context property (loaded by the host) rather than something the
    # plugin's own qml_source file could declare locally.
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
    theme_component = QQmlComponent(engine, QUrl.fromLocalFile(plugin_content.theme_qml_source))
    theme = theme_component.create(context)
    if theme is None:
        raise RuntimeError(f"{plugin_content.theme_qml_source} failed to load: {theme_component.errorString()}")
    QQmlEngine.setObjectOwnership(theme, QQmlEngine.CppOwnership)
    context.setContextProperty("Theme", theme)

    # The plugin's own root content file, loaded by Main.qml's own
    # contentLoader (a plain QML Loader reading this context property) —
    # set before Main.qml is constructed so that Loader has a source from
    # its very first evaluation.
    context.setContextProperty("pluginContentUrl", QUrl.fromLocalFile(plugin_content.qml_source))

    main_component = QQmlComponent(engine, QUrl.fromLocalFile(os.path.join(QML_DIR, "Main.qml")))
    window = main_component.create(context)
    if window is None:
        raise RuntimeError(f"Main.qml failed to load: {main_component.errorString()}")
    QQmlEngine.setObjectOwnership(window, QQmlEngine.CppOwnership)

    # Informational-only lifecycle notifications (see PluginContent's own
    # docstring) — the plugin can't veto either transition, it just
    # optionally reacts. No-ops for a plugin that leaves either hook None
    # (true of simple_task_list today).
    if plugin_content.on_lock_state_changed:
        host_settings.lockStateChanged.connect(
            lambda: plugin_content.on_lock_state_changed(host_settings.lockState)
        )
    if plugin_content.on_window_closing:
        window.visibleChanged.connect(
            lambda visible: (not visible) and plugin_content.on_window_closing()
        )

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
        # "task_model" is simple_task_list-specific convenience access for
        # tests/tooling (e.g. scripts/capture_screenshots.py, and several
        # test fixtures reach in for direct model assertions) — as of
        # r-9.md step 5, WindowManager itself no longer depends on this
        # entry existing; moveTaskToWindow goes through plugin_content's
        # own take_item/insert_item hooks instead, which stay correct for
        # any future plugin regardless of whether it happens to expose a
        # "taskModel" context property at all.
        task_model=plugin_content.context_properties.get("taskModel"),
        app_settings=host_settings, context=context, theme=theme,
        theme_component=theme_component, main_component=main_component,
        # plugin_content itself (kept alive here for the whole window's
        # lifetime) — same "must outlive this function" reasoning as
        # theme_component/main_component above, just for a different
        # failure mode: none of its context_properties QObjects (e.g.
        # "appSettings"/TaskListSettings) has a C++ parent or CppOwnership,
        # so with no Python reference surviving past this function's own
        # return, Python's refcount-based GC deletes the *entire* underlying
        # C++ object shortly after construction — not just leaking it, but
        # leaving context.setContextProperty()'s raw pointer dangling.
        # Confirmed live: every "appSettings.*" QML binding (theme mode/
        # tint, opacity, font scale, wheel-zoom) silently read back null
        # the moment the event loop got a chance to run garbage collection.
        plugin_content=plugin_content,
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


def _unique_backup_path(dest_dir: Path, stamp: str) -> Path:
    """yb-<stamp>.zip, or yb-<stamp>-<n>.zip with the lowest n that doesn't
    already exist — so running --backup twice in the same minute (same
    stamp) never overwrites the earlier backup."""
    candidate = dest_dir / f"yb-{stamp}.zip"
    n = 1
    while candidate.exists():
        candidate = dest_dir / f"yb-{stamp}-{n}.zip"
        n += 1
    return candidate


def _create_backup(dest_dir: Path | None = None) -> Path:
    """Zips YATA's whole config and data directories (covering every
    window's settings/tasks, not just the default window's — see
    window_registry.py's per-instance paths) into dest_dir (defaults to the
    current working directory)."""
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
    """Whoever set YATA_LOADER_SOCKET (run.sh for a source checkout, or
    _maybe_launch_bundled_loader for a packaged build.sh binary) has
    already started x-loader listening on it by the time we get here, but
    this retries a little anyway (up to ~1s) in case scheduling ever put
    the connect before the accept -- run directly (run-yata.sh, or a
    packaged binary with no loader sibling) the env var is unset and this
    is a silent no-op, same rationale the old SIGUSR1 handshake used. Never
    raises: a splash that fails to connect just never hears 'running' and
    times out on its own (see x-loader/main.c)."""
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
    # add_help=True (the default) gives us -h/--help for free: argparse's
    # own help action prints usage and calls sys.exit(0) immediately during
    # parse_known_args() below, before any Qt setup runs, so `-h` never
    # starts the app — same as --backup.
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
    for plugin in plugins_registry.AVAILABLE_PLUGINS.values():
        if plugin.qml_import_dir:
            engine.addImportPath(plugin.qml_import_dir)

    registry = WindowRegistry()

    def _plugin_content_for(window_id, legacy_qsettings):
        # legacy_qsettings: the window's own raw per-window QSettings (also
        # what AppSettings itself wraps) — passed through unchanged so the
        # plugin's own settings object can migrate its old theme/* keys off
        # of it once, the first time this window's plugin-state file is
        # created (see TaskListSettings). Not otherwise touched here; the
        # plugin owns whatever it does with it.
        plugin = plugins_registry.get(registry.get_plugin(window_id))
        return plugin.create_content(window_id, tasks_path_for(window_id), legacy_qsettings)

    def window_factory(window_id, caller_state):
        # Used for windows created via the YATAS view's ADD button — clones
        # the creating window's theme (explicit requirement: "new window has
        # same theme as the actual window") and a non-overlapping position
        # WindowManager already computed into caller_state's x/y. Theme
        # cloning lands on the new plugin content's own "appSettings" (not
        # this function's own host app_settings — those keys are plugin-
        # owned, see settings.py's module docstring), read back generically
        # by name since main.py stays plugin-agnostic about what object
        # that actually is. zoomLevel/wheelZoomInverted clone onto the
        # HOST app_settings instead — zoom is generic host-owned window
        # state now, not plugin-owned (see yata-src/settings.py's own
        # docstring).
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
        # No theme/geometry cloning here (that's only for windows created
        # live via YATAS, in window_factory above) — a restored window
        # already has its own persisted position/theme/content. Used both
        # for every window at startup and for WindowManager.openWindow()
        # (YatasView's SHOW toggle, on) reopening one later in the session.
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

    # x-loader (see its own module docstring) waits for this exact message
    # to know every window this launch is going to open has actually
    # appeared, then fades out -- loader_socket is None unless we were
    # actually launched *through* the loader (run.sh), so this is a silent
    # no-op when run directly (run-yata.sh, or this binary standalone).
    # Two processEvents() calls (same idiom this codebase's own test suite
    # uses after creating windows) let Qt actually show/expose what was
    # just created before signaling "done" -- constructing a window and
    # setting visible:true doesn't guarantee it's been mapped by the
    # platform in that same instant.
    if loader_socket:
        app.processEvents()
        app.processEvents()
        _send_loader_message(loader_socket, "running")
        loader_socket.close()

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

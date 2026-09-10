#!/usr/bin/env python3
"""Regenerates the README screenshots in docs/screenshots/.

Each scenario boots a real (but fully isolated) instance of the app on the
live X11 display, drives it into the desired state (theme, filters, hover
targets) via direct QML property/method access, then captures the window
with ImageMagick's `import`. This is deliberately a *live* capture, not an
offscreen one: MultiEffect glow (hover icons, active glows) and real desktop
backdrop bleed-through for translucent themes only render correctly live —
see project memory "Live-desktop screenshot technique" for why.

Every window is built via main.py's own `_make_window()` (real
WindowRegistry + WindowManager + ThemeImpl + Main.qml, exactly like a real
launch) rather than loading Main.qml by hand — Main.qml has required
`windowManager`/`windowId` context properties since the 0.15.0 multi-window
feature, and a hand-rolled engine.load() predating that (this script's
original form) fails with "Theme is not defined" everywhere.

Usage:
    uv run python scripts/capture_screenshots.py --all
    uv run python scripts/capture_screenshots.py --scenario main-green

Safety: every scenario runs under a fresh, throwaway XDG_DATA_HOME/
XDG_CONFIG_HOME (mktemp -d, deleted after) seeded from
tests/fixtures/mock_tasks.json — it NEVER touches the real
~/.config/yata/yata.conf or ~/.local/share/yata/tasks.json. Do not remove
this isolation; see feedback_test_data_safety project memory for why (it was
accidentally clobbered four times in earlier sessions before this became a
hard rule).

Moves the real mouse pointer and briefly steals window focus while running
(needed for genuine HoverHandler-driven glow effects) — expected to run
unattended, not while you're using the mouse for something else.

Reproducing WINDOW_X/WINDOW_Y/FONT_SCALE below (only needed if the target
monitor layout changes, or the user wants the capture window somewhere
else): launch a throwaway instance sized WINDOW_WIDTHxWINDOW_HEIGHT under
an isolated XDG_CONFIG_HOME/XDG_DATA_HOME (same pattern as run_scenario()
below, minus the auto-actions/capture — just construct AppSettings +
TaskListModel + the QML engine and call app.exec() so it stays open), ask
the user to drag/zoom it where they want it on their real desktop, then once
they confirm, read the actual position back with
`xdotool getwindowgeometry <winid>` and the actual fontScale back from that
instance's own yata.conf (`[theme] fontScale=`) — don't guess either value.
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "mock_tasks.json"
OUT_DIR = REPO_ROOT / "docs" / "screenshots"

# Window size matches the previous generation of screenshots
# (docs/screenshots/*.png were all 991x511 before this script existed).
# Position/zoom were picked interactively on this machine's real desktop
# (right side of the primary 5120x1440 monitor, avoiding the user's other
# windows) and confirmed by the user — don't change these without doing
# that again: launch a throwaway instance, let the user drag/zoom it where
# they want, then read the resulting x/y/fontScale back from its (isolated)
# yata.conf. See the module docstring's "Reproducing this" section.
WINDOW_X = 4112
WINDOW_Y = 42
WINDOW_WIDTH = 991
WINDOW_HEIGHT = 511
FONT_SCALE = 1.4

# Exact per-window geometry for the multiwindow YATAS scenario (see
# run_yatas_multiwindow_scenario) — picked interactively by the user on this
# machine's real desktop (launched both windows live via a throwaway picker
# script — see scripts/_position_picker_notes below — dragged/resized each
# directly until neither overlapped and both stayed readable), then read
# back via `xdotool getwindowgeometry`, same don't-guess-it procedure as
# WINDOW_X/WINDOW_Y/FONT_SCALE above. The two windows are deliberately
# different sizes now (unlike every single-window scenario, which all share
# WINDOW_WIDTH/WINDOW_HEIGHT).
#
# An EARLIER pick (x/y/width/height requested programmatically rather than
# dragged live) silently overlapped: Main.qml's own
# `minimumWidth: toolbar.actionButtonsWidth * 2` clamped the requested back-
# window width (552) up to ~760 on actual render, pushing its right edge
# past the front window's left edge — invisible from the *requested* values
# alone, only caught by reading the *rendered* geometry back and by the user
# actually looking at the result. The values below were confirmed by
# `xdotool getwindowgeometry` against the live, already-rendered windows
# (not fed back in as a new request), so this clamping cannot recur for
# these specific numbers — but if either window's content (toolbar button
# count, font scale) changes enough to shift its own minimumWidth, re-derive
# via the same picker + read-back procedure rather than hand-editing these.
#
# font_scale here is a best-known approximation, not read back exactly: the
# picker script this session shared one on-disk settings file between both
# windows (a throwaway bug in the picker only — real capture_screenshots.py
# windows each get their own via _open_settings — see project memory), so
# the file's last-written values were an unreliable mix of both windows'
# histories. The actual screenshot in docs/screenshots/ was captured live
# from the real picked session directly (not regenerated from these
# constants), so it's correct regardless; regenerating from this script
# later may need a quick visual re-check of font size against the committed
# image.
# border_color (r-4.md) values are deliberately far apart in hue from each
# other AND from either window's own theme tint (magenta vs. black, green
# vs. goldenrod) so this one screenshot doubles as a demonstration of the
# per-window colorized-border feature — a viewer can tell the two windows
# apart by border color alone, not just position/tint.
MULTIWINDOW_BACK = dict(tag="Personal", theme_tint="black", opacity=100,
                         x=3573, y=39, width=760, height=498, font_scale=1.4,
                         border_color="#FF3DB2")
MULTIWINDOW_FRONT = dict(tag="Work", theme_tint="goldenrod", opacity=65,
                          x=4348, y=39, width=760, height=500, font_scale=1.4,
                          border_color="#39FF14")

# Each scenario: filename (under docs/screenshots/), theme, filters, which
# view is showing, and an optional two-step hover target (row match text,
# then a specific icon glyph inside that row to hover onto for its glow).
SCENARIOS = {
    # Restored — this scenario was accidentally dropped in commit 1155ace
    # while main-yata/main-yatas-multiwindow were being added, even though
    # README.md still references docs/screenshots/main-green.png at (0,0);
    # without it the script couldn't regenerate that screenshot at all.
    "main-green": dict(
        theme_mode="dark", theme_tint="green", opacity=65,
        view="list", group_by_day=False, status_sort="",
    ),
    "main-goldenrod": dict(
        theme_mode="dark", theme_tint="goldenrod", opacity=65,
        view="month", group_by_day=False, status_sort="",
    ),
    "main-dark": dict(
        theme_mode="dark", theme_tint="none", opacity=65,
        view="list", group_by_day=False, status_sort="",
        hover_row="deliberately **very long** task", hover_icon="\U0001F5D1",  # 🗑
    ),
    "main-yata": dict(
        theme_mode="dark", theme_tint="black", opacity=100,
        view="list", group_by_day=True, status_sort="",
        hover_row="Finish reading **Project Hail Mary**", hover_icon="↺",  # ↺
    ),
    "main_settings": dict(
        theme_mode="dark", theme_tint="none", opacity=57,
        view="list", group_by_day=True, status_sort="",
        wheel_zoom_inverted=True, open_theme_menu=True,
    ),
    "main-links": dict(
        theme_mode="dark", theme_tint="none", opacity=100,
        view="links", group_by_day=False, status_sort="active",
        hover_link_button=True,
    ),
}


def find_by_class(root, class_substr):
    matches = []

    def rec(item):
        try:
            cn = item.metaObject().className()
        except Exception:
            cn = ""
        if class_substr in cn:
            matches.append(item)
        for c in item.childItems():
            rec(c)

    rec(root)
    return matches


def find_by_exact_text(root, text):
    matches = []

    def rec(item):
        if item.property("text") == text:
            matches.append(item)
        for c in item.childItems():
            rec(c)

    rec(root)
    return matches


def find_task_delegate(root, contains):
    for item in find_by_class(root, "TaskDelegate"):
        text = item.property("text")
        if text and contains in text:
            return item
    return None


def find_qobject_by_class(root_qobject, class_substr):
    # Menu/Popup (e.g. ThemeMenu) are QObjects, not QQuickItems — Qt Quick
    # Controls parents them into the Window's Overlay layer rather than the
    # normal visual item tree, so find_by_class's childItems() walk never
    # reaches them regardless of open/closed state. QObject's own
    # parent-child *ownership* tree (set by QML at instantiation) does
    # include them, so search that instead via the generic findChildren().
    from PySide6.QtCore import QObject

    return [
        obj for obj in root_qobject.findChildren(QObject)
        if class_substr in obj.metaObject().className()
    ]


def center_of(item, content_root):
    pt = item.mapToItem(content_root, item.width() / 2, item.height() / 2)
    return round(pt.x()), round(pt.y())


def _bootstrap_app(tmp_dir: str):
    """Common setup shared by every scenario: isolated XDG dirs, a real
    QGuiApplication + QQmlApplicationEngine, and a real (but disposable)
    WindowRegistry/WindowManager pair. Returns
    (app, engine, manager, icon_provider, app_icon) — callers build actual
    windows on top of this via main._make_window()."""
    import os

    os.environ["XDG_DATA_HOME"] = tmp_dir
    os.environ["XDG_CONFIG_HOME"] = tmp_dir
    os.environ.pop("QT_QPA_PLATFORM", None)  # must be the real X11 platform, not offscreen

    sys.path.insert(0, str(REPO_ROOT / "yata-src"))
    # Re-import per subprocess invocation (this always runs in its own fresh
    # process — see main()'s --all re-exec loop — so a plain top-level
    # import is fine and PySide6/Qt singletons are never reused across
    # scenarios).
    import resources_rc  # noqa: F401
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    # QQuickWindow must be imported before any QWindow.contentItem() call
    # below — shiboken needs the type registered to downcast the plain
    # QWindow the engine hands back into a QQuickWindow (see project
    # memory: "QQuickWindow downcast issue").
    from PySide6.QtQuick import QQuickWindow  # noqa: F401
    from icons import IconProvider
    from window_registry import WindowRegistry
    from window_manager import WindowManager
    import main as main_module

    # main._make_window()'s deferred setup calls enable_always_below() on
    # every window it builds (real launched windows deliberately stay below
    # other apps — see x11_stacking.py). A screenshot window has no reason
    # to: it just needs to behave like an ordinary top-level window so
    # xdotool's windowactivate/mousemove reliably deliver real hover events
    # (confirmed empirically: leaving always-below in made the LINKS hover-
    # glow scenario silently capture with no glow at all), and so the
    # multiwindow scenario's explicit front/back windowraise is deterministic
    # instead of racing with always-below's own activeChanged reassertion.
    # Patched here (not by editing x11_stacking.py) since this no-op is only
    # correct for throwaway screenshot windows, never for a real launch.
    main_module.enable_always_below = lambda window: None

    app = QGuiApplication(sys.argv[:1])
    app.setOrganizationName("yata")
    app.setApplicationName("yata")

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO_ROOT / "yata-src" / "qml"))
    # Same per-plugin import path registration main.py's own main() does —
    # without it, the plugin's QML files (e.g. TaskListContent.qml's
    # ThemeMenu/Toolbar/etc references) can't be resolved the same way a
    # real launch resolves them.
    import plugins_registry  # noqa: PLC0415

    for plugin in plugins_registry.AVAILABLE_PLUGINS.values():
        if plugin.qml_import_dir:
            engine.addImportPath(plugin.qml_import_dir)

    registry = WindowRegistry(path=str(Path(tmp_dir) / "windows.json"))

    def _unused_factory(*_a, **_k):
        raise RuntimeError("createWindow() should never be invoked by a screenshot scenario")

    manager = WindowManager(registry, _unused_factory)
    icon_provider = IconProvider()
    app_icon = QIcon()
    return app, engine, registry, manager, icon_provider, app_icon


def _build_window(engine, registry, manager, icon_provider, app_icon, *, tag, theme_mode,
                   theme_tint, opacity, x, y, width=WINDOW_WIDTH, height=WINDOW_HEIGHT,
                   font_scale=FONT_SCALE, wheel_zoom_inverted=False, seed_tasks=True,
                   border_color=""):
    """Registers a fresh window_id in `registry`, seeds its task store (from
    the shared mock fixture, unless seed_tasks=False), and builds it via
    main._make_window() — the exact same construction path a real launch
    uses, so it always has a correctly-populated windowManager/windowId/
    Theme context. Returns (window_id, QQuickWindow, TaskListModel).

    r-9.md step 4: theme/opacity/font-scale/wheel-zoom are plugin-owned
    settings now (plugins/simple_task_list/settings.py's TaskListSettings,
    reached via the plugin's own "appSettings" content property), not the
    host's settings.AppSettings — same split main.py's own window_factory/
    restore_factory apply. Window geometry/borderColor stay host-owned.
    """
    import plugins_registry
    from main import _make_window, _open_settings
    from settings import AppSettings
    from window_registry import tasks_path_for

    window_id = registry.add(tag)
    tasks_path = tasks_path_for(window_id)
    if seed_tasks:
        shutil.copy(FIXTURE, tasks_path)

    legacy_qsettings = _open_settings(window_id)
    plugin = plugins_registry.get(registry.get_plugin(window_id))
    plugin_content = plugin.create_content(window_id, tasks_path, legacy_qsettings)
    plugin_content.context_properties["appSettings"].themeMode = theme_mode
    plugin_content.context_properties["appSettings"].themeTint = theme_tint
    plugin_content.context_properties["appSettings"].opacityPercent = opacity
    plugin_content.context_properties["appSettings"].fontScale = font_scale
    plugin_content.context_properties["appSettings"].wheelZoomInverted = wheel_zoom_inverted

    settings = AppSettings(legacy_qsettings)
    settings.width = width
    settings.height = height
    settings.x = x
    settings.y = y
    settings.borderColor = border_color

    win = _make_window(engine, icon_provider, manager, app_icon, window_id, plugin_content, settings)
    task_model = manager._windows[window_id]["task_model"]
    return window_id, win, task_model


def run_scenario(name: str, cfg: dict, out_dir: Path):
    tmp_dir = tempfile.mkdtemp(prefix="yata-screenshot-")
    try:
        app, engine, registry, manager, icon_provider, app_icon = _bootstrap_app(tmp_dir)

        from PySide6.QtCore import QTimer, QMetaObject, Q_ARG, Qt as QtNS

        window_id, win, task_model = _build_window(
            engine, registry, manager, icon_provider, app_icon,
            tag="YATA", theme_mode=cfg["theme_mode"], theme_tint=cfg["theme_tint"],
            opacity=cfg["opacity"], x=WINDOW_X, y=WINDOW_Y,
            wheel_zoom_inverted=cfg.get("wheel_zoom_inverted", False),
        )
        task_model.setGroupByDay(cfg.get("group_by_day", False))
        task_model.setStatusSortMode(cfg.get("status_sort", ""))

        result = {}

        # PySide swallows exceptions raised inside a Qt timer callback (just
        # prints a traceback) rather than propagating them out of
        # app.exec(), which would otherwise hang forever waiting for a
        # capture() that never runs. Every callback below is wrapped so a
        # failure always quits the loop and gets re-raised after exec().
        def guarded(fn):
            def wrapper(*a):
                try:
                    fn(*a)
                except Exception as exc:  # noqa: BLE001
                    result["error"] = exc
                    app.quit()

            return wrapper

        @guarded
        def act():
            content = win.contentItem()

            view = cfg.get("view", "list")
            if view in ("month", "links"):
                filter_bars = find_by_class(content, "FilterBar")
                QMetaObject.invokeMethod(
                    filter_bars[0], "setGrouping", QtNS.DirectConnection,
                    Q_ARG("QVariant", view), Q_ARG("QVariant", True),
                )

            win_id = int(win.winId())
            subprocess.run(["xdotool", "windowactivate", str(win_id)], check=False)

            @guarded
            def hover_step2():
                row_text = cfg.get("hover_row")
                if row_text:
                    delegate = find_task_delegate(content, row_text)
                    if delegate is None:
                        raise RuntimeError(f"no task delegate matches {row_text!r}")
                    icons = find_by_exact_text(delegate, cfg["hover_icon"])
                    if not icons:
                        raise RuntimeError(f"no icon {cfg['hover_icon']!r} found in hovered row")
                    ix, iy = center_of(icons[0], content)
                    subprocess.run(
                        ["xdotool", "mousemove", "--window", str(win_id), str(ix), str(iy)],
                        check=False,
                    )
                elif cfg.get("hover_link_button"):
                    buttons = find_by_class(content, "LinkToTaskButton")
                    if not buttons:
                        raise RuntimeError("no LinkToTaskButton found")
                    ix, iy = center_of(buttons[0], content)
                    subprocess.run(
                        ["xdotool", "mousemove", "--window", str(win_id), str(ix), str(iy)],
                        check=False,
                    )

                if cfg.get("open_theme_menu"):
                    menus = [
                        m for m in find_qobject_by_class(win, "ThemeMenu")
                        if m.property("showQuit") is False
                    ]
                    if not menus:
                        raise RuntimeError("no toolbar ThemeMenu found")
                    # Menu.popup() with no arguments opens at the *current
                    # mouse cursor position* (matching a real click on the
                    # button), not anchored to its nominal QML parent — move
                    # the pointer onto the THEME button first, or the menu
                    # opens wherever the cursor last happened to be.
                    theme_buttons = [
                        b for b in find_by_class(content, "ToolButton")
                        if b.property("text") == "Theme"
                    ]
                    if not theme_buttons:
                        raise RuntimeError("no Theme toolbar button found")
                    tx, ty = center_of(theme_buttons[0], content)
                    subprocess.run(
                        ["xdotool", "mousemove", "--window", str(win_id), str(tx), str(ty)],
                        check=False,
                    )
                    QMetaObject.invokeMethod(menus[0], "popup")

                QTimer.singleShot(400, capture)

            @guarded
            def hover_step1():
                row_text = cfg.get("hover_row")
                if row_text:
                    delegate = find_task_delegate(content, row_text)
                    if delegate is None:
                        raise RuntimeError(f"no task delegate matches {row_text!r}")
                    rx, ry = center_of(delegate, content)
                    subprocess.run(
                        ["xdotool", "mousemove", "--window", str(win_id), str(rx), str(ry)],
                        check=False,
                    )
                QTimer.singleShot(400, hover_step2)

            @guarded
            def capture():
                out_path = out_dir / f"{name}.png"
                subprocess.run(
                    ["import", "-window", str(win_id), str(out_path)], check=True,
                )
                result["ok"] = True
                app.quit()

            QTimer.singleShot(300, hover_step1)

        QTimer.singleShot(900, act)  # let the window map before touching it
        app.exec()

        if "error" in result:
            raise result["error"]
        if not result.get("ok"):
            raise RuntimeError(f"scenario {name!r} did not complete (see errors above)")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def run_yatas_multiwindow_scenario(out_dir: Path):
    """Two real windows in one screenshot, demonstrating YATAS multi-window
    management: a Goldenrod-themed window with YATAS open (listing both
    windows), cascaded in front of a Black-themed window showing the normal
    (mock) task list. Captured as two separate per-window `import` grabs
    (the proven, stacking-order-immune technique every other scenario uses),
    then composited into one image — NOT a single live full-screen region
    grab: each window's own translucent/rounded areas would otherwise show
    whatever was really behind it on the live desktop at capture time (its
    own backdrop bleed-through, baked into the PNG, not a clean alpha
    channel), which would look wrong once pasted over a different
    background. Compositing two already-correct individual captures avoids
    that entirely.
    """
    tmp_dir = tempfile.mkdtemp(prefix="yata-screenshot-")
    try:
        app, engine, registry, manager, icon_provider, app_icon = _bootstrap_app(tmp_dir)

        from PySide6.QtCore import QTimer

        # WindowRegistry auto-seeds a "YATA"/DEFAULT_WINDOW_ID entry on a
        # true first run (windows.json not existing yet in this fresh tmp
        # dir counts) — drop it before building the two real demo windows
        # below, or it shows up as a confusing third, never-actually-open
        # row in the captured YATAS list.
        from window_registry import DEFAULT_WINDOW_ID
        registry.remove(DEFAULT_WINDOW_ID)

        # Back window first (task list, mock entries) — created/mapped
        # before the front one so it's naturally behind in stacking order
        # even before any explicit raise.
        back_cfg = MULTIWINDOW_BACK
        back_id, back_win, back_model = _build_window(
            engine, registry, manager, icon_provider, app_icon,
            tag=back_cfg["tag"], theme_mode="dark", theme_tint=back_cfg["theme_tint"],
            opacity=back_cfg["opacity"], x=back_cfg["x"], y=back_cfg["y"],
            width=back_cfg["width"], height=back_cfg["height"],
            font_scale=back_cfg["font_scale"], border_color=back_cfg["border_color"],
        )

        result = {}

        def guarded(fn):
            def wrapper(*a):
                try:
                    fn(*a)
                except Exception as exc:  # noqa: BLE001
                    result["error"] = exc
                    app.quit()

            return wrapper

        @guarded
        def build_front():
            # Front window (YATAS section open) — built only once the back
            # window has had time to map, so windowManager.listWindows()
            # (read when YatasView first becomes visible) already includes
            # it, and both rows show up in the captured YATAS list.
            front_cfg = MULTIWINDOW_FRONT
            front_id, front_win, front_model = _build_window(
                engine, registry, manager, icon_provider, app_icon,
                tag=front_cfg["tag"], theme_mode="dark", theme_tint=front_cfg["theme_tint"],
                opacity=front_cfg["opacity"], x=front_cfg["x"], y=front_cfg["y"],
                width=front_cfg["width"], height=front_cfg["height"],
                font_scale=front_cfg["font_scale"], border_color=front_cfg["border_color"],
                seed_tasks=False,  # never shown — YATAS view replaces the list entirely
            )
            result["front_id"] = front_id
            result["front_win"] = front_win
            QTimer.singleShot(900, lambda: open_yatas(front_win))

        @guarded
        def open_yatas(front_win):
            from PySide6.QtCore import QMetaObject, Q_ARG, Qt as QtNS

            content = front_win.contentItem()
            filter_bars = find_by_class(content, "FilterBar")
            QMetaObject.invokeMethod(
                filter_bars[0], "setGrouping", QtNS.DirectConnection,
                Q_ARG("QVariant", "yatas"), Q_ARG("QVariant", True),
            )
            front_win_id = int(front_win.winId())
            subprocess.run(["xdotool", "windowactivate", str(front_win_id)], check=False)
            subprocess.run(["xdotool", "windowraise", str(front_win_id)], check=False)
            QTimer.singleShot(400, capture)

        @guarded
        def capture():
            # A single live grab of the real, composited desktop region
            # spanning both windows — NOT two separate per-window captures
            # glued together after the fact. That was tried first and is
            # wrong: each window's own translucent areas bake in whatever
            # was behind THAT window during ITS OWN separate capture, so
            # gluing two such captures together breaks background
            # continuity between them (visible as a seam/transparent gap) —
            # the whole point of the user's carefully-chosen real desktop
            # position was a continuous backdrop behind both real windows at
            # once, which only a real single screen-region grab preserves.
            # Safe now that enable_always_below is neutralized above (real
            # stacking is deterministic — front window explicitly raised in
            # open_yatas — so "root" genuinely shows it on top).
            back_cfg, front_cfg = MULTIWINDOW_BACK, MULTIWINDOW_FRONT
            # Sanity check, not just trust the constants: Main.qml's own
            # minimumWidth (toolbar.actionButtonsWidth * 2) can silently
            # clamp a requested width up to something bigger on actual
            # render — this is exactly what caused an earlier version of
            # this scenario to render with the two windows overlapping
            # (requested geometry didn't overlap; rendered geometry did).
            # Comparing requested vs. actually-rendered geometry here would
            # have caught that immediately instead of only in the final
            # image.
            for label, win_obj, cfg in (("back", back_win, back_cfg),
                                         ("front", result["front_win"], front_cfg)):
                actual_w, actual_h = win_obj.width(), win_obj.height()
                if (actual_w, actual_h) != (cfg["width"], cfg["height"]):
                    raise RuntimeError(
                        f"{label} window rendered at {actual_w}x{actual_h}, "
                        f"not the requested {cfg['width']}x{cfg['height']} — "
                        f"likely Main.qml's minimumWidth clamped it; MULTIWINDOW_"
                        f"{label.upper()} needs updating to a size that survives "
                        f"unclamped, or the two windows may overlap"
                    )
            min_x = min(back_cfg["x"], front_cfg["x"])
            min_y = min(back_cfg["y"], front_cfg["y"])
            max_x = max(back_cfg["x"] + back_cfg["width"], front_cfg["x"] + front_cfg["width"])
            max_y = max(back_cfg["y"] + back_cfg["height"], front_cfg["y"] + front_cfg["height"])
            total_w = max_x - min_x
            total_h = max_y - min_y
            out_path = out_dir / "main-yatas-multiwindow.png"
            subprocess.run(
                [
                    "import", "-window", "root",
                    "-crop", f"{total_w}x{total_h}+{min_x}+{min_y}",
                    "+repage", str(out_path),
                ],
                check=True,
            )
            result["ok"] = True
            app.quit()

        QTimer.singleShot(900, build_front)
        app.exec()

        if "error" in result:
            raise result["error"]
        if not result.get("ok"):
            raise RuntimeError("multiwindow scenario did not complete (see errors above)")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    all_choices = sorted(SCENARIOS) + ["main-yatas-multiwindow"]
    parser.add_argument("--scenario", choices=all_choices, help="capture a single scenario")
    parser.add_argument("--all", action="store_true", help="capture every scenario")
    parser.add_argument("--out", default=str(OUT_DIR), help="output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        # Each scenario gets its own fresh process (Qt doesn't support
        # multiple QGuiApplication instances in one process), re-invoking
        # this same script one scenario at a time.
        for scenario_name in all_choices:
            print(f"--- {scenario_name} ---", flush=True)
            subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--scenario", scenario_name,
                 "--out", str(out_dir)],
                check=True, cwd=str(REPO_ROOT),
            )
        return

    if not args.scenario:
        parser.error("pass --scenario NAME or --all")

    if args.scenario == "main-yatas-multiwindow":
        run_yatas_multiwindow_scenario(out_dir)
        print(f"wrote {out_dir / 'main-yatas-multiwindow.png'}")
        return

    run_scenario(args.scenario, SCENARIOS[args.scenario], out_dir)
    print(f"wrote {out_dir / (args.scenario + '.png')}")


if __name__ == "__main__":
    main()

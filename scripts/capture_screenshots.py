#!/usr/bin/env python3
"""Regenerates the README screenshots in docs/screenshots/.

Each scenario boots a real (but fully isolated) instance of the app on the
live X11 display, drives it into the desired state (theme, filters, hover
targets) via direct QML property/method access, then captures the window
with ImageMagick's `import`. This is deliberately a *live* capture, not an
offscreen one: MultiEffect glow (hover icons, active glows) and real desktop
backdrop bleed-through for translucent themes only render correctly live —
see project memory "Live-desktop screenshot technique" for why.

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
QML_MAIN = REPO_ROOT / "yata-src" / "qml" / "Main.qml"
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

# Each scenario: filename (under docs/screenshots/), theme, filters, which
# view is showing, and an optional two-step hover target (row match text,
# then a specific icon glyph inside that row to hover onto for its glow).
SCENARIOS = {
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


def run_scenario(name: str, cfg: dict, out_dir: Path):
    import os

    tmp_dir = tempfile.mkdtemp(prefix="yata-screenshot-")
    try:
        data_dir = Path(tmp_dir) / "yata"
        data_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(FIXTURE, data_dir / "tasks.json")
        os.environ["XDG_DATA_HOME"] = tmp_dir
        os.environ["XDG_CONFIG_HOME"] = tmp_dir
        os.environ.pop("QT_QPA_PLATFORM", None)  # must be the real X11 platform, not offscreen

        sys.path.insert(0, str(REPO_ROOT / "yata-src"))
        # Re-import per subprocess invocation (this function always runs in
        # its own fresh process — see main()'s --all re-exec loop — so a
        # plain top-level import is fine and PySide6/Qt singletons are never
        # reused across scenarios).
        import resources_rc  # noqa: F401
        from PySide6.QtCore import QUrl, QTimer, QMetaObject, Q_ARG, Qt as QtNS
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
        # QQuickWindow must be imported before any QWindow.contentItem() call
        # below — shiboken needs the type registered to downcast the plain
        # QWindow the engine hands back into a QQuickWindow (see project
        # memory: "QQuickWindow downcast issue").
        from PySide6.QtQuick import QQuickWindow  # noqa: F401
        from models import TaskListModel, TaskStore
        from settings import AppSettings

        try:
            from icons import IconProvider
        except ImportError:
            IconProvider = None

        app = QGuiApplication(sys.argv[:1])
        app.setOrganizationName("yata")
        app.setApplicationName("yata")

        engine = QQmlApplicationEngine()
        engine.addImportPath(str(REPO_ROOT / "yata-src" / "qml"))

        settings = AppSettings()
        settings.width = WINDOW_WIDTH
        settings.height = WINDOW_HEIGHT
        settings.x = WINDOW_X
        settings.y = WINDOW_Y
        settings.themeMode = cfg["theme_mode"]
        settings.themeTint = cfg["theme_tint"]
        settings.opacityPercent = cfg["opacity"]
        settings.fontScale = FONT_SCALE
        settings.wheelZoomInverted = cfg.get("wheel_zoom_inverted", False)

        task_model = TaskListModel(TaskStore())
        task_model.setGroupByDay(cfg.get("group_by_day", False))
        task_model.setStatusSortMode(cfg.get("status_sort", ""))

        icon_provider = IconProvider() if IconProvider else None
        engine.rootContext().setContextProperty("taskModel", task_model)
        engine.rootContext().setContextProperty("appSettings", settings)
        if icon_provider:
            engine.rootContext().setContextProperty("iconProvider", icon_provider)

        engine.load(QUrl.fromLocalFile(str(QML_MAIN)))
        if not engine.rootObjects():
            raise RuntimeError("QML failed to load")
        win = engine.rootObjects()[0]

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

                QTimer.singleShot(250, capture)

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
                QTimer.singleShot(300, hover_step2)

            @guarded
            def capture():
                out_path = out_dir / f"{name}.png"
                subprocess.run(
                    ["import", "-window", str(win_id), str(out_path)], check=True,
                )
                result["ok"] = True
                app.quit()

            QTimer.singleShot(200, hover_step1)

        QTimer.singleShot(400, act)  # let the window map before touching it
        app.exec()

        if "error" in result:
            raise result["error"]
        if not result.get("ok"):
            raise RuntimeError(f"scenario {name!r} did not complete (see errors above)")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), help="capture a single scenario")
    parser.add_argument("--all", action="store_true", help="capture every scenario")
    parser.add_argument("--out", default=str(OUT_DIR), help="output directory")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.all:
        # Each scenario gets its own fresh process (Qt doesn't support
        # multiple QGuiApplication instances in one process), re-invoking
        # this same script one scenario at a time.
        for scenario_name in SCENARIOS:
            print(f"--- {scenario_name} ---", flush=True)
            subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), "--scenario", scenario_name,
                 "--out", str(out_dir)],
                check=True, cwd=str(REPO_ROOT),
            )
        return

    if not args.scenario:
        parser.error("pass --scenario NAME or --all")

    run_scenario(args.scenario, SCENARIOS[args.scenario], out_dir)
    print(f"wrote {out_dir / (args.scenario + '.png')}")


if __name__ == "__main__":
    main()

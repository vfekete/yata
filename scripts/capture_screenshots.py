#!/usr/bin/env python3
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

WINDOW_X = 4112
WINDOW_Y = 42
WINDOW_WIDTH = 991
WINDOW_HEIGHT = 511
FONT_SCALE = 1.4

MULTIWINDOW_BACK = dict(tag="Personal", theme_tint="black", opacity=100,
                         x=3573, y=39, width=760, height=498, font_scale=1.4,
                         border_color="#FF3DB2")
MULTIWINDOW_FRONT = dict(tag="Work", theme_tint="goldenrod", opacity=65,
                          x=4348, y=39, width=760, height=500, font_scale=1.4,
                          border_color="#39FF14")

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
        hover_row="deliberately **very long** task", hover_icon="\U0001F5D1",
    ),
    "main-yata": dict(
        theme_mode="dark", theme_tint="black", opacity=100,
        view="list", group_by_day=True, status_sort="",
        hover_row="Finish reading **Project Hail Mary**", hover_icon="↺",
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
    from PySide6.QtCore import QObject

    return [
        obj for obj in root_qobject.findChildren(QObject)
        if class_substr in obj.metaObject().className()
    ]


def center_of(item, content_root):
    pt = item.mapToItem(content_root, item.width() / 2, item.height() / 2)
    return round(pt.x()), round(pt.y())


def _bootstrap_app(tmp_dir: str):
    import os

    os.environ["XDG_DATA_HOME"] = tmp_dir
    os.environ["XDG_CONFIG_HOME"] = tmp_dir
    os.environ.pop("QT_QPA_PLATFORM", None)

    sys.path.insert(0, str(REPO_ROOT / "yata-src"))
    import resources_rc  # noqa: F401
    from PySide6.QtGui import QGuiApplication, QIcon
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtQuick import QQuickWindow  # noqa: F401
    from icons import IconProvider
    from window_registry import WindowRegistry
    from window_manager import WindowManager
    import main as main_module

    main_module.enable_always_below = lambda window: None

    app = QGuiApplication(sys.argv[:1])
    app.setOrganizationName("yata")
    app.setApplicationName("yata")

    engine = QQmlApplicationEngine()
    engine.addImportPath(str(REPO_ROOT / "yata-src" / "qml"))
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
    import os

    import plugins_registry
    from main import _make_window, _open_settings
    from settings import AppSettings
    from window_registry import instance_dir_for

    window_id = registry.add(tag)
    instance_dir = instance_dir_for(window_id)
    if seed_tasks:
        shutil.copy(FIXTURE, os.path.join(instance_dir, "tasks.json"))

    legacy_qsettings = _open_settings(window_id)
    plugin = plugins_registry.get(registry.get_plugin(window_id))
    plugin_content = plugin.create_content(window_id, instance_dir, legacy_qsettings)
    plugin_content.context_properties["appSettings"].themeMode = theme_mode
    plugin_content.context_properties["appSettings"].themeTint = theme_tint
    plugin_content.context_properties["appSettings"].opacityPercent = opacity

    settings = AppSettings(legacy_qsettings)
    settings.width = width
    settings.height = height
    settings.x = x
    settings.y = y
    settings.zoomLevel = font_scale
    settings.wheelZoomInverted = wheel_zoom_inverted
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

        QTimer.singleShot(900, act)
        app.exec()

        if "error" in result:
            raise result["error"]
        if not result.get("ok"):
            raise RuntimeError(f"scenario {name!r} did not complete (see errors above)")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def run_yatas_multiwindow_scenario(out_dir: Path):
    tmp_dir = tempfile.mkdtemp(prefix="yata-screenshot-")
    try:
        app, engine, registry, manager, icon_provider, app_icon = _bootstrap_app(tmp_dir)

        from PySide6.QtCore import QTimer

        from window_registry import DEFAULT_WINDOW_ID
        registry.remove(DEFAULT_WINDOW_ID)

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
            front_cfg = MULTIWINDOW_FRONT
            front_id, front_win, front_model = _build_window(
                engine, registry, manager, icon_provider, app_icon,
                tag=front_cfg["tag"], theme_mode="dark", theme_tint=front_cfg["theme_tint"],
                opacity=front_cfg["opacity"], x=front_cfg["x"], y=front_cfg["y"],
                width=front_cfg["width"], height=front_cfg["height"],
                font_scale=front_cfg["font_scale"], border_color=front_cfg["border_color"],
                seed_tasks=False,
            )
            result["front_id"] = front_id
            result["front_win"] = front_win
            QTimer.singleShot(900, lambda: open_yatas(front_win))

        @guarded
        def open_yatas(front_win):
            front_win.setProperty("yatasActive", True)
            front_win_id = int(front_win.winId())
            subprocess.run(["xdotool", "windowactivate", str(front_win_id)], check=False)
            subprocess.run(["xdotool", "windowraise", str(front_win_id)], check=False)
            QTimer.singleShot(400, capture)

        @guarded
        def capture():
            back_cfg, front_cfg = MULTIWINDOW_BACK, MULTIWINDOW_FRONT
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

# Building and running YATA

YATA is a Python + QtQuick/QML application managed with [`uv`](https://docs.astral.sh/uv/).
Running it from source needs no explicit build step — "building" just means
creating the project's virtual environment and installing dependencies,
which `uv` handles automatically. A separate step (`./build.sh`, below)
packages the app into a single standalone executable for easy installation.

## Prerequisites

- `uv` installed (https://docs.astral.sh/uv/getting-started/installation/)
- On Linux, a working Qt platform plugin (the default `xcb`/`wayland` plugin
  that ships with PySide6 is enough on GNOME/Ubuntu)

`uv` downloads a matching Python interpreter and creates `.venv/`
automatically the first time it is used in this project — no manual
`venv` setup or `pip install` is required, and no dependency is ever
installed outside of that virtual environment.

## Run the application

```sh
./run.sh
```

Builds (if needed) and launches the startup splash (`x-loader/`) alongside
YATA, wired together over a private Unix domain socket — see "Startup
splash" below. `./run-yata.sh` runs YATA directly with no splash at all;
`./run-loader.sh` previews the splash on its own, without launching YATA.

### Startup splash

`x-loader/` is a small, independent program shown while the real YATA app
loads — most useful for the packaged single-file binary, where Nuitka's
onefile self-extraction plus Python/Qt init can take noticeably longer
than an already-warm interpreter. It's had a rockier history than most
things in this repo: two earlier Qt-based implementations (a PySide6
prototype, then a from-scratch C++/QML rewrite linking a real Qt6 install
directly, both since removed) were built and verified working, but each
turned out to have Qt's own startup/init cost baked in regardless of
language or optimization level — reported/measured live at 26-53s before a
window even appeared, even from an `-O3`+LTO Release C++ build. `x-loader/`
is a ground-up rewrite in plain C against only Xlib/Xinerama (no Qt, no
Python, no image-decoding library even — see its own top comment) and
measures ~19ms from process start to the window actually appearing on
screen.

**Fully wired into the real launch flow.** `x-loader/` fades in, holds
fully visible, fades out, and exits — driven by two tiny messages YATA
sends over a Unix domain socket (`YATA_LOADER_SOCKET`): `"starting"` once
connected, `"running"` once every window from this launch is actually
shown. The splash fades out and exits the instant it hears `"running"`,
after 2 minutes if it never does, or immediately if YATA disconnects
without ever sending it (e.g. a crash). Two ways this gets wired up:
- **Source checkout**: `run.sh` generates the socket path, launches
  `x-loader` in the background, and runs YATA in the foreground with that
  path exported.
- **Packaged binary** (`build.sh`, below): `x-loader` ships bundled inside
  the one binary itself; at startup it self-extracts and launches (see
  `yata-src/main.py`'s `_maybe_launch_bundled_loader`) — no shell script
  involved, just running the one file.

`./run-yata.sh --backup`/`-b` and `-h`/`--help` skip the splash entirely
(both exit before any window opens, so there'd be nothing for a
`"running"` to ever report).

```sh
./run-loader.sh          # builds (if needed) and previews x-loader standalone
./run-loader.sh --dark   # force dark regardless of desktop preference
./run-loader.sh --light  # force light regardless of desktop preference
```

Run standalone like this (no `YATA_LOADER_SOCKET` set), it just holds the
fully-faded-in image until dismissed by a click or keypress, then holds
fully hidden until a second one — there's no YATA to report `"running"`.
With neither flag, it follows the desktop's own light/dark preference
(`gsettings get org.gnome.desktop.interface color-scheme`). Needs
`libx11-dev`/`libxinerama-dev` (or equivalent) and a C compiler; see
`x-loader/Makefile`.

## Run the tests

```sh
uv run --group dev pytest
```

`x-loader/` has no automated tests yet (kept to manual/visual verification
so far — see CHANGELOG).

## Build a standalone binary

```sh
./build.sh
```

Checks that `yata-src/main.py`'s `APP_VERSION` matches `pyproject.toml`'s
`version` (they gate independent things — `APP_VERSION` controls desktop
entry/icon-cache resync on upgrade — but drifting apart is a real bug the
build should catch, not ship) and that the app icon
(`resources/assets/app-icon.png`) actually exists, then produces a single
file: `dist/yata-X.Y.Z`, via
[`pyside6-deploy`](https://doc.qt.io/qtforpython/deployment/deploy-guide.html)
(bundled with PySide6, which drives [Nuitka](https://nuitka.net/) to
compile it into one file). This is the file to run, and what a desktop
entry's `Exec=` should point at. `nuitka`/`patchelf` come from the `build`
dependency group (`uv run --group build ...`), the first build takes a few
minutes, and the resulting binary is large (~65MB, embeds a private Qt
plus `x-loader`) and Linux-only (produces ELF binaries).

`x-loader` (compiled fresh via plain `make`, no Nuitka needed for it) ships
*inside* that one file — `build.sh` passes it to Nuitka as an onefile data
file (`--include-data-files`, injected into the generated
`pysidedeploy.spec`'s `[nuitka] extra_args`), and `yata-src/main.py`'s
`_maybe_launch_bundled_loader()` finds it at startup via the
`__nuitka_binary_dir` name Nuitka injects into `builtins` (the directory
included data files get self-extracted into) and launches it from there —
see "Startup splash" above. No separate sibling file to lose track of; if
extraction ever fails to turn it up, the app still runs fine, just with no
splash.

Each registered plugin's own QML (`plugins/<id>/qml/`, see "Plugin
architecture" below) ships inside the binary the same way, via
`--include-data-dir` (Nuitka's recursive directory equivalent of
`--include-data-files`) — one per plugin, generated by `build.sh` from
`plugins_registry.AVAILABLE_PLUGINS`, so adding a new plugin needs no
`build.sh` change as long as it sets `qml_import_dir` on its `Plugin`
entry. This is necessary because `pyside6-deploy`'s own QML
auto-detection only finds files reachable via `yata-src/qml/Main.qml`'s
*static* QML imports — a plugin's content, loaded at runtime through a
`Loader` whose `source` is a plain Python-computed `QUrl` string (see
`plugin_api.py`'s `PluginContent.qml_source`), is invisible to that scan.
Skipping this step produces a binary that launches, then immediately
fails with `"No such file or directory"` the moment it tries to load the
plugin's own QML — confirmed live before this was added, so if you ever
see that error from a packaged build, this is the first thing to check.

## Try the mock task dataset

`tests/fixtures/mock_tasks.json` is a 21-task, 3-day dataset (6 active / 6
done / 3 cancelled on day 1, 5 done on day 2, 1 cancelled on day 3) used to
spot-check day-grouping, status-sort, markdown rendering and long-text word
wrap (one task's text is 779 characters). `tests/test_mock_fixture.py`
checks its shape stays as described. To see it in the running app, point
the app at it directly instead of copying over your real data:

```sh
XDG_DATA_HOME="$(mktemp -d)" bash -c '
  mkdir -p "$XDG_DATA_HOME/yata"
  cp tests/fixtures/mock_tasks.json "$XDG_DATA_HOME/yata/tasks.json"
  XDG_DATA_HOME="$XDG_DATA_HOME" ./run.sh
'
```

(`XDG_DATA_HOME` controls where `storage.py`'s `data_dir()` looks for
`tasks.json`, so this runs against a throwaway copy and never touches
`~/.local/share/yata/tasks.json`.)

## Project layout

- `yata-src/` — host application source (window/lock/close/title chrome,
  plugin loading machinery — `main.py`, `window_manager.py`,
  `plugin_api.py`, `plugins_registry.py` — and the host's own QML in
  `yata-src/qml/`, just `Main.qml`/`DragGhost.qml` as of r-9.md)
- `plugins/` — window-content plugins (r-9.md's plugin architecture); each
  `plugins/<id>/` is a self-contained Python package with its own
  `plugin.py` (`PLUGIN`/`create_content()`) and, if it has visual content,
  its own `plugins/<id>/qml/`. `plugins/simple_task_list/` is the
  original, and so far only, plugin — the actual task-list UI/backend.
  Statically registered (not dynamically loaded), see
  `plugins_registry.py`
- `x-loader/` — the pure-X11 startup splash (`main.c`, `effects.c`/`.h`,
  `Makefile`, `generate_assets.sh`) — see "Startup splash" above
- `resources/` — non-code assets for the main app, including
  `resources/loader-assets/` (the splash's background images)
- `tests/` — pytest test suite for `yata-src/`/`plugins/`; `tests/fixtures/`
  holds mock data
- `pyproject.toml` — dependencies, managed by `uv`
- `run.sh` / `run-yata.sh` / `run-loader.sh` — run YATA with the splash in
  front of it, run YATA directly with no splash, and preview the splash
  standalone, respectively
- `build.sh` — packages `yata-src/` + `plugins/` + `x-loader/` into one
  standalone binary (see "Build a standalone binary" above)

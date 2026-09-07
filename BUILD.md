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

```sh
./run.sh
```

Currently just runs YATA directly (equivalent to `./run-yata.sh`) — see
"Startup splash" below for why. `./run-yata.sh` is the explicit form of the
same thing; `./run-loader.sh` previews the splash on its own, without
launching YATA at all.

### Startup splash

`x-loader/` is a small, independent program meant to be shown while the
real YATA app loads — most useful for the packaged single-file binary,
where Nuitka's onefile self-extraction plus Python/Qt init can take
noticeably longer than an already-warm interpreter. It's had a rockier
history than most things in this repo: two earlier Qt-based
implementations (a PySide6 prototype, then a from-scratch C++/QML rewrite
linking a real Qt6 install directly, both since removed) were built and
verified working, but each turned out to have Qt's own startup/init cost
baked in regardless of language or optimization level — reported/measured
live at 26-53s before a window even appeared, even from an `-O3`+LTO
Release C++ build. `x-loader/` is a ground-up rewrite in plain C against
only Xlib/Xinerama (no Qt, no Python, no image-decoding library even — see
its own top comment) and measures ~19ms from process start to the window
actually appearing on screen.

**Current state: preview-only, not wired into the real launch flow.**
`x-loader/` shows a static image (light/dark, from `resources/loader-assets/`)
and exits on click or any key — no animation, and no
process-orchestration (launching YATA and waiting for a readiness signal,
the way the removed prototypes did) yet. That's why `run.sh` doesn't
actually show it: there's nothing yet for it to orchestrate.

```sh
./run-loader.sh          # builds (if needed) and previews x-loader
./run-loader.sh --dark   # force dark regardless of desktop preference
./run-loader.sh --light  # force light regardless of desktop preference
```

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

**`./build.sh` is currently broken — it still references `loader-src/`,
which has been removed.** Left unfixed deliberately until `x-loader/` (or
whatever the splash ends up being) actually gets wired into the real
launch flow; packaging it before then would just be packaging dead paths.
Once fixed, it's expected to still do what it says below for `yata-src/`
itself, via
[`pyside6-deploy`](https://doc.qt.io/qtforpython/deployment/deploy-guide.html)
(bundled with PySide6, which drives [Nuitka](https://nuitka.net/) to
compile it into one file); `nuitka`/`patchelf` come from the `build`
dependency group (`uv run --group build ...`), the first build takes a few
minutes, and the resulting binary is large (~60MB, embeds a private Qt) and
Linux-only (produces ELF binaries).

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

- `yata-src/` — application source (Python backend + QML UI in `yata-src/qml/`)
- `x-loader/` — the pure-X11 startup splash preview (`main.c`, `Makefile`,
  `generate_assets.sh`) — see "Startup splash" above; not yet wired into
  `run.sh`/`build.sh`
- `resources/` — non-code assets for the main app, including
  `resources/loader-assets/` (the splash's background images)
- `tests/` — pytest test suite for `yata-src/`; `tests/fixtures/` holds mock data
- `pyproject.toml` — dependencies, managed by `uv`
- `run.sh` / `run-yata.sh` / `run-loader.sh` — run YATA (currently no
  splash), run YATA explicitly, and preview the splash standalone,
  respectively
- `build.sh` — packages `yata-src/` into a standalone binary; currently
  broken (see "Build a standalone binary" above)

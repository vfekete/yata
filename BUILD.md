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

This is equivalent to `uv run python yata-src/main.py`.

## Run the tests

```sh
uv run --group dev pytest
```

## Build a standalone binary

```sh
./build.sh
```

Packages the whole application (Python + QML + a private Qt/Python runtime)
into a single executable, `dist/yata-X.Y.Z` (version taken from
`pyproject.toml`) — copy that one file anywhere and run it directly, no `uv`
or Python install required on the target machine. Uses
[`pyside6-deploy`](https://doc.qt.io/qtforpython/deployment/deploy-guide.html)
(bundled with PySide6), which drives [Nuitka](https://nuitka.net/) to
compile everything into one file; `nuitka` and `patchelf` are pulled in via
the `build` dependency group (`uv run --group build ...`) the first time you
run it. The first build downloads/compiles Nuitka's C build and takes a few
minutes; the resulting binary is large (~60MB) since it embeds a private Qt.
Linux-only for now (produces an ELF binary); re-run after bumping the
version to get a correspondingly-named binary.

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
- `resources/` — non-code assets
- `tests/` — pytest test suite for the Python backend; `tests/fixtures/` holds mock data
- `pyproject.toml` — dependencies, managed by `uv`
- `build.sh` — packages the app into `dist/yata-X.Y.Z`, a standalone binary

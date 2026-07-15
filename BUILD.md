# Building and running YATA

YATA is a Python + QtQuick/QML application managed with [`uv`](https://docs.astral.sh/uv/).
There is no compiled binary to produce; "building" means creating the
project's virtual environment and installing dependencies, which `uv`
handles automatically.

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

## Project layout

- `yata-src/` — application source (Python backend + QML UI in `yata-src/qml/`)
- `resources/` — non-code assets
- `tests/` — pytest test suite for the Python backend
- `pyproject.toml` — dependencies, managed by `uv`

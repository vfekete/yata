#!/usr/bin/env bash
# Packages YATA into ONE distributable file via pyside6-deploy (Nuitka
# under the hood): dist/yata-X.Y.Z. This is the file to run, and what a
# desktop entry's Exec= should point at.
#
# The pure-X11 startup splash (x-loader/) is bundled INSIDE that file as a
# Nuitka onefile data file (--include-data-files, set via the [nuitka]
# extra_args below) rather than shipped as a separate sibling file --
# Nuitka's onefile bootstrap self-extracts included data files into a
# private per-run temp directory at startup and exposes that directory to
# the running program via a "__nuitka_binary_dir" name it injects into
# `builtins`. yata-src/main.py's _maybe_launch_bundled_loader() finds the
# extracted "x-loader-loader" there, chmods it executable, and launches it
# over a private socket -- the same protocol run.sh uses for a source
# checkout (see x-loader/main.c's socket-mode branch), just self-
# orchestrated here instead of shell-scripted. If x-loader isn't found
# there (e.g. this script's own extra_args injection didn't happen for
# some reason), the app still runs fine, just with no splash -- the same
# graceful no-op _maybe_launch_bundled_loader always has for that case.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

VERSION=$(grep -m1 '^version = ' pyproject.toml | sed -E 's/^version = "(.*)"$/\1/')
if [ -z "$VERSION" ]; then
    echo "Could not read version from pyproject.toml" >&2
    exit 1
fi
NAME="yata-$VERSION"

# Catch version drift before shipping: yata-src/main.py's own APP_VERSION
# (gates desktop-entry/icon-cache resync on upgrade -- see
# _ensure_desktop_entry) has to track pyproject.toml's version, or an
# already-installed desktop entry could look "current" to a newer build
# that actually needs a resync. This has drifted silently before.
APP_VERSION=$(grep -m1 '^APP_VERSION = ' yata-src/main.py | sed -E 's/^APP_VERSION = "(.*)"$/\1/')
if [ "$APP_VERSION" != "$VERSION" ]; then
    echo "yata-src/main.py's APP_VERSION ($APP_VERSION) doesn't match pyproject.toml's version ($VERSION) -- bump APP_VERSION to match before building." >&2
    exit 1
fi

ICON="resources/assets/app-icon.png"
if [ ! -s "$ICON" ]; then
    echo "Missing or empty $ICON -- can't build without an app icon." >&2
    exit 1
fi

# Regenerate the Qt resource module so the binary always has the latest
# bundled assets (icon/fonts/SVGs), even if resources_rc.py wasn't
# committed after an asset change.
uv run pyside6-rcc yata-src/resources.qrc -o yata-src/resources_rc.py

# x-loader is plain C -- no Nuitka packaging needed, just compile it (make
# is incremental already, and regenerates its embedded assets.h from the
# background PNGs if either changed -- see x-loader/Makefile).
make -C x-loader

# Clean up any leftover deployment artifacts from a previous/interrupted
# build (pyside6-deploy writes these next to main.py, not in dist/).
rm -rf yata-src/deployment yata-src/pysidedeploy.spec

# --init generates a normal spec file we then edit -- letting pyside6-deploy
# auto-generate one on the fly (like a plain `pyside6-deploy -f --name ...`
# with no -c) gives no chance to inject extra Nuitka args before the real
# compile runs.
uv run --group build pyside6-deploy --init -f --name "$NAME" yata-src/main.py
LOADER_ABS="$(pwd)/x-loader/x-loader"
sed -i -E "s|^extra_args = (.*)|extra_args = \1 --include-data-files=${LOADER_ABS}=x-loader-loader|" yata-src/pysidedeploy.spec

# pyside6-deploy's QML auto-detection (the spec's own "qml_files" line)
# only finds files reachable via yata-src/qml/Main.qml's own static QML
# imports -- a plugin's content, loaded at runtime through a Loader whose
# source is a plain Python-computed QUrl string (see plugin_api.py's
# PluginContent.qml_source), is invisible to that scan. Without this, the
# packaged binary launches, then immediately fails with "No such file or
# directory" the moment it tries to load the plugin's own QML (confirmed
# live against an actual built binary before this was added) -- the .py
# files DO get bundled correctly (Nuitka follows the static import graph
# for those), only the .qml data files were missing. Bundled the same way
# x-loader is above (--include-data-dir, Nuitka's recursive directory
# equivalent of --include-data-files), one per registered plugin (not
# hardcoded to simple_task_list) so a future plugin needs no build.sh
# change here -- just qml_import_dir set on its own Plugin entry.
PLUGIN_QML_ARGS="$(uv run python -c "
import os, sys
sys.path.insert(0, 'yata-src')
import plugins_registry
repo_root = os.getcwd()
for p in plugins_registry.AVAILABLE_PLUGINS.values():
    if p.qml_import_dir:
        rel = os.path.relpath(p.qml_import_dir, repo_root)
        print(f' --include-data-dir={p.qml_import_dir}={rel}', end='')
")"
if [ -n "$PLUGIN_QML_ARGS" ]; then
    sed -i -E "s|^extra_args = (.*)|extra_args = \1${PLUGIN_QML_ARGS}|" yata-src/pysidedeploy.spec
fi

uv run --group build pyside6-deploy -c yata-src/pysidedeploy.spec -f --name "$NAME" yata-src/main.py

mkdir -p dist
mv "yata-src/$NAME.bin" "dist/$NAME"
chmod +x "dist/$NAME"

# pyside6-deploy cleans up its deployment/ build dir on its own but leaves
# the generated spec file behind.
rm -f yata-src/pysidedeploy.spec

echo "Built dist/$NAME"

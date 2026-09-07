#!/usr/bin/env bash
# Packages YATA into two single-file executables via pyside6-deploy (which
# uses Nuitka under the hood): the real app, and its startup loader/splash
# (loader-src) in front of it. Output lands in dist/ as:
#   dist/yata-X.Y.Z       -- the loader. This is the file a user actually
#                            runs (and what a desktop entry's Exec= should
#                            point to) -- it shows the splash immediately,
#                            then finds and launches its sibling below.
#   dist/yata-X.Y.Z-app   -- the real app. loader-src/main.py looks for
#                            exactly this name (its own path + "-app") next
#                            to itself when run with no arguments -- see
#                            loader-src/main.py's _find_sibling_app_binary().
# Both files must ship together, in the same directory, for this to work.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

VERSION=$(grep -m1 '^version = ' pyproject.toml | sed -E 's/^version = "(.*)"$/\1/')
if [ -z "$VERSION" ]; then
    echo "Could not read version from pyproject.toml" >&2
    exit 1
fi
NAME="yata-$VERSION"

# Regenerate both Qt resource modules so each binary always has its latest
# bundled assets, even if resources_rc.py wasn't committed for one of them.
uv run pyside6-rcc yata-src/resources.qrc -o yata-src/resources_rc.py
uv run pyside6-rcc loader-src/resources.qrc -o loader-src/resources_rc.py

# Clean up any leftover deployment artifacts from a previous/interrupted
# build (pyside6-deploy writes these next to each main.py, not in dist/).
rm -rf yata-src/deployment yata-src/pysidedeploy.spec
rm -rf loader-src/deployment loader-src/pysidedeploy.spec

uv run --group build pyside6-deploy -f --name "$NAME-app" yata-src/main.py
uv run --group build pyside6-deploy -f --name "$NAME" loader-src/main.py

mkdir -p dist
mv "yata-src/$NAME-app.bin" "dist/$NAME-app"
mv "loader-src/$NAME.bin" "dist/$NAME"
chmod +x "dist/$NAME-app" "dist/$NAME"

# pyside6-deploy cleans up its deployment/ build dir on its own but leaves
# the generated spec file behind, for each.
rm -f yata-src/pysidedeploy.spec loader-src/pysidedeploy.spec

echo "Built dist/$NAME (loader) and dist/$NAME-app (real app) -- run dist/$NAME"

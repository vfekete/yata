#!/usr/bin/env bash
# Packages YATA into a single-file executable via pyside6-deploy (which
# uses Nuitka under the hood), named yata-X.Y.Z after the current version
# in pyproject.toml. Output lands in dist/.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

VERSION=$(grep -m1 '^version = ' pyproject.toml | sed -E 's/^version = "(.*)"$/\1/')
if [ -z "$VERSION" ]; then
    echo "Could not read version from pyproject.toml" >&2
    exit 1
fi
NAME="yata-$VERSION"

# Regenerate the Qt resource module so the binary always has the latest
# bundled assets (fonts, etc.) even if resources_rc.py wasn't committed.
uv run pyside6-rcc yata-src/resources.qrc -o yata-src/resources_rc.py

# Clean up any leftover deployment artifacts from a previous/interrupted
# build (pyside6-deploy writes these next to main.py, not in dist/).
rm -rf yata-src/deployment yata-src/pysidedeploy.spec

uv run --group build pyside6-deploy -f --name "$NAME" yata-src/main.py

mkdir -p dist
mv "yata-src/$NAME.bin" "dist/$NAME"
chmod +x "dist/$NAME"

# pyside6-deploy cleans up its deployment/ build dir on its own but leaves
# the generated spec file behind.
rm -f yata-src/pysidedeploy.spec

echo "Built dist/$NAME"

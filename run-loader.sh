#!/usr/bin/env bash
# Previews the startup splash on its own (background + spinner, see
# x-loader/main.c), dismissed by clicking it or pressing any key.
#
# Builds (if needed) and runs the pure-X11 loader (x-loader/) -- two
# Qt-based prototypes (a PySide6 one, then a from-scratch C++/QML rewrite
# against a real Qt6 install) were tried and abandoned: both had Qt's own
# startup/init cost baked in regardless of language or optimization level
# (measured live at 26-53s before a window even appeared, even from an
# -O3+LTO Release C++ build). x-loader/ links only Xlib/Xinerama and
# measures ~19ms from process start to the window actually appearing.
#
# In real use it's launched alongside YATA with a readiness socket
# (YATA_LOADER_SOCKET) -- by run.sh for a source checkout, or by the
# packaged binary itself (build.sh bundles it, see main.py's
# _maybe_launch_bundled_loader). Run standalone like this, with no socket,
# it just holds the fully-faded-in image until you dismiss it yourself (see
# fade_set_auto_close in effects.c).
#
# By default the light/dark background follows the desktop's own preference.
# Pass --light or --dark to force one, e.g. `./run-loader.sh --dark`.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
make -C x-loader >&2
exec ./x-loader/x-loader "$@"

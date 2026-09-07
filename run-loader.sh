#!/usr/bin/env bash
# Previews the startup splash on its own -- static image only for now (see
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
# x-loader has no process-orchestration (launching YATA and waiting for a
# readiness signal) or animation yet -- this script only previews the
# static image. run.sh (the full loader-then-YATA flow) and build.sh
# (packaging) still reference the removed Qt prototypes and are broken
# pending that follow-up work.
#
# By default the light/dark background follows the desktop's own preference.
# Pass --light or --dark to force one, e.g. `./run-loader.sh --dark`.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
make -C x-loader >&2
exec ./x-loader/x-loader "$@"

#!/usr/bin/env bash
# Runs YATA. This used to also show a startup splash in front of it
# (loader-src/, then loader-cpp/ -- both since removed after turning out to
# have Qt's own startup cost baked in regardless of language/optimization
# level, see run-loader.sh and x-loader/main.c). x-loader/ (the pure-X11
# replacement) has no process-orchestration yet -- it can't launch YATA and
# wait for a readiness signal the way those did -- so for now this is
# exactly run-yata.sh; see run-loader.sh to preview the splash on its own.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
exec ./run-yata.sh "$@"

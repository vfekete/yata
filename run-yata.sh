#!/usr/bin/env bash
# Runs YATA directly, with no startup loader/splash in front of it. Use
# this for normal development (fast iteration, no splash to wait through)
# or when you specifically don't want the loader involved. See run.sh for
# the loader+yata orchestrated version, and run-loader.sh to preview the
# splash on its own.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
uv run python yata-src/main.py "$@"

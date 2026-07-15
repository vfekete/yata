#!/usr/bin/env bash
# Runs YATA via uv, which creates/updates the project's virtual environment
# on demand. See BUILD.md for details.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
uv run python yata-src/main.py "$@"

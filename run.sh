#!/usr/bin/env bash
# Runs YATA with the startup splash (x-loader/) in front of it. The two
# talk over a private Unix domain socket (YATA_LOADER_SOCKET): YATA sends
# "starting" as soon as it connects, then "running" once every window from
# this launch is actually shown on screen (see x-loader/main.c's
# socket-mode branch and yata-src/main.py's _connect_to_loader /
# _send_loader_message). The loader fades out and exits the moment it hears
# "running", after 2 minutes if it never does, or immediately if YATA
# disconnects without ever sending it (e.g. a crash).
#
# --backup/-b and -h/--help make YATA exit immediately without opening any
# window (see main.py) -- skip the splash entirely for those rather than
# leaving it on screen for up to 2 minutes waiting for a "running" that's
# never coming.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

for arg in "$@"; do
    case "$arg" in
    -b | --backup | -h | --help)
        exec ./run-yata.sh "$@"
        ;;
    esac
done

make -C x-loader >&2

socket_path="$(mktemp -u "${XDG_RUNTIME_DIR:-/tmp}/yata-loader-XXXXXXXX.sock")"
export YATA_LOADER_SOCKET="$socket_path"
trap 'rm -f "$socket_path"' EXIT

./x-loader/x-loader &
loader_pid=$!

yata_status=0
./run-yata.sh "$@" || yata_status=$?

wait "$loader_pid" 2>/dev/null || true

exit "$yata_status"

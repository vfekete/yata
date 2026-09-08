#!/usr/bin/env bash
# Swaps the REAL YATA task data (~/.local/share/yata, or $XDG_DATA_HOME/yata)
# for screenshot-friendly mock data, in place -- for taking manual/
# interactive screenshots of the real, already-configured app.
#
# Unlike scripts/capture_screenshots.py (which drives fully isolated,
# throwaway XDG_DATA_HOME/XDG_CONFIG_HOME instances and never touches real
# files), this script mutates real files on disk, on purpose: it replaces
# each window's tasks.json content with mock data so it's ready for a
# screenshot. windows.json itself (which windows exist, their tags,
# open/deleted state) is never touched.
#
# It also snapshots every window's *settings* file (position, size, theme,
# tint, border color, opacity, font scale -- yata.conf / instances/<id>.conf)
# before doing anything, purely so that whatever you change afterwards while
# posing a window for a screenshot (drag it somewhere nicer, pick a tint,
# set a border color, zoom the font) can be put back exactly as it was --
# this script itself never modifies those files.
#
# Usage:
#   scripts/mock-env-init.sh
#
# Safe by construction:
#   - Before ever touching a tracked file, its current content (or the fact
#     that it didn't exist yet) is recorded under a backup directory
#     (.mock-backup/ next to the real data) -- nothing is ever discarded.
#   - If that backup already exists (mock data looks already active, e.g.
#     from an earlier run of this script), it asks whether to refresh the
#     mock task data again or restore everything from backup, rather than
#     guessing.
#   - Deleted windows (windows.json entries with "deleted": true) are left
#     alone entirely -- they aren't visible, so there's nothing to mock.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FIXTURE="$REPO_ROOT/tests/fixtures/mock_tasks.json"
DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/yata"
CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/yata"
WINDOWS_JSON="$DATA_DIR/windows.json"
BACKUP_DIR="$DATA_DIR/.mock-backup"
MANIFEST="$BACKUP_DIR/manifest.txt"

if [[ ! -f "$FIXTURE" ]]; then
    echo "error: mock fixture not found at $FIXTURE" >&2
    exit 1
fi

# Non-deleted window ids from windows.json, excluding "default" (which
# always uses the legacy top-level paths, never instances/<id>). Empty on a
# fresh install that has no windows.json yet.
other_window_ids() {
    if [[ -f "$WINDOWS_JSON" ]]; then
        jq -r '.[] | select(.deleted == false and .id != "default") | .id' "$WINDOWS_JSON"
    fi
}

# Every tasks.json path currently in play: "task <path>" lines.
task_entries() {
    printf 'task %s\n' "$DATA_DIR/tasks.json"
    other_window_ids | while IFS= read -r id; do
        printf 'task %s\n' "$DATA_DIR/instances/$id/tasks.json"
    done
}

# Every settings file path currently in play: "setting <path>" lines.
setting_entries() {
    printf 'setting %s\n' "$CONFIG_DIR/yata.conf"
    other_window_ids | while IFS= read -r id; do
        printf 'setting %s\n' "$CONFIG_DIR/instances/$id.conf"
    done
}

backup_path_for() {
    local path="$1"
    if [[ "$path" == "$DATA_DIR"/* ]]; then
        printf '%s\n' "$BACKUP_DIR/data/${path#"$DATA_DIR"/}"
    elif [[ "$path" == "$CONFIG_DIR"/* ]]; then
        printf '%s\n' "$BACKUP_DIR/config/${path#"$CONFIG_DIR"/}"
    else
        echo "error: don't know how to back up $path" >&2
        exit 1
    fi
}

do_backup_and_populate() {
    mkdir -p "$BACKUP_DIR"
    : > "$MANIFEST"
    while IFS=' ' read -r kind path; do
        bpath="$(backup_path_for "$path")"
        mkdir -p "$(dirname "$bpath")"
        if [[ -f "$path" ]]; then
            cp "$path" "$bpath"
            echo "present $kind $path" >> "$MANIFEST"
        else
            echo "absent $kind $path" >> "$MANIFEST"
        fi
        if [[ "$kind" == "task" ]]; then
            mkdir -p "$(dirname "$path")"
            cp "$FIXTURE" "$path"
        fi
    done < <(task_entries; setting_entries)
    echo "Mock data is active in $DATA_DIR."
    echo "Your real tasks and window settings (position, size, theme, colors) are backed up under $BACKUP_DIR."
    echo "Restart YATA to see the mock data. Run this script again when you're done to restore everything."
}

do_replace_mock() {
    while IFS=' ' read -r state kind path; do
        [[ "$kind" == "task" ]] || continue
        mkdir -p "$(dirname "$path")"
        cp "$FIXTURE" "$path"
    done < "$MANIFEST"
    echo "Mock data refreshed. Restart YATA to see it."
}

do_restore() {
    while IFS=' ' read -r state kind path; do
        case "$state" in
        present)
            cp "$(backup_path_for "$path")" "$path"
            ;;
        absent)
            rm -f "$path"
            ;;
        esac
    done < "$MANIFEST"
    rm -rf "$BACKUP_DIR"
    echo "Your real tasks and window settings have been restored. Restart YATA to see it."
}

if pgrep -f "yata-src/main.py" > /dev/null 2>&1; then
    echo "warning: YATA appears to be running -- quit it first, or its next save" >&2
    echo "         may overwrite these changes (or your restored data)." >&2
fi

if [[ -f "$MANIFEST" ]]; then
    echo "A mock-data backup already exists at $BACKUP_DIR -- mock data looks active."
    read -rp "Replace the mock data again, or restore your real tasks/settings from backup? [r]eplace/[b]ackup restore/[c]ancel: " choice
    case "$choice" in
    r | R) do_replace_mock ;;
    b | B) do_restore ;;
    *) echo "Cancelled."; exit 0 ;;
    esac
else
    do_backup_and_populate
fi

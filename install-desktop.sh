#!/usr/bin/env bash
# Installs YATA's desktop entry and icon so GNOME shows the correct icon in
# the Alt+Tab switcher and application launcher.
# Run once after cloning; re-run if you move the repo.
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ICON_DIR="$HOME/.local/share/icons/hicolor/256x256/apps"
APPS_DIR="$HOME/.local/share/applications"

mkdir -p "$ICON_DIR" "$APPS_DIR"

cp "$REPO/resources/icon.png" "$ICON_DIR/yata.png"

VERSION=$(grep '^version' "$REPO/pyproject.toml" | head -1 | sed 's/version = "\(.*\)"/\1/')
sed \
    -e "s|Exec=YATA_EXEC_PLACEHOLDER|Exec=$REPO/run.sh|" \
    -e "s|X-AppVersion=YATA_VERSION_PLACEHOLDER|X-AppVersion=$VERSION|" \
    "$REPO/resources/yata.desktop" > "$APPS_DIR/yata.desktop"

# Refresh icon and desktop caches so GNOME picks up the changes immediately.
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true
update-desktop-database "$APPS_DIR" 2>/dev/null || true

echo "Done. YATA desktop entry installed."
echo "  Icon : $ICON_DIR/yata.png"
echo "  Entry: $APPS_DIR/yata.desktop"

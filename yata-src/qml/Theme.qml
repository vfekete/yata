pragma Singleton
import QtQuick

// Each named tint recreates the look of a specific old CRT/terminal display
// (green/amber phosphor, paperwhite monitor, teletype paper) and colors
// task status, backgrounds, buttons and fields to match. "none" is the safe
// default: it keeps the original plain look (respects the light/dark
// toggle, no color wash, no monospace font).
QtObject {
    readonly property bool dark: appSettings.themeMode === "dark"
    readonly property string tintName: appSettings.themeTint

    // Base task text size, scaled by the user's Ctrl+/Ctrl- font zoom
    // (appSettings.fontScale). The day-section header (1.5x this) and the
    // status/hover icons (2x this) size themselves off this same value, so
    // zooming scales the whole task list together.
    readonly property int taskFontPixelSize: Math.round(14 * appSettings.fontScale)

    readonly property var palettes: ({
        "none": {
            background: "transparent",
            active: dark ? "#f3f4f6" : "#111827",
            done: dark ? "#9ca3af" : "#6b7280",
            cancelled: dark ? "#9ca3af" : "#6b7280",
            muted: dark ? "#9ca3af" : "#6b7280",
            accent: "#64748b",
            field: dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(0, 0, 0, 0.05),
            hover: dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(0, 0, 0, 0.06),
            fontFamily: "Noto Sans"
        },
        // Classic green phosphor terminal.
        "green": {
            background: Qt.rgba(0, 0.078, 0, 0.90),
            active: "#33FF33",
            done: "#1FAA1F",
            cancelled: "#4D5D4D",
            muted: "#3A7A3A",
            accent: "#33FF33",
            field: Qt.rgba(0.2, 1, 0.2, 0.08),
            hover: Qt.rgba(0.2, 1, 0.2, 0.12),
            fontFamily: "VT323",
            labelDone: "#21C821",
            labelCancelled: "#149114"
        },
        // Classic amber phosphor terminal.
        "goldenrod": {
            background: Qt.rgba(0.094, 0.059, 0, 0.90),
            active: "#FFB000",
            done: "#CC8400",
            cancelled: "#6B5637",
            muted: "#A37325",
            accent: "#FFB000",
            field: Qt.rgba(1, 0.69, 0, 0.08),
            hover: Qt.rgba(1, 0.69, 0, 0.12),
            fontFamily: "VT323",
            labelDone: "#D9960A",
            labelCancelled: "#9B6900"
        },
        // Paperwhite CRT: white phosphor on near-black.
        "white": {
            background: Qt.rgba(0.039, 0.039, 0.039, 0.90),
            active: "#F0F0F0",
            done: "#AFAFAF",
            cancelled: "#5A5A5A",
            muted: "#8A8A8A",
            accent: "#F0F0F0",
            field: Qt.rgba(1, 1, 1, 0.08),
            hover: Qt.rgba(1, 1, 1, 0.12),
            fontFamily: "VT323",
            labelDone: "#ADADAD",
            labelCancelled: "#828282"
        },
        // Teletype paper terminal: dark ink on cream paper (the inverse of
        // the phosphor-on-black tints above).
        "black": {
            background: Qt.rgba(0.929, 0.902, 0.827, 0.94),
            active: "#2B2620",
            done: "#6B6152",
            cancelled: "#A39A86",
            muted: "#8A8060",
            accent: "#2B2620",
            field: Qt.rgba(0, 0, 0, 0.05),
            hover: Qt.rgba(0, 0, 0, 0.08),
            fontFamily: "VT323",
            labelDone: "#4C4036",
            labelCancelled: "#706055"
        }
    })

    readonly property var current: palettes[tintName] !== undefined ? palettes[tintName] : palettes["none"]

    readonly property color contentBackground: current.background
    readonly property color textColor: current.active
    readonly property color doneColor: current.done
    readonly property color cancelledColor: current.cancelled
    readonly property color mutedTextColor: current.muted
    readonly property color accentColor: current.accent
    readonly property color borderColor: current.accent
    readonly property color fieldColor: current.field
    readonly property color hoverColor: current.hover
    readonly property string fontFamily: current.fontFamily

    // One global, user-set opacity (appSettings.opacityPercent, 5-100)
    // applies to every tint identically, rather than each tint carrying its
    // own fixed value.
    readonly property real windowOpacity: appSettings.opacityPercent / 100.0

    // Completion label status-word colors. "none" uses semantic green/red;
    // tinted themes use palette-tuned colors at matching luminance in the
    // tint's hue (done brighter, cancelled dimmer, same ratio as green/red).
    readonly property color completedDoneLabelColor: tintName === "none" ? "#22c55e" : current.labelDone
    readonly property color completedCancelledLabelColor: tintName === "none" ? "#ef4444" : current.labelCancelled

    // Status indicator icons shown in front of non-active tasks. "none"
    // uses literal green/red; CRT tints reuse their own done/cancelled
    // colors, which are already tint-native (and check already reads
    // brighter than cross for every CRT tint by design).
    readonly property color checkIconColor: tintName === "none" ? "#22c55e" : current.done
    readonly property color crossIconColor: tintName === "none" ? "#ef4444" : current.cancelled

    // Markdown hyperlink color. "none" gets a legible blue tuned per
    // light/dark mode (the default Qt link blue, 0x0000FF, is unreadable on
    // a dark background); CRT tints reuse their own accent color, which
    // already contrasts against that tint's background.
    readonly property color linkColor: tintName === "none" ? (dark ? "#22d3ee" : "#0369a1") : current.accent

    // Glow colours for FilterBar toggle buttons.
    // "none" uses fixed cyan (on) / white (hover) — theme-independent signals.
    // CRT tints use their own accent colour so the glow stays on-palette;
    // hover gets a lightened shade for the same on-vs-hover distinction.
    readonly property color filterGlowColor: tintName === "none" ? "#00FFFF" : current.accent
    readonly property color filterHoverColor: tintName === "none" ? "#FFFFFF" : Qt.lighter(current.accent, 1.4)
}

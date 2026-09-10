import QtQuick

// Same contract/filename convention as plugins/simple_task_list/qml/
// ThemeImpl.qml (see that file's own header for why this can't be named
// Theme.qml) — one instance per window, injected as the "Theme" context
// property by main.py before this plugin's own content QML loads. A
// smaller palette than the task list's own: no per-task status colors
// (done/cancelled/link/etc.) since this plugin has no such concept, but
// the same five named tints (dark mode default "none" plus four CRT
// looks) so a timesheet window can visually match whatever the rest of
// the app is using.
QtObject {
    readonly property bool dark: appSettings.themeMode === "dark"
    readonly property string tintName: appSettings.themeTint

    // Scaled by the host's own generic zoom (hostSettings.zoomLevel) —
    // same mechanism/reasoning simple_task_list's own taskFontPixelSize
    // documents; kept under the same property name for consistency across
    // plugins even though nothing here is strictly a "task".
    readonly property int taskFontPixelSize: Math.round(14 * hostSettings.zoomLevel)

    readonly property var palettes: ({
        "none": {
            background: "transparent",
            active: dark ? "#f3f4f6" : "#111827",
            muted: dark ? "#9ca3af" : "#6b7280",
            accent: "#64748b",
            field: dark ? Qt.rgba(1, 1, 1, 0.10) : Qt.rgba(0, 0, 0, 0.05),
            hover: dark ? Qt.rgba(1, 1, 1, 0.08) : Qt.rgba(0, 0, 0, 0.06),
            fontFamily: "Noto Sans"
        },
        "green": {
            background: Qt.rgba(0, 0.078, 0, 0.90),
            active: "#33FF33",
            muted: "#3A7A3A",
            accent: "#33FF33",
            field: Qt.rgba(0.2, 1, 0.2, 0.08),
            hover: Qt.rgba(0.2, 1, 0.2, 0.12),
            fontFamily: "VT323"
        },
        "goldenrod": {
            background: Qt.rgba(0.094, 0.059, 0, 0.90),
            active: "#FFB000",
            muted: "#A37325",
            accent: "#FFB000",
            field: Qt.rgba(1, 0.69, 0, 0.08),
            hover: Qt.rgba(1, 0.69, 0, 0.12),
            fontFamily: "VT323"
        },
        "white": {
            background: Qt.rgba(0.039, 0.039, 0.039, 0.90),
            active: "#F0F0F0",
            muted: "#8A8A8A",
            accent: "#F0F0F0",
            field: Qt.rgba(1, 1, 1, 0.08),
            hover: Qt.rgba(1, 1, 1, 0.12),
            fontFamily: "VT323"
        },
        "black": {
            background: Qt.rgba(0.929, 0.902, 0.827, 0.94),
            active: "#2B2620",
            muted: "#8A8060",
            accent: "#2B2620",
            field: Qt.rgba(0, 0, 0, 0.05),
            hover: Qt.rgba(0, 0, 0, 0.08),
            fontFamily: "VT323"
        }
    })

    readonly property var current: palettes[tintName] !== undefined ? palettes[tintName] : palettes["none"]

    readonly property color contentBackground: current.background
    readonly property color textColor: current.active
    readonly property color mutedTextColor: current.muted
    readonly property color accentColor: current.accent
    readonly property color borderColor: current.accent
    readonly property color fieldColor: current.field
    readonly property color hoverColor: current.hover
    readonly property string fontFamily: current.fontFamily

    // Same "custom border color overrides the theme's own accent, under
    // the 'none' tint only" convention simple_task_list's own
    // effectiveGlowColor established (r-5.md) — this plugin's toggle-pill
    // period selector and hover glows follow it the same way.
    readonly property color effectiveGlowColor: (tintName === "none" && hostSettings.borderColor !== "") ? hostSettings.borderColor : accentColor
    readonly property color effectiveGlowShadowColor: Qt.lighter(effectiveGlowColor, 1.4)

    readonly property real windowOpacity: appSettings.opacityPercent / 100.0

    // Fixed, theme-independent — same reasoning TaskDelegate's own
    // checkIconColor/crossIconColor use literal green/red under "none":
    // ON-SITE/REMOTE and the abandoned-session flag are semantic signals,
    // not decorative accents.
    readonly property color onSiteColor: "#22c55e"
    readonly property color remoteColor: "#0ea5e9"
    readonly property color abandonedColor: "#ef4444"
}

import QtQuick

// Filename is deliberately NOT Theme.qml, even though every other .qml file
// still refers to it as the bare identifier "Theme" — see main.py's
// _make_window, which loads this file but injects the result as a context
// property literally named "Theme".
//
// NOT a pragma Singleton: multi-window support (r-3.md) needs one Theme
// instance per window, each bound to that window's own appSettings (a
// singleton is one instance for the whole QQmlEngine, shared by every
// window — incompatible with "every window remembers its... settings
// separately"). Instead each window's context gets its own Theme instance
// created explicitly and exposed as that "Theme" context property.
//
// The filename must stay off "Theme.qml" specifically because Qt's
// implicit-directory-import still registers a TYPE named "Theme" for any
// sibling file called Theme.qml regardless of pragma Singleton — so once
// the singleton declaration was removed, "Theme.qml" left behind a
// same-named, no-longer-registered TYPE that collided with the "Theme"
// CONTEXT PROPERTY. QML's compiled-bindings path resolved the (broken) type
// reference instead of falling back to the context property, silently
// leaving every Theme.* binding undefined — while dynamically-evaluated
// expressions (e.g. via QQmlExpression) resolved correctly, which is what
// made this so confusing to track down: reading a Theme property directly
// off the live Python object always worked, but any QML binding elsewhere
// in the app reading the exact same property through the identifier
// "Theme" silently got `undefined` and rendered with default Qt colors
// (black text, transparent-turned-white backgrounds) instead. Renaming the
// file (content otherwise unchanged) removes the type/property name clash
// entirely. Confirmed via a from-scratch reproduction: same context, same
// context-property wiring, only the loaded file's name changed.
//
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

    // r-5.md: once a window has its own custom border color (r-4.md), the
    // pushed FilterButton glow and markdown link color/glow follow that
    // same color instead of their own theme defaults — one shared "this
    // window's identity color" instead of three independently-themed
    // accents. "" (no custom border color, the default) falls back to each
    // one's own existing theme color exactly as before.
    //
    // Only under the "none" tint, though — a CRT tint's own accent-derived
    // colors (filterGlowColor/linkColor above, current.accent, etc.) are
    // already tuned per-tint for legibility against that tint's background,
    // and a user-picked color can clash with them arbitrarily. Per explicit
    // follow-up request: under any tint, only the border itself takes the
    // custom color (Main.qml's windowBorder/tagLabelText — untouched by
    // this file, always follows appSettings.borderColor regardless of
    // tint); buttons/links keep the tint's own color exactly as they did
    // before r-5.md existed.
    readonly property color effectiveGlowColor: (tintName === "none" && appSettings.borderColor !== "") ? appSettings.borderColor : filterGlowColor
    readonly property color effectiveLinkColor: (tintName === "none" && appSettings.borderColor !== "") ? appSettings.borderColor : linkColor

    // Shadow-only variants, lightened the same way filterHoverColor already
    // lightens its own base accent (Qt.lighter(..., 1.4)) — a custom border
    // color can be any brightness the user picks (a mid-tone pink has much
    // lower perceived luminance than the fixed "#00FFFF" every hover glow
    // used before r-5.md), so the base color alone isn't reliably vivid
    // enough to read as a strong glow at the same shadowBlur/shadowOpacity.
    // The base effectiveGlowColor/effectiveLinkColor stay untouched for
    // fill/text/border usage — only the glow itself gets lightened.
    readonly property color effectiveGlowShadowColor: Qt.lighter(effectiveGlowColor, 1.4)
    readonly property color effectiveLinkShadowColor: Qt.lighter(effectiveLinkColor, 1.4)

    // LinksView's "ACTIVE" status tag (see StatusTag.qml). Spec: "white with
    // glow; for tints, color follows tint color but has adequate brightness
    // to express white". A literal white would be unreadable in "none"
    // theme's light mode, so "none" reuses textColor (already the correct
    // near-white in dark mode / near-black in light mode for legibility).
    // CRT tints reuse accentColor — each tint's own brightest/most prominent
    // color, which for the inverted "black" (dark-ink-on-cream) tint is
    // correctly its darkest ink color, not literal white, since that's what
    // reads as "the prominent accent" against that tint's own background.
    readonly property color activeTagColor: tintName === "none" ? textColor : accentColor

    // vfe: default spacing between items:
    readonly property int nonActiveActionIconGap: Math.round(taskFontPixelSize * 0.1)

}

import QtQuick
import QtQuick.Window

// A single, app-wide floating preview shown while a task is being dragged
// (TaskDelegate.qml's row-wide DragHandler) — an independent top-level
// window (not an Item nested inside any YATA window) specifically so it
// stays visible even once the pointer leaves the source window's own
// bounds, e.g. while hovering over a different YATA window mid cross-window
// move. Built once in main.py and reused for every drag, regardless of
// which window/row started it — see WindowManager's
// showDragGhost/moveDragGhost/hideDragGhost.
//
// Deliberately theme-independent (fixed dark/cyan styling, not Theme.*):
// Theme is a per-window context property (see ThemeImpl.qml's own comment
// on why it can't be a singleton), and this window isn't "owned" by any one
// YATA window in particular, so it doesn't have one theme to consistently
// borrow.
Window {
    id: ghost
    // WindowTransparentForInput alone stops it from *receiving* clicks, but
    // not from taking window focus/activation the instant it's mapped — on
    // X11 that focus change silently cancelled the DragHandler's active
    // pointer grab in the source window the moment a drag started, breaking
    // the whole gesture (not just the ghost) the instant showDragGhost()
    // was called. WindowDoesNotAcceptFocus is what actually prevents that.
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
           | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput
    color: "transparent"
    visible: false

    property string taskText: ""
    property string status: "active"

    // label.width, NOT label.implicitWidth — implicitWidth is the full
    // unclamped/un-elided text's natural width (can be huge for a long
    // task), while label.width is already capped to 320 below and is what
    // actually determines the visible (possibly elided) text's on-screen
    // extent. Sizing off implicitWidth made this window balloon out far
    // past the elided text it was showing for any sufficiently long task.
    width: label.width + 20
    height: label.implicitHeight + 14

    Rectangle {
        anchors.fill: parent
        radius: 6
        color: "#1e1e1e"
        opacity: 0.9
        border.color: "#00FFFF"
        border.width: 1

        Text {
            id: label
            anchors.centerIn: parent
            width: Math.min(implicitWidth, 320)
            text: ghost.taskText
            color: "#f0f0f0"
            font.pixelSize: 14
            font.strikeout: ghost.status !== "active"
            elide: Text.ElideRight
            wrapMode: Text.NoWrap
        }
    }
}

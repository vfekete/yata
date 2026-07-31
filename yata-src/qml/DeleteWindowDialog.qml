import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Confirmation dialog for soft-deleting a YATA window from YatasView's
// ACTIVE row (WindowManager.deleteWindow) — moves it to the DELETED
// category without touching its data, recoverable later via Re-create, or
// permanently discarded via PurgeWindowDialog. Must be theme-colored but
// NOT affected by the opacity slider — comes for free here: DialogWindow is
// its own real top-level window (see its own comment), not even part of
// the opacity-affected content wrapper Item's tree in the first place (same
// reasoning ThemeMenu's popups relied on for the old in-window Dialog).
DialogWindow {
    id: root
    title: qsTr("Delete window?")
    // Scales with font zoom like every other sized-by-font element in this
    // app (e.g. ThemeMenu's width) — a fixed pixel width didn't grow with
    // Ctrl+=/Ctrl+- zoom, so at a larger zoom the text ran right up to (and
    // past) the dialog's edges.
    contentWidth: Math.max(300, Math.round(Theme.taskFontPixelSize * 26))

    property string targetId: ""
    property string targetTag: ""
    signal confirmed(string windowId)

    function openFor(windowId, tag) {
        root.targetId = windowId
        root.targetTag = tag
        root.open()
    }

    onAccepted: root.confirmed(root.targetId)

    Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: qsTr("Are you sure you want to delete “%1”?").arg(root.targetTag)
        color: Theme.textColor
        font.pixelSize: Theme.taskFontPixelSize
    }

    Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: qsTr("It moves to the Deleted list — its tasks and settings are kept, and you can Re-create it from there, or Purge it to remove them for good.")
        color: Theme.mutedTextColor
        font.pixelSize: Theme.taskFontPixelSize
    }
}

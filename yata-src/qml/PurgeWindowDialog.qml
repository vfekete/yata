import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Confirmation dialog for permanently purging a YATA window from YatasView's
// DELETED row (WindowManager.purgeWindow) — removes its registry entry and
// deletes its on-disk tasks/settings for good. Unlike DeleteWindowDialog
// (soft-delete, fully recoverable) this one is genuinely irreversible, so
// the wording says so plainly and there's no "keep the data" choice to
// offer — purge always removes it.
DialogWindow {
    id: root
    title: qsTr("Purge window?")
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
        text: qsTr("Are you sure you want to permanently purge “%1”?").arg(root.targetTag)
        color: Theme.textColor
        font.pixelSize: Theme.taskFontPixelSize
    }

    Label {
        text: qsTr("Its tasks and settings are deleted for good. This action cannot be undone.")
        color: Theme.mutedTextColor
        wrapMode: Text.Wrap
        Layout.fillWidth: true
        font.pixelSize: Theme.taskFontPixelSize
    }
}

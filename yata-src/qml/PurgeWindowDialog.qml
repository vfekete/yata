import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

HostDialogWindow {
    id: root
    title: qsTr("Purge window?")

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
        color: root.chromeTextColor
        font.family: root.chromeFontFamily
        font.pixelSize: root.chromeFontPixelSize
    }

    Label {
        text: qsTr("Its tasks and settings are deleted for good. This action cannot be undone.")
        color: root.chromeMutedTextColor
        wrapMode: Text.Wrap
        Layout.fillWidth: true
        font.family: root.chromeFontFamily
        font.pixelSize: root.chromeFontPixelSize
    }
}

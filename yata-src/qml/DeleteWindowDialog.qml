import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

HostDialogWindow {
    id: root
    title: qsTr("Delete window?")

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
        color: root.chromeTextColor
        font.family: root.chromeFontFamily
        font.pixelSize: root.chromeFontPixelSize
    }

    Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: qsTr("It moves to the Deleted list — its tasks and settings are kept, and you can Re-create it from there, or Purge it to remove them for good.")
        color: root.chromeMutedTextColor
        font.family: root.chromeFontFamily
        font.pixelSize: root.chromeFontPixelSize
    }
}

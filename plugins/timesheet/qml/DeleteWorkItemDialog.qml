import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Confirmation dialog for deleting a work item — spec: "Work item can be
// deleted, but confirmation of user is required." Soft-delete (see
// storage.py's WorkItem.deleted docstring for why): past sessions are
// kept for summary/PDF accuracy, it just drops out of the active list.
DialogWindow {
    id: root
    title: qsTr("Delete work item?")

    property string targetId: ""
    property string targetName: ""
    signal confirmed(string itemId)

    function openFor(itemId, name) {
        root.targetId = itemId
        root.targetName = name
        root.open()
    }

    onAccepted: root.confirmed(root.targetId)

    Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: qsTr("Are you sure you want to delete “%1”?").arg(root.targetName)
        color: Theme.textColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }

    Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: qsTr("It disappears from the list, but hours already logged against it stay counted in summaries and PDF exports.")
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }
}

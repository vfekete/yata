import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

DialogWindow {
    id: root
    title: qsTr("NOTE")
    contentWidth: Math.max(300, Math.round(Theme.taskFontPixelSize * 28))

    property string taskId: ""
    property string pendingStatus: ""

    function openFor(taskId, status, existingNote) {
        root.taskId = taskId
        root.pendingStatus = status
        noteField.text = existingNote
        root.open()
    }

    onAccepted: {
        taskModel.setNote(root.taskId, noteField.text)
        taskModel.setStatus(root.taskId, root.pendingStatus)
    }

    ScrollView {
        Layout.fillWidth: true
        Layout.preferredHeight: Math.round(Theme.taskFontPixelSize * 8)
        clip: true

        TextArea {
            id: noteField
            wrapMode: TextArea.Wrap
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            placeholderText: qsTr("Markdown note…")
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }
        }
    }
}

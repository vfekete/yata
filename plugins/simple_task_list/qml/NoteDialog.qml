import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Opened automatically (r-6.md) once a press-and-hold on a task's DONE/
// CANCEL icon (HoldToNoteButton.qml) fills its progress ring — lets the
// user attach an optional markdown note explaining the state change
// before it's actually applied. Same DialogWindow base and openFor()/
// onAccepted shape as DeleteWindowDialog.qml; the only real difference is
// a multi-line TextArea instead of plain Labels.
DialogWindow {
    id: root
    title: qsTr("NOTE")
    contentWidth: Math.max(300, Math.round(Theme.taskFontPixelSize * 28))

    property string taskId: ""
    // "done" | "cancelled" — whichever icon was held; applied on accept,
    // never on reject, so cancelling never changes the task's status.
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

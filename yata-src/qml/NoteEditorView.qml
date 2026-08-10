import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Shown instead of the task ListView (r-6.md) while a task's note is being
// viewed/edited — reached by clicking a completed task's note icon
// (TaskDelegate.qml). Single always-editable textbox pre-filled with the
// task's current raw markdown note; OK saves, CANCEL discards, both
// return to the task list (see Main.qml's noteEditorVisible/
// listView.noteEditorTaskId wiring).
Item {
    id: root
    property string taskId: ""
    signal closed()

    // Only reloads from the model when the TARGET task actually changes —
    // not on every Links/Yatas cover/uncover (this view stays mounted with
    // visible:false while either of those is shown on top, per Main.qml's
    // own comment), which would otherwise wipe in-progress edits on every
    // round trip through them.
    onTaskIdChanged: noteField.text = root.taskId !== "" ? taskModel.noteFor(root.taskId) : ""

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        ScrollView {
            Layout.fillWidth: true
            Layout.fillHeight: true
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

        RowLayout {
            Layout.alignment: Qt.AlignRight
            spacing: 8

            Button {
                text: qsTr("Cancel")
                onClicked: root.closed()
            }
            Button {
                text: qsTr("OK")
                onClicked: {
                    taskModel.setNote(root.taskId, noteField.text)
                    root.closed()
                }
            }
        }
    }
}

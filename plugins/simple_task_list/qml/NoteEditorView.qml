import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    property string taskId: ""
    signal closed()

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

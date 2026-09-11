import QtQuick
import QtQuick.Window

Window {
    id: ghost
    flags: Qt.FramelessWindowHint | Qt.Tool | Qt.WindowStaysOnTopHint
           | Qt.WindowDoesNotAcceptFocus | Qt.WindowTransparentForInput
    color: "transparent"
    visible: false

    property string taskText: ""
    property string status: "active"

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

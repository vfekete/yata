import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root
    flags: Qt.Dialog | Qt.FramelessWindowHint
    modality: Qt.WindowModal
    color: "transparent"
    visible: false

    property string title: ""
    property real contentWidth: Math.max(300, Math.round(Theme.taskFontPixelSize * 26))
    property string okText: qsTr("OK")
    property string cancelText: qsTr("Cancel")
    property bool showCancel: true
    default property alias content: contentColumn.data

    signal accepted()
    signal rejected()

    function open() {
        root.visible = true
        root.requestActivate()
    }
    function close() {
        root.visible = false
    }
    function accept() {
        root.close()
        root.accepted()
    }
    function reject() {
        root.close()
        root.rejected()
    }

    width: contentWidth
    height: outerColumn.implicitHeight

    x: transientParent ? Math.round(transientParent.x + (transientParent.width - width) / 2) : 0
    y: transientParent ? Math.round(transientParent.y + (transientParent.height - height) / 2) : 0

    onVisibleChanged: if (visible) focusScope.forceActiveFocus()

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: Theme.tintName === "none"
               ? (Theme.dark ? "#111827" : "#f9fafb")
               : Theme.contentBackground
        border.color: Theme.borderColor
        border.width: 1
    }

    FocusScope {
        id: focusScope
        anchors.fill: parent
        focus: true

        Keys.onEscapePressed: root.reject()
        Keys.onReturnPressed: root.accept()

        ColumnLayout {
            id: outerColumn
            width: parent.width
            spacing: 10

            Label {
                visible: root.title.length > 0
                text: root.title
                color: Theme.textColor
                font.bold: true
                font.pixelSize: Theme.taskFontPixelSize * 1.2
                Layout.fillWidth: true
                Layout.margins: 12
                Layout.bottomMargin: 0
            }

            ColumnLayout {
                id: contentColumn
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                spacing: 10
            }

            RowLayout {
                Layout.alignment: Qt.AlignRight
                Layout.margins: 12
                Layout.topMargin: 4
                spacing: 8

                Button {
                    text: root.cancelText
                    visible: root.showCancel
                    onClicked: root.reject()
                }
                Button {
                    text: root.okText
                    onClicked: root.accept()
                }
            }
        }
    }
}

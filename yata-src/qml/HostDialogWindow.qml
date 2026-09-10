import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

// Host-owned twin of plugins/simple_task_list/qml/DialogWindow.qml — same
// "real top-level Window, not an in-window Popup" reasoning (see that
// file's own comment for why), but styled off Main.qml's fixed chrome
// palette instead of the plugin's Theme, since this is used exclusively by
// host-owned dialogs (DeleteWindowDialog/PurgeWindowDialog) that must look
// the same regardless of which plugin happens to be running in the window
// that opened them. Not shared with the plugin's own DialogWindow.qml on
// purpose — that one stays Theme-coupled for NoteDialog.qml, which IS
// plugin content; duplicating this small chrome is the same deliberate
// tradeoff Main.qml itself already makes (its own chromeTextColor etc.
// duplicate, rather than reuse, Theme's equivalents).
Window {
    id: root
    flags: Qt.Dialog | Qt.FramelessWindowHint
    modality: Qt.WindowModal
    color: "transparent"
    visible: false

    required property color chromeTextColor
    required property color chromeMutedTextColor
    required property color chromeAccentColor
    required property string chromeFontFamily
    required property int chromeFontPixelSize
    required property var chromeBoxColor

    property string title: ""
    property real contentWidth: Math.max(300, Math.round(chromeFontPixelSize * 26))
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

    // Centered over whichever YATA window opened it, at open time and
    // whenever that window subsequently moves/resizes — see
    // DialogWindow.qml's own comment for why transientParent is already
    // set with no code on our part.
    x: transientParent ? Math.round(transientParent.x + (transientParent.width - width) / 2) : 0
    y: transientParent ? Math.round(transientParent.y + (transientParent.height - height) / 2) : 0

    onVisibleChanged: if (visible) focusScope.forceActiveFocus()

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.chromeBoxColor(false)
        border.color: root.chromeAccentColor
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
                color: root.chromeTextColor
                font.bold: true
                font.family: root.chromeFontFamily
                font.pixelSize: Math.round(root.chromeFontPixelSize * 1.2)
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

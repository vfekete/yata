import QtQuick
import QtQuick.Controls
import QtQuick.Effects
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

                // Custom background/contentItem, not the plain QtQuick.
                // Controls default look (which is styled for a light
                // "Basic" theme, not this dark chrome panel) — same
                // Rectangle+Text+hover-glow idiom the plugin's own toolbar
                // buttons and Main.qml's own icon boxes already use.
                Button {
                    id: cancelBtn
                    text: root.cancelText
                    visible: root.showCancel
                    onClicked: root.reject()
                    background: Rectangle {
                        radius: 4
                        color: root.chromeBoxColor(cancelBtn.hovered)
                        layer.enabled: cancelBtn.hovered
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowColor: root.chromeAccentColor
                            shadowBlur: 1.0
                            shadowHorizontalOffset: 0
                            shadowVerticalOffset: 0
                            shadowOpacity: 1.0
                            shadowScale: 1.05
                        }
                    }
                    contentItem: Text {
                        text: cancelBtn.text
                        color: root.chromeTextColor
                        font.family: root.chromeFontFamily
                        font.pixelSize: root.chromeFontPixelSize
                        font.capitalization: Font.AllUppercase
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
                Button {
                    id: okBtn
                    text: root.okText
                    onClicked: root.accept()
                    background: Rectangle {
                        radius: 4
                        color: root.chromeBoxColor(okBtn.hovered)
                        layer.enabled: okBtn.hovered
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowColor: root.chromeAccentColor
                            shadowBlur: 1.0
                            shadowHorizontalOffset: 0
                            shadowVerticalOffset: 0
                            shadowOpacity: 1.0
                            shadowScale: 1.05
                        }
                    }
                    contentItem: Text {
                        text: okBtn.text
                        font.bold: true
                        color: root.chromeTextColor
                        font.family: root.chromeFontFamily
                        font.pixelSize: root.chromeFontPixelSize
                        font.capitalization: Font.AllUppercase
                        horizontalAlignment: Text.AlignHCenter
                        verticalAlignment: Text.AlignVCenter
                    }
                }
            }
        }
    }
}

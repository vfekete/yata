import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    implicitHeight: row.implicitHeight + 8

    property bool linksActive: false
    signal linksToggled()

    readonly property string searchText: searchField.text

    readonly property real actionButtonsWidth: addButton.width + reloadButton.width + themeButton.width + linksButton.width + row.spacing * 3

    MouseArea {
        anchors.fill: parent
        onPressed: Window.window.startSystemMove()
    }

    RowLayout {
        id: row
        anchors.fill: parent
        anchors.margins: 4
        spacing: 6

        ToolButton {
            id: addButton
            text: qsTr("Add")
            font.bold: true
            focusPolicy: Qt.NoFocus
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Add task")
            onClicked: taskModel.addTask()
            background: Rectangle {
                radius: 4
                color: parent.hovered ? Theme.hoverColor : "transparent"
            }
            contentItem: Text {
                text: parent.text
                font.bold: parent.font.bold
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                color: Theme.textColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        ToolButton {
            id: reloadButton
            text: qsTr("Reload")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Reload tasks from disk")
            onClicked: taskModel.reloadTasks()
            background: Rectangle {
                radius: 4
                color: reloadButton.hovered ? Theme.hoverColor : "transparent"
            }
            contentItem: Text {
                text: reloadButton.text
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        ToolButton {
            id: themeButton
            text: qsTr("Theme")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Change theme")
            onClicked: themeMenu.popup()
            background: Rectangle {
                radius: 4
                color: themeButton.hovered ? Theme.hoverColor : "transparent"
            }
            contentItem: Text {
                text: themeButton.text
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            ThemeMenu {
                id: themeMenu
            }
        }

        ToolButton {
            id: linksButton
            text: qsTr("Links")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Show all URLs mentioned in tasks")
            onClicked: root.linksToggled()
            background: Rectangle {
                radius: 4
                color: root.linksActive ? Theme.accentColor
                       : (linksButton.hovered ? Theme.hoverColor : "transparent")
                opacity: root.linksActive ? 0.5 : 1.0
            }
            contentItem: Text {
                text: linksButton.text
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: root.linksActive ? qsTr("Search for link") : qsTr("Search for task")
            placeholderTextColor: Theme.mutedTextColor
            leftPadding: searchIcon.width + 12
            rightPadding: clearIcon.width + 14
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            onTextChanged: taskModel.setSearchText(text)
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }

            IconIndicator {
                id: searchIcon
                iconName: "search"
                tint: Theme.mutedTextColor
                anchors.left: parent.left
                anchors.leftMargin: 6
                anchors.verticalCenter: parent.verticalCenter
            }

            Text {
                id: clearIcon
                visible: searchField.text.length > 0
                anchors.right: parent.right
                anchors.rightMargin: 6
                anchors.verticalCenter: parent.verticalCenter
                text: "✕"
                color: Theme.mutedTextColor

                MouseArea {
                    anchors.fill: parent
                    anchors.margins: -4
                    onClicked: searchField.text = ""
                }
            }
        }
    }
}

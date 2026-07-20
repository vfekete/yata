import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    implicitHeight: row.implicitHeight + 8

    // Empty toolbar background doubles as a window drag handle, since the
    // window has no title bar. Buttons/fields declared below sit on top and
    // consume their own clicks first.
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
            text: "Add"
            font.bold: true
            focusPolicy: Qt.NoFocus
            ToolTip.visible: hovered
            ToolTip.text: "Add task"
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
            id: statusButton
            text: "Order"
            ToolTip.visible: hovered
            ToolTip.text: "Sort by order"
            onClicked: statusMenu.popup()
            background: Rectangle {
                radius: 4
                color: taskModel.statusSortMode !== "" ? Theme.accentColor
                       : (statusButton.hovered ? Theme.hoverColor : "transparent")
                opacity: taskModel.statusSortMode !== "" ? 0.5 : 1.0
            }
            contentItem: Text {
                text: statusButton.text
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Menu {
                id: statusMenu
                // Popups are parented into the window's Overlay layer, not
                // the item that opened them, so this needs its own explicit
                // font size rather than inheriting one.
                font.pixelSize: Theme.taskFontPixelSize
                // Explicit reactive width for the same reason as ThemeMenu:
                // longest item is "Cancelled first" → multiplier 13 is safe.
                width: Theme.taskFontPixelSize * 13
                MenuItem {
                    text: "Manual order"
                    checkable: true
                    checked: taskModel.statusSortMode === ""
                    onTriggered: taskModel.setStatusSortMode("")
                    padding: 10
                }
                MenuItem {
                    text: "Active first"
                    checkable: true
                    checked: taskModel.statusSortMode === "active"
                    onTriggered: taskModel.setStatusSortMode("active")
                    padding: 10
                }
                MenuItem {
                    text: "Done first"
                    checkable: true
                    checked: taskModel.statusSortMode === "done"
                    onTriggered: taskModel.setStatusSortMode("done")
                    padding: 10
                }
                MenuItem {
                    text: "Cancelled first"
                    checkable: true
                    checked: taskModel.statusSortMode === "cancelled"
                    onTriggered: taskModel.setStatusSortMode("cancelled")
                    padding: 10
                }
            }
        }

        ToolButton {
            id: reloadButton
            text: "Reload"
            ToolTip.visible: hovered
            ToolTip.text: "Reload tasks from disk"
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
            text: "Theme"
            ToolTip.visible: hovered
            ToolTip.text: "Change theme"
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

        TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search for task"
            rightPadding: clearIcon.width + 14
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            onTextChanged: taskModel.setSearchText(text)
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
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

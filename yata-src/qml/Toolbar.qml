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
            text: "+"
            font.bold: true
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
                color: Theme.textColor
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        ToolButton {
            id: dayButton
            text: "Day"
            checkable: true
            checked: taskModel.groupByDay
            ToolTip.visible: hovered
            ToolTip.text: "Group by day"
            onToggled: taskModel.setGroupByDay(checked)
            background: Rectangle {
                radius: 4
                color: dayButton.checked ? Theme.accentColor : (dayButton.hovered ? Theme.hoverColor : "transparent")
                opacity: dayButton.checked ? 0.5 : 1.0
            }
            contentItem: Text {
                text: dayButton.text
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.capitalization: Font.AllUppercase
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }
        }

        ToolButton {
            id: statusButton
            text: "Status"
            ToolTip.visible: hovered
            ToolTip.text: "Sort by status"
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
                font.capitalization: Font.AllUppercase
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Menu {
                id: statusMenu
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

        TextField {
            id: searchField
            Layout.fillWidth: true
            placeholderText: "Search for task"
            rightPadding: clearIcon.width + 14
            color: Theme.textColor
            font.family: Theme.fontFamily
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

        // Shares the remaining space equally with the search field above,
        // so the field renders at half the width it would otherwise take,
        // and pushes the theme button to the toolbar's right edge.
        Item {
            Layout.fillWidth: true
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
                font.capitalization: Font.AllUppercase
                horizontalAlignment: Text.AlignHCenter
                verticalAlignment: Text.AlignVCenter
            }

            Menu {
                id: themeMenu
                MenuItem {
                    text: "Dark theme"
                    checkable: true
                    checked: appSettings.themeMode === "dark"
                    onTriggered: appSettings.themeMode = "dark"
                    padding: 10
                }
                MenuItem {
                    text: "Light theme"
                    checkable: true
                    checked: appSettings.themeMode === "light"
                    onTriggered: appSettings.themeMode = "light"
                    padding: 10
                }
                MenuSeparator {}
                Menu {
                    title: "Tint"
                    MenuItem { text: "None (plain)"; onTriggered: appSettings.themeTint = "none"; padding: 10 }
                    MenuItem { text: "Green"; onTriggered: appSettings.themeTint = "green"; padding: 10 }
                    MenuItem { text: "Goldenrod"; onTriggered: appSettings.themeTint = "goldenrod"; padding: 10 }
                    MenuItem { text: "White"; onTriggered: appSettings.themeTint = "white"; padding: 10 }
                    MenuItem { text: "Black"; onTriggered: appSettings.themeTint = "black"; padding: 10 }
                }
            }
        }
    }
}

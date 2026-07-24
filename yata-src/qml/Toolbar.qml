import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    implicitHeight: row.implicitHeight + 8

    // Set externally by Main.qml (from FilterBar.linksActive) — Toolbar
    // can't see FilterBar directly (separate QML documents, ids don't cross
    // file boundaries), so Main.qml relays state both ways: this property
    // drives the button's highlighted look, and linksToggled() below is how
    // a click gets back out to Main.qml to actually flip it.
    property bool linksActive: false
    signal linksToggled()

    // Relayed to LinksView by Main.qml while Links is active — see
    // searchField below for why the same field drives both contexts.
    readonly property string searchText: searchField.text

    // Sum of ADD/RELOAD/THEME/LINKS's own widths plus the spacing between
    // them — i.e. "the width of the upper toolbar buttons one after
    // another", scaling with font zoom same as the buttons themselves. Used
    // by Main.qml to set the window's minimumWidth.
    readonly property real actionButtonsWidth: addButton.width + reloadButton.width + themeButton.width + linksButton.width + row.spacing * 3

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
            id: addButton
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

        ToolButton {
            id: linksButton
            text: "Links"
            ToolTip.visible: hovered
            ToolTip.text: "Show all URLs mentioned in tasks"
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
            // One shared field for both contexts — its text always feeds
            // taskModel's search (harmless while Links is active, since
            // LinksView doesn't use taskModel._visible) and is separately
            // relayed to LinksView for link-label/url filtering there; the
            // placeholder is what actually tells the user which context
            // they're currently searching.
            placeholderText: root.linksActive ? "Search for link" : "Search for task"
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

            // Static "lupe" (magnifying glass) marking this field as search —
            // non-interactive, unlike clearIcon on the right. Explicitly
            // matched to placeholderTextColor above (the visible "Search for
            // task" text's actual color) rather than Theme.textColor, which
            // is only what typed-in text uses and rendered visibly brighter.
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

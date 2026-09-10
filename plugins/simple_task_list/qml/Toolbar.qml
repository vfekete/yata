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

    // Same relay pattern as linksActive/linksToggled above, for the YATAS
    // window-list view (r-3.md).
    property bool yatasActive: false
    signal yatasToggled()

    // ADD's meaning is context-sensitive: a new task normally, but a new
    // YATA window while the YATAS view is showing (explicit requirement —
    // "when ADD is clicked, instead of new task, new window is created").
    signal addWindowRequested()

    // Relayed to LinksView/YatasView by Main.qml while each is active — see
    // searchField below for why the same field drives all three contexts.
    readonly property string searchText: searchField.text

    // Sum of ADD/RELOAD/THEME/LINKS/YATAS's own widths plus the spacing
    // between them — i.e. "the width of the upper toolbar buttons one after
    // another", scaling with font zoom same as the buttons themselves. Used
    // by Main.qml to set the window's minimumWidth.
    readonly property real actionButtonsWidth: addButton.width + reloadButton.width + themeButton.width + linksButton.width + yatasButton.width + row.spacing * 4

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
            text: qsTr("Add")
            font.bold: true
            focusPolicy: Qt.NoFocus
            ToolTip.visible: hovered
            ToolTip.text: root.yatasActive ? qsTr("Add window") : qsTr("Add task")
            onClicked: root.yatasActive ? root.addWindowRequested() : taskModel.addTask()
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

        ToolButton {
            id: yatasButton
            text: qsTr("Yatas")
            ToolTip.visible: hovered
            ToolTip.text: qsTr("Manage YATA windows")
            onClicked: root.yatasToggled()
            background: Rectangle {
                radius: 4
                color: root.yatasActive ? Theme.accentColor
                       : (yatasButton.hovered ? Theme.hoverColor : "transparent")
                opacity: root.yatasActive ? 0.5 : 1.0
            }
            contentItem: Text {
                text: yatasButton.text
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
            // One shared field for all three contexts — its text always
            // feeds taskModel's search (harmless while Links/Yatas is
            // active, since neither view uses taskModel._visible) and is
            // separately relayed to LinksView/YatasView for their own
            // filtering there; the placeholder is what actually tells the
            // user which context they're currently searching.
            placeholderText: root.yatasActive ? qsTr("Search for window")
                             : (root.linksActive ? qsTr("Search for link") : qsTr("Search for task"))
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

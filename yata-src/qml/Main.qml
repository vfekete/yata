import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root
    visible: true
    color: "transparent"
    opacity: Theme.windowOpacity
    // Qt.WindowStaysOnBottomHint is intentionally not used: on GNOME/Mutter
    // (the primary target platform) it places the window below the desktop
    // background layer itself, making it invisible rather than merely
    // "beneath other windows, above icons". See README.md.
    flags: Qt.FramelessWindowHint

    x: appSettings.x
    y: appSettings.y
    width: appSettings.width
    height: appSettings.height

    onXChanged: appSettings.x = x
    onYChanged: appSettings.y = y
    onWidthChanged: appSettings.width = width
    onHeightChanged: appSettings.height = height

    // Right-click anywhere on the background for theme + quit. Placed first so
    // real controls (declared later / painted on top) get first refusal at clicks.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: contextMenu.popup()
    }

    Menu {
        id: contextMenu
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
        MenuSeparator {}
        MenuItem { text: "Quit"; onTriggered: Qt.quit(); padding: 10 }
    }

    // The window itself stays fully transparent (per spec); this wash is
    // what actually paints each tint's background, translucent so the
    // window still reads as "transparent" rather than opaque.
    Rectangle {
        anchors.fill: parent
        radius: 6
        color: Theme.contentBackground
    }

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 6
        spacing: 4

        Toolbar {
            id: toolbar
            Layout.fillWidth: true
        }

        ListView {
            id: listView
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 2
            model: taskModel
            ScrollBar.vertical: ScrollBar { id: vbar; policy: ScrollBar.AsNeeded }

            section.property: taskModel.groupByDay ? "dayLabel" : ""
            section.criteria: ViewSection.FullString
            section.delegate: sectionHeader

            // Drag-to-reorder state, read by TaskDelegate instances.
            property bool dragActive: false
            property int dragFromIndex: -1
            property int dragHoverIndex: -1

            // The scrollbar is an overlay (doesn't reserve its own width),
            // so rows must leave room for it themselves or their hover
            // icons render underneath its thumb.
            property real rowWidth: width - (vbar.visible ? vbar.width : 0)

            delegate: TaskDelegate {
                width: listView.rowWidth
            }
        }
    }

    Component {
        id: sectionHeader
        Rectangle {
            width: listView.rowWidth
            height: headerText.implicitHeight + 10
            color: "transparent"
            Text {
                id: headerText
                anchors.left: parent.left
                anchors.verticalCenter: parent.verticalCenter
                text: section
                color: Theme.mutedTextColor
                font.bold: true
                // Day name reads as a heading over the task list below it.
                font.pixelSize: Theme.taskFontPixelSize * 1.5
                font.family: Theme.fontFamily
            }
        }
    }

    Rectangle {
        anchors.fill: parent
        color: "transparent"
        radius: 6
        border.color: Theme.borderColor
        border.width: 1
    }
}

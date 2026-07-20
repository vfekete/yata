import QtQuick
import QtQuick.Controls

// Shared theme popup, used both by Main.qml's background right-click menu
// and Toolbar.qml's "Theme" button, so the opacity editor's state (view vs.
// edit mode) only needs to live in one place.
Menu {
    id: root
    property bool showQuit: false

    // Popups are parented into the window's Overlay layer, not into the
    // visual item that opened them, so they don't inherit font size from
    // the toolbar/window's item tree and need it set explicitly.
    font.pixelSize: Theme.taskFontPixelSize
    // Explicitly scale width with font so the menu stays wide enough for
    // the longest item ("Switch zoom direction") at every zoom level.
    // Qt Quick Controls 2 doesn't reactively re-derive contentWidth from
    // MenuItem implicitWidths when font.pixelSize changes.
    width: Theme.taskFontPixelSize * 16

    // Opacity slider first, per feature request. A plain Item, not a
    // MenuItem, because Menu accepts arbitrary Items alongside MenuItems.
    Item {
        id: opacityRow
        width: root.width > 0 ? root.width - 20 : 200
        implicitWidth: 200
        height: opacityLabel.implicitHeight + opacitySlider.implicitHeight + 8
        anchors.horizontalCenter: parent ? parent.horizontalCenter : undefined

        Text {
            id: opacityLabel
            y: 4
            width: parent.width
            text: "Opacity: " + appSettings.opacityPercent + "%"
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            horizontalAlignment: Text.AlignHCenter
        }

        Slider {
            id: opacitySlider
            y: opacityLabel.y + opacityLabel.implicitHeight + 4
            width: parent.width
            from: 5
            to: 100
            stepSize: 1
            value: appSettings.opacityPercent
            onMoved: appSettings.opacityPercent = Math.round(value)
        }
    }

    MenuItem {
        text: "Reset"
        font.capitalization: Font.AllUppercase
        onTriggered: {
            appSettings.opacityPercent = appSettings.defaultOpacityPercent
            appSettings.fontScale = appSettings.defaultFontScale
        }
        padding: 10
    }
    MenuItem {
        text: "Switch zoom direction"
        checkable: true
        checked: appSettings.wheelZoomInverted
        onTriggered: appSettings.wheelZoomInverted = checked
        padding: 10
    }

    MenuSeparator {}

    MenuItem {
        text: "Dark theme"
        checkable: true
        // "Dark"/"Light" are also the way back to the plain look: picking
        // either forces the tint to "none" (the Tint submenu no longer has
        // its own "None" entry).
        checked: appSettings.themeMode === "dark" && appSettings.themeTint === "none"
        onTriggered: {
            appSettings.themeMode = "dark"
            appSettings.themeTint = "none"
        }
        padding: 10
    }
    MenuItem {
        text: "Light theme"
        checkable: true
        checked: appSettings.themeMode === "light" && appSettings.themeTint === "none"
        onTriggered: {
            appSettings.themeMode = "light"
            appSettings.themeTint = "none"
        }
        padding: 10
    }

    MenuSeparator {}

    Menu {
        title: "Tint"
        font.pixelSize: Theme.taskFontPixelSize
        // CRT tints ignore theme mode entirely; "None" was removed here
        // since Dark/Light theme above now cover that look directly.
        MenuItem { text: "Green"; onTriggered: appSettings.themeTint = "green"; padding: 10 }
        MenuItem { text: "Goldenrod"; onTriggered: appSettings.themeTint = "goldenrod"; padding: 10 }
        MenuItem { text: "White"; onTriggered: appSettings.themeTint = "white"; padding: 10 }
        MenuItem { text: "Black"; onTriggered: appSettings.themeTint = "black"; padding: 10 }
    }

    MenuSeparator {
        visible: root.showQuit
        height: root.showQuit ? implicitHeight : 0
    }
    MenuItem {
        visible: root.showQuit
        height: root.showQuit ? implicitHeight : 0
        text: "Quit"
        onTriggered: Qt.quit()
        padding: 10
    }
}

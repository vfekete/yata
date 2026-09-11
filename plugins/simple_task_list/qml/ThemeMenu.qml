import QtQuick
import QtQuick.Controls

Menu {
    id: root
    property bool showQuit: false

    font.pixelSize: Theme.taskFontPixelSize
    width: Theme.taskFontPixelSize * 16

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
            text: qsTr("Opacity: %1%").arg(appSettings.opacityPercent)
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
        text: qsTr("Reset")
        font.capitalization: Font.AllUppercase
        onTriggered: {
            appSettings.opacityPercent = appSettings.defaultOpacityPercent
            hostSettings.zoomLevel = hostSettings.defaultZoomLevel
            hostSettings.borderColor = ""
        }
        padding: 10
    }
    MenuItem {
        text: qsTr("Switch zoom direction")
        checkable: true
        checked: hostSettings.wheelZoomInverted
        onTriggered: hostSettings.wheelZoomInverted = checked
        padding: 10
    }

    MenuSeparator {}

    MenuItem {
        text: qsTr("Dark theme")
        checkable: true
        checked: appSettings.themeMode === "dark" && appSettings.themeTint === "none"
        onTriggered: {
            appSettings.themeMode = "dark"
            appSettings.themeTint = "none"
        }
        padding: 10
    }
    MenuItem {
        text: qsTr("Light theme")
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
        title: qsTr("Tint")
        font.pixelSize: Theme.taskFontPixelSize
        MenuItem { text: qsTr("Green"); onTriggered: appSettings.themeTint = "green"; padding: 10 }
        MenuItem { text: qsTr("Goldenrod"); onTriggered: appSettings.themeTint = "goldenrod"; padding: 10 }
        MenuItem { text: qsTr("White"); onTriggered: appSettings.themeTint = "white"; padding: 10 }
        MenuItem { text: qsTr("Black"); onTriggered: appSettings.themeTint = "black"; padding: 10 }
    }

    MenuSeparator {
        visible: root.showQuit
        height: root.showQuit ? implicitHeight : 0
    }
    MenuItem {
        visible: root.showQuit
        height: root.showQuit ? implicitHeight : 0
        text: qsTr("Quit")
        onTriggered: Qt.quit()
        padding: 10
    }
}

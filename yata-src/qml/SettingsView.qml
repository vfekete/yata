import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    readonly property int rowInset: 8

    ColumnLayout {
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.margins: 16
        spacing: 14

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            Text {
                Layout.leftMargin: root.rowInset
                text: qsTr("Opacity: %1%").arg(appSettings.opacityPercent)
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
            Slider {
                Layout.fillWidth: true
                from: 5
                to: 100
                stepSize: 1
                value: appSettings.opacityPercent
                onMoved: appSettings.opacityPercent = Math.round(value)
            }
        }

        Rectangle {
            id: resetRow
            Layout.fillWidth: true
            radius: 4
            implicitHeight: resetText.implicitHeight + 16
            color: resetHover.hovered ? Theme.hoverColor : "transparent"

            Text {
                id: resetText
                anchors.left: parent.left
                anchors.leftMargin: root.rowInset
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Reset")
                font.capitalization: Font.AllUppercase
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
            HoverHandler { id: resetHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: {
                    appSettings.opacityPercent = appSettings.defaultOpacityPercent
                    hostSettings.zoomLevel = hostSettings.defaultZoomLevel
                    hostSettings.borderColor = ""
                }
            }
        }

        Rectangle {
            id: zoomDirRow
            Layout.fillWidth: true
            radius: 4
            implicitHeight: zoomDirText.implicitHeight + 16
            color: hostSettings.wheelZoomInverted ? Theme.accentColor
                   : (zoomDirHover.hovered ? Theme.hoverColor : "transparent")
            opacity: hostSettings.wheelZoomInverted ? 0.5 : 1.0

            Text {
                id: zoomDirText
                anchors.left: parent.left
                anchors.leftMargin: root.rowInset
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Switch zoom direction")
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
            HoverHandler { id: zoomDirHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: hostSettings.wheelZoomInverted = !hostSettings.wheelZoomInverted
            }
        }

        Rectangle {
            id: darkRow
            Layout.fillWidth: true
            radius: 4
            implicitHeight: darkText.implicitHeight + 16
            readonly property bool checked: appSettings.themeMode === "dark" && appSettings.themeTint === "none"
            color: darkRow.checked ? Theme.accentColor : (darkHover.hovered ? Theme.hoverColor : "transparent")
            opacity: darkRow.checked ? 0.5 : 1.0

            Text {
                id: darkText
                anchors.left: parent.left
                anchors.leftMargin: root.rowInset
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Dark theme")
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
            HoverHandler { id: darkHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: { appSettings.themeMode = "dark"; appSettings.themeTint = "none" }
            }
        }

        Rectangle {
            id: lightRow
            Layout.fillWidth: true
            radius: 4
            implicitHeight: lightText.implicitHeight + 16
            readonly property bool checked: appSettings.themeMode === "light" && appSettings.themeTint === "none"
            color: lightRow.checked ? Theme.accentColor : (lightHover.hovered ? Theme.hoverColor : "transparent")
            opacity: lightRow.checked ? 0.5 : 1.0

            Text {
                id: lightText
                anchors.left: parent.left
                anchors.leftMargin: root.rowInset
                anchors.verticalCenter: parent.verticalCenter
                text: qsTr("Light theme")
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
            HoverHandler { id: lightHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: { appSettings.themeMode = "light"; appSettings.themeTint = "none" }
            }
        }

        Text {
            Layout.leftMargin: root.rowInset
            text: qsTr("Tint")
            color: Theme.mutedTextColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
        }

        Flow {
            Layout.fillWidth: true
            Layout.leftMargin: root.rowInset
            spacing: 8

            Repeater {
                model: [
                    { id: "green", label: qsTr("Green") },
                    { id: "goldenrod", label: qsTr("Goldenrod") },
                    { id: "white", label: qsTr("White") },
                    { id: "black", label: qsTr("Black") }
                ]
                delegate: Rectangle {
                    id: tintBtn
                    required property var modelData
                    radius: 4
                    width: tintText.implicitWidth + 20
                    height: tintText.implicitHeight + 12
                    readonly property bool checked: appSettings.themeTint === tintBtn.modelData.id
                    color: tintBtn.checked ? Theme.accentColor : (tintHover.hovered ? Theme.hoverColor : "transparent")
                    opacity: tintBtn.checked ? 0.5 : 1.0

                    Text {
                        id: tintText
                        anchors.centerIn: parent
                        text: tintBtn.modelData.label
                        color: Theme.textColor
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.taskFontPixelSize
                    }
                    HoverHandler { id: tintHover; cursorShape: Qt.PointingHandCursor }
                    TapHandler { onTapped: appSettings.themeTint = tintBtn.modelData.id }
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    required property string windowId
    required property string tag
    required property bool open
    required property bool deleted
    required property int openWindowCount
    required property string borderColor
    signal renamed(string windowId, string newTag)
    signal deleteRequested(string windowId, string tag)
    signal showToggled(string windowId, bool show)
    signal recreateRequested(string windowId)
    signal purgeRequested(string windowId, string tag)
    signal borderColorPicked(string windowId, color newColor)

    required property color chromeTextColor
    required property color chromeMutedTextColor
    required property color chromeAccentColor
    required property string chromeFontFamily
    required property int chromeFontPixelSize
    required property var chromeBoxColor
    required property color chromeFieldColor
    required property color chromeHoverColor
    required property color chromeDangerColor

    property bool editing: false
    readonly property bool hovered: hoverHandler.hovered

    readonly property int iconBoxHeight: Math.round(root.chromeFontPixelSize * 0.86)

    width: ListView.view.width
    height: Math.max(30, mainRow.implicitHeight + 12 + (root.deleted ? deletedLabel.implicitHeight + 2 : 0))

    HoverHandler { id: hoverHandler }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? root.chromeHoverColor : "transparent"
    }

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: 10

        Text {
            id: tagText
            Layout.fillWidth: true
            visible: !root.editing
            text: root.tag
            color: root.borderColor !== "" ? root.borderColor : root.chromeTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: root.chromeFontPixelSize

            TapHandler {
                onDoubleTapped: root.editing = true
            }
        }

        TextField {
            id: editField
            Layout.fillWidth: true
            visible: root.editing
            text: root.tag
            color: root.chromeTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: root.chromeFontPixelSize
            background: Rectangle {
                radius: 4
                color: root.chromeFieldColor
            }

            onVisibleChanged: if (visible) { selectAll(); forceActiveFocus() }

            function commit() {
                root.editing = false
                var trimmed = text.trim()
                if (trimmed.length > 0 && trimmed !== root.tag)
                    root.renamed(root.windowId, trimmed)
            }
            onEditingFinished: commit()
            Keys.onReturnPressed: commit()
            Keys.onEscapePressed: root.editing = false
        }

        Image {
            id: showBtn
            visible: !root.deleted && !root.editing && (!root.open || root.openWindowCount > 1)
            source: iconProvider.coloredSvgUri("visibility",
                (showHover.hovered ? root.chromeAccentColor : (root.open ? root.chromeTextColor : root.chromeMutedTextColor)).toString())
            fillMode: Image.PreserveAspectFit
            smooth: true
            height: root.iconBoxHeight
            width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
            Layout.preferredWidth: width
            Layout.preferredHeight: height
            Layout.alignment: Qt.AlignVCenter
            opacity: root.open ? 1.0 : 0.4
            layer.enabled: showHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: showHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.showToggled(root.windowId, !root.open) }
        }

        Image {
            id: colorBtn
            visible: !root.deleted && !root.editing
            source: iconProvider.coloredSvgUri("paintbucket",
                (colorHover.hovered ? root.chromeAccentColor : root.chromeTextColor).toString())
            fillMode: Image.PreserveAspectFit
            smooth: true
            height: root.iconBoxHeight
            width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
            Layout.preferredWidth: width
            Layout.preferredHeight: height
            Layout.alignment: Qt.AlignVCenter
            layer.enabled: colorHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: colorHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: {
                    var current = windowManager.getBorderColor(root.windowId)
                    colorDialog.selectedColor = current !== "" ? current : "white"
                    colorDialog.open()
                }
            }

            ColorDialog {
                id: colorDialog
                title: qsTr("Choose border color")
                onAccepted: root.borderColorPicked(root.windowId, selectedColor)
            }
        }

        Text {
            id: deleteBtn
            visible: !root.deleted && !root.editing
            text: "🗑"
            color: deleteHover.hovered ? root.chromeAccentColor : root.chromeMutedTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 1.3)
            layer.enabled: deleteHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: deleteHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.deleteRequested(root.windowId, root.tag) }
        }

        Text {
            id: recreateBtn
            visible: root.deleted && !root.editing
            text: "↺"
            color: recreateHover.hovered ? root.chromeAccentColor : root.chromeTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 1.3)
            layer.enabled: recreateHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: recreateHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.recreateRequested(root.windowId) }
        }

        Text {
            id: purgeBtn
            visible: root.deleted && !root.editing
            text: "🗑"
            color: purgeHover.hovered ? root.chromeAccentColor : root.chromeMutedTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 1.3)
            layer.enabled: purgeHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: purgeHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.purgeRequested(root.windowId, root.tag) }
        }
    }

    Text {
        id: deletedLabel
        visible: root.deleted
        anchors.left: mainRow.left
        anchors.top: mainRow.bottom
        anchors.topMargin: 2
        text: qsTr("DELETED")
        color: root.chromeDangerColor
        font.family: root.chromeFontFamily
        font.pixelSize: Math.round(root.chromeFontPixelSize * 0.75)
        font.bold: true
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: deletedLabel.color
            shadowBlur: 1.0
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0
            shadowOpacity: 1.0
        }
    }
}

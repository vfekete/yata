import QtQuick
import QtQuick.Effects
import QtQuick.Layouts

Item {
    id: root
    property string iconName: ""
    property bool active: false
    property real sizeScale: 1.0
    signal tapped()

    readonly property int hitPadding: 4
    readonly property int boxHeight: Math.round(Theme.taskFontPixelSize * 1.15 * sizeScale)
    readonly property int boxWidth: img.implicitHeight > 0
        ? Math.round(boxHeight * img.implicitWidth / img.implicitHeight)
        : boxHeight

    Layout.alignment: Qt.AlignVCenter
    implicitWidth: root.boxWidth + root.hitPadding * 2
    implicitHeight: root.boxHeight + root.hitPadding * 2
    Layout.preferredWidth: root.implicitWidth
    Layout.preferredHeight: root.implicitHeight

    readonly property color iconColor: hoverHandler.hovered ? Theme.filterHoverColor
        : (root.active ? Theme.effectiveGlowColor : Theme.mutedTextColor)

    Image {
        id: img
        anchors.centerIn: parent
        width: root.boxWidth
        height: root.boxHeight
        fillMode: Image.PreserveAspectFit
        smooth: true
        source: root.iconName ? iconProvider.coloredSvgUri(root.iconName, root.iconColor.toString()) : ""

        layer.enabled: hoverHandler.hovered || root.active
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: hoverHandler.hovered ? Theme.filterHoverColor : Theme.effectiveGlowShadowColor
            shadowBlur: 1.0
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0
            shadowOpacity: 1.0
            shadowScale: 1.05
        }
    }

    HoverHandler { id: hoverHandler; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.tapped() }
}

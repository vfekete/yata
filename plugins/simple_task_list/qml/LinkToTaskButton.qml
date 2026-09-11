import QtQuick
import QtQuick.Effects
import QtQuick.Layouts

Item {
    id: root
    signal clicked()

    readonly property color iconTint: hh.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
    readonly property real iconBoxHeight: Theme.taskFontPixelSize * 1
    readonly property real iconBoxWidth: icon.implicitHeight > 0
        ? Math.round(iconBoxHeight * icon.implicitWidth / icon.implicitHeight)
        : iconBoxHeight

    Layout.alignment: Qt.AlignVCenter
    implicitWidth: iconBoxWidth
    implicitHeight: iconBoxHeight

    HoverHandler { id: hh; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.clicked() }

    Image {
        id: icon
        width: root.iconBoxWidth
        height: root.iconBoxHeight
        fillMode: Image.PreserveAspectFit
        smooth: true
        source: iconProvider.coloredSvgUri("link", root.iconTint.toString())

        layer.enabled: hh.hovered
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: Theme.effectiveGlowShadowColor
            shadowBlur: 1.0
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0
            shadowOpacity: 1.0
            shadowScale: 1.05
        }
    }
}

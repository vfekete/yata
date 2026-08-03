import QtQuick
import QtQuick.Effects
import QtQuick.Layouts

// "To task" button at the end of each LinksView row: navigates back to the
// task list, scrolled to that task. Glow-on-hover / cyan-on-hover convention
// matches TaskDelegate's hover action icons (done/cancel/reopen/delete), but
// sized at half their size (taskFontPixelSize*1, not *2) per explicit
// follow-up request ("make the icon 50% smaller"). Built directly on the
// coloredSvgUri recoloring technique (see IconIndicator.qml for why:
// MultiEffect colorization doesn't reliably recolor these icons live, so
// recoloring is done via a data: URI swap instead) rather than reusing
// IconIndicator itself, since IconIndicator is static/non-interactive and
// this needs hover + tap + a hover-driven color/glow change.
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

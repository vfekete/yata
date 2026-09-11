import QtQuick
import QtQuick.Effects

Item {
    id: btn
    property string label: ""
    property bool active: false
    signal tapped()

    implicitWidth: lbl.implicitWidth + 8
    implicitHeight: lbl.implicitHeight + 2

    HoverHandler { id: bh; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: btn.tapped() }

    Text {
        id: lbl
        anchors.centerIn: parent
        text: btn.label
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
        font.capitalization: Font.AllUppercase
        color: bh.hovered ? Theme.effectiveGlowColor : (btn.active ? Theme.effectiveGlowColor : Theme.mutedTextColor)
        layer.enabled: bh.hovered || btn.active
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

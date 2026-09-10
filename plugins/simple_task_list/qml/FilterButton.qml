import QtQuick
import QtQuick.Effects

// Small toggle-pill button shared by FilterBar (multi-select toggles) and
// OrderBar (radio-style select). ON state looks identical to hover (cyan
// glow + #00FFFF text) so toggled state is unmistakable regardless of theme
// palette. Callers decide what `toggled`'s argument means (flip vs. select).
Item {
    id: btn
    property string label: ""
    property bool active: true
    signal toggled(bool newChecked)

    implicitWidth: lbl.implicitWidth + 8
    implicitHeight: lbl.implicitHeight + 2

    HoverHandler { id: bh; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: btn.toggled(!btn.active) }

    Text {
        id: lbl
        anchors.centerIn: parent
        text: btn.label
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
        font.capitalization: Font.AllUppercase
        // Pushed (active) state matches the window's own custom border
        // color (r-4.md/r-5.md) when one is set — Theme.effectiveGlowColor
        // already carries that fallback. Hover keeps its own existing
        // Theme.filterHoverColor regardless — that's a transient
        // interaction state, not this window's persistent identity color.
        color: bh.hovered ? Theme.filterHoverColor : (btn.active ? Theme.effectiveGlowColor : Theme.mutedTextColor)
        layer.enabled: bh.hovered || btn.active
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: bh.hovered ? Theme.filterHoverColor : Theme.effectiveGlowShadowColor
            shadowBlur: 1.0
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0
            shadowOpacity: 1.0
            shadowScale: 1.05
        }
    }
}

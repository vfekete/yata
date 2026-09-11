import QtQuick
import QtQuick.Effects

Item {
    id: root
    required property string taskId
    required property string targetStatus
    required property string glyph
    required property color idleColor
    required property string note

    readonly property int holdDurationMs: 700
    readonly property int clickThresholdMs: 200
    property real pressStartMs: 0
    property bool isHeld: false

    implicitWidth: glyphText.implicitWidth
    implicitHeight: glyphText.implicitHeight

    HoverHandler { id: hh; cursorShape: Qt.PointingHandCursor }
    Loader {
        id: tapLoader
        anchors.fill: parent
        active: true
        sourceComponent: TapHandler {
            id: th
            target: root
            acceptedButtons: Qt.LeftButton
            longPressThreshold: root.holdDurationMs / 1000
            onPressedChanged: {
                if (pressed) {
                    root.pressStartMs = Date.now()
                    root.isHeld = true
                } else {
                    root.isHeld = false
                }
            }
            onTapped: {
                if (Date.now() - root.pressStartMs < root.clickThresholdMs)
                    taskModel.setStatus(root.taskId, root.targetStatus)
            }
            onLongPressed: {
                root.isHeld = false
                noteDialog.openFor(root.taskId, root.targetStatus, root.note)
            }
        }
    }

    Text {
        id: glyphText
        anchors.centerIn: parent
        visible: !root.isHeld
        text: root.glyph
        color: hh.hovered ? Theme.effectiveGlowColor : root.idleColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize * 2
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

    Image {
        id: noteGlyph
        anchors.centerIn: parent
        visible: root.isHeld
        readonly property int boxSize: Math.round(Math.min(parent.width, parent.height) * 0.7)
        width: boxSize * 0.80
        height: boxSize * 0.80
        fillMode: Image.PreserveAspectFit
        smooth: true
        source: root.isHeld ? iconProvider.coloredSvgUri("notes", Theme.effectiveGlowColor.toString()) : ""
        layer.enabled: root.isHeld
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

    Canvas {
        id: ring
        anchors.fill: parent
        visible: root.isHeld
        property real progress: tapLoader.item ? Math.max(0, Math.min(1, tapLoader.item.timeHeld / (root.holdDurationMs / 1000))) : 0
        onProgressChanged: requestPaint()
        onVisibleChanged: if (visible) requestPaint()
        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.lineWidth = 3
            ctx.strokeStyle = Theme.effectiveGlowColor
            ctx.beginPath()
            ctx.arc(width / 2, height / 2, Math.min(width, height) / 2 - 2,
                     -Math.PI / 2, -Math.PI / 2 + 2 * Math.PI * progress)
            ctx.stroke()
        }
    }

    NoteDialog {
        id: noteDialog
        onVisibleChanged: if (!visible) {
            tapLoader.active = false
            tapLoader.active = true
        }
    }
}

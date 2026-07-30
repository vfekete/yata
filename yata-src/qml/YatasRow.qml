import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

// One row in YatasView: a window's tag (double-click to rename, matching
// TaskDelegate's double-click-to-edit convention) and a trash icon that's
// always visible (not hover-gated — r-3.md: "every item in submenu has
// small trash bin on the right", unlike TaskDelegate's hover-only action
// icons).
Item {
    id: root
    required property string windowId
    required property string tag
    required property bool open
    required property int openWindowCount
    signal renamed(string windowId, string newTag)
    signal deleteRequested(string windowId, string tag)
    signal showToggled(string windowId, bool show)

    property bool editing: false
    readonly property bool hovered: hoverHandler.hovered

    width: ListView.view.width
    height: Math.max(30, mainRow.implicitHeight + 12)

    HoverHandler { id: hoverHandler }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? Theme.hoverColor : "transparent"
    }

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: 10

        Text {
            id: tagText
            Layout.fillWidth: true
            visible: !root.editing
            text: root.tag
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize

            TapHandler {
                onDoubleTapped: root.editing = true
            }
        }

        TextField {
            id: editField
            Layout.fillWidth: true
            visible: root.editing
            text: root.tag
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
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

        IconIndicator {
            id: showBtn
            // Hidden (not just disabled) when this is the only window open
            // right now — closing it would leave nothing on screen and no
            // YatasView left to reopen anything from. A closed window's row
            // always keeps its button (reopening is always safe).
            visible: !root.editing && (!root.open || root.openWindowCount > 1)
            iconName: "visibility"
            // 65% of the original 1.15 size, per explicit user request after
            // it rendered far larger than deleteBtn and not vertically
            // centered with it — height follows width via IconIndicator's
            // own aspect-ratio sizing.
            sizeScale: 1.15 * 0.65
            Layout.alignment: Qt.AlignVCenter
            // Even with matching AlignVCenter, the eye's tightly-cropped SVG
            // box and deleteBtn's emoji glyph (which renders with descender
            // padding baked into its own line-height box, pushing the
            // visible glyph higher than its box's true center) don't share
            // the same optical center — this nudges the eye to match
            // deleteBtn's visible glyph position rather than its box.
            // Started as +0.2*taskFontPixelSize (too far down per live
            // screenshot); pulled back up 15px per direct user feedback.
            Layout.topMargin: Math.round(Theme.taskFontPixelSize * 0.2) - 15
            tint: showHover.hovered ? "#00FFFF" : (root.open ? Theme.textColor : Theme.mutedTextColor)
            opacity: root.open ? 1.0 : 0.4
            layer.enabled: showHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: "#00FFFF"
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: showHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.showToggled(root.windowId, !root.open) }
        }

        Text {
            id: deleteBtn
            visible: !root.editing
            text: "🗑"
            color: deleteHover.hovered ? "#00FFFF" : Theme.mutedTextColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize * 1.3
            layer.enabled: deleteHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: "#00FFFF"
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: deleteHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.deleteRequested(root.windowId, root.tag) }
        }
    }
}

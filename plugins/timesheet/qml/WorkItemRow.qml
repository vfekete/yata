import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

// One row in the work-item list — name (double-click to rename, matching
// YatasRow.qml/TaskDelegate.qml's own double-click-to-edit convention),
// hover-revealed start/stop + sessions + non-working + delete buttons,
// total duration shown beneath the name.
Item {
    id: root
    required property string itemId
    required property string name
    required property bool nonWorking
    required property bool running
    required property string durationLabel
    required property bool hasAbandonedSession

    signal renamed(string itemId, string newName)
    signal startRequested(string itemId)
    signal stopRequested(string itemId)
    signal deleteRequested(string itemId, string name)
    signal nonWorkingToggled(string itemId, bool nonWorking)
    signal sessionsRequested(string itemId)

    property bool editing: root.name.length === 0
    readonly property bool hovered: hoverHandler.hovered

    width: ListView.view.width
    height: Math.max(40, mainRow.implicitHeight + 14)

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
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        spacing: 10

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            visible: !root.editing

            Text {
                text: root.name
                color: root.nonWorking ? Theme.mutedTextColor : Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.italic: root.nonWorking

                TapHandler {
                    onDoubleTapped: root.editing = true
                }
            }

            Text {
                text: root.durationLabel + (root.nonWorking ? qsTr(" (non-working)") : "")
                color: Theme.mutedTextColor
                font.family: Theme.fontFamily
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
            }
        }

        TextField {
            id: nameField
            Layout.fillWidth: true
            visible: root.editing
            text: root.name
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
                if (trimmed.length > 0)
                    root.renamed(root.itemId, trimmed)
                else if (root.name.length === 0)
                    root.deleteRequested(root.itemId, "")  // abandoned ADD, never named -- see model.py's addItem pruning
            }
            onEditingFinished: commit()
            Keys.onReturnPressed: commit()
            Keys.onEscapePressed: { root.editing = false; text = root.name }
        }

        // Warns when at least one of this item's sessions was auto-closed
        // by the abandoned-session sweep (storage.py) — tap to jump
        // straight to SessionsDialog to review/fix it.
        Text {
            visible: root.hasAbandonedSession && !root.editing
            text: "⚠"
            color: Theme.abandonedColor
            font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.1)
            ToolTip.visible: abandonedHover.hovered
            ToolTip.text: qsTr("Has an abandoned session -- click to review")
            HoverHandler { id: abandonedHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.sessionsRequested(root.itemId) }
        }

        Text {
            visible: !root.editing
            text: root.nonWorking ? "☑" : "☐"
            color: nonWorkingHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
            font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
            ToolTip.visible: nonWorkingHover.hovered
            ToolTip.text: qsTr("Non-working (excluded from totals)")
            HoverHandler { id: nonWorkingHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.nonWorkingToggled(root.itemId, !root.nonWorking) }
        }

        Text {
            visible: !root.editing
            text: "🕘"
            color: sessionsHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
            font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
            ToolTip.visible: sessionsHover.hovered
            ToolTip.text: qsTr("Edit sessions")
            HoverHandler { id: sessionsHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.sessionsRequested(root.itemId) }
        }

        Text {
            visible: !root.editing
            text: root.running ? "⏸" : "▶"
            color: startStopHover.hovered ? Theme.effectiveGlowColor : Theme.textColor
            font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.3)
            layer.enabled: startStopHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: Theme.effectiveGlowShadowColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
            }
            HoverHandler { id: startStopHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: root.running ? root.stopRequested(root.itemId) : root.startRequested(root.itemId)
            }
        }

        Text {
            visible: !root.editing
            text: "🗑"
            color: deleteHover.hovered ? Theme.abandonedColor : Theme.mutedTextColor
            font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
            HoverHandler { id: deleteHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.deleteRequested(root.itemId, root.name) }
        }
    }
}

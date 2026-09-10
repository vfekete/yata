import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

// One row in the work-item list — name (double-click to rename, matching
// YatasRow.qml/TaskDelegate.qml's own double-click-to-edit convention),
// hover-revealed start/stop + sessions + non-working + delete buttons
// (same hover-reveal convention TaskDelegate.qml's own action row uses —
// see its own "Row { visible: root.hovered && !root.editing }" at the end
// of its RowLayout), total duration shown beneath the name.
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

    // While running, ticks every second so the duration shown actually
    // moves — durationLabel (the required property above, backed by
    // TimesheetModel's own durationLabel role) only reflects completed
    // sessions and is recomputed on start/stop, not continuously; this is
    // what makes second-level precision actually visible rather than a
    // number that happens to include seconds but never changes. A plain
    // property refreshed imperatively (not a binding calling
    // timesheetModel.liveDurationLabel() directly) — QML's binding
    // dependency tracker can't see through a method call into what it
    // reads internally, so a declarative binding here would never
    // re-evaluate on its own (confirmed real bug elsewhere this session:
    // a ComboBox.currentIndex binding built on indexOfValue() the same
    // way never updated either).
    property string displayedDuration: root.durationLabel
    function _refreshDisplayedDuration() {
        root.displayedDuration = root.running
            ? timesheetModel.liveDurationLabel(root.itemId) : root.durationLabel
    }
    onRunningChanged: root._refreshDisplayedDuration()
    onDurationLabelChanged: root._refreshDisplayedDuration()
    Component.onCompleted: root._refreshDisplayedDuration()

    Timer {
        interval: 1000
        repeat: true
        running: root.running
        onTriggered: root._refreshDisplayedDuration()
    }

    width: ListView.view.width
    height: Math.max(40, mainRow.implicitHeight + 14)

    HoverHandler { id: hoverHandler }

    // Highlighted (not just hovered) while this item is the one actually
    // being tracked — explicit follow-up request ("make it highlighted").
    // hoverColor still layers on top while both are true (hovering the
    // running row), same as a plain overlay addition would.
    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.running
            ? Qt.rgba(Theme.effectiveGlowColor.r, Theme.effectiveGlowColor.g, Theme.effectiveGlowColor.b, root.hovered ? 0.22 : 0.14)
            : (root.hovered ? Theme.hoverColor : "transparent")
        border.color: root.running ? Theme.effectiveGlowColor : "transparent"
        border.width: root.running ? 1 : 0
    }

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        spacing: 10

        // Column, NOT ColumnLayout — confirmed via a minimal reproduction
        // that a ColumnLayout nested inside this RowLayout silently
        // ignores Layout.fillWidth entirely (stays at its own implicit
        // content width, e.g. 41px, regardless of how much space the
        // RowLayout actually has), while a plain Column honors it
        // correctly. This is what pushed the action-icon Row into the
        // middle of the row instead of flush against the right edge —
        // the "column" here consuming only ~45px left the icons sitting
        // wherever 45px-plus-spacing happened to land, not at the true
        // right edge the fillWidth was supposed to push them to.
        Column {
            Layout.fillWidth: true
            spacing: 0
            visible: !root.editing

            Text {
                text: root.name
                color: root.nonWorking ? Theme.mutedTextColor : Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.bold: root.running
                font.italic: root.nonWorking

                TapHandler {
                    onDoubleTapped: root.editing = true
                }
            }

            Text {
                text: root.displayedDuration + (root.nonWorking ? qsTr(" (non-working)") : "")
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

        // Persistent status indicator, NOT hover-gated (unlike the action
        // buttons below) — same "a status stays visible, only the
        // ACTIONS hide behind hover" split TaskDelegate.qml's own
        // completedLabel/reopenGlyph (always shown) vs. doneBtn/cancelBtn/
        // deleteBtn (hover-only) already establishes. Warns when at least
        // one of this item's sessions was auto-closed by the abandoned-
        // session sweep (storage.py) — tap to jump straight to
        // SessionsDialog to review/fix it.
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

        // Action buttons — hover-only (explicit follow-up request: "the
        // icons... should not [be] always visible, the visual behavior
        // should mimic task row"), and pushed to the row's right edge by
        // the Column's own Layout.fillWidth above rather than an
        // anchors.right (same mechanism TaskDelegate.qml's own trailing
        // action Row relies on — nothing here needs anchoring, RowLayout
        // does it once the fillWidth sibling consumes the rest of the
        // space). Layout.alignment: Qt.AlignVCenter is NOT implied by
        // default for a Row nested in a RowLayout — has to be set
        // explicitly, or it drifts to the top of a taller row.
        Row {
            visible: root.hovered && !root.editing
            Layout.alignment: Qt.AlignVCenter
            spacing: 6

            Text {
                text: root.nonWorking ? "☑" : "☐"
                color: nonWorkingHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
                ToolTip.visible: nonWorkingHover.hovered
                ToolTip.text: qsTr("Non-working (excluded from totals)")
                HoverHandler { id: nonWorkingHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.nonWorkingToggled(root.itemId, !root.nonWorking) }
            }

            Text {
                text: "🕘"
                color: sessionsHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
                ToolTip.visible: sessionsHover.hovered
                ToolTip.text: qsTr("Edit sessions")
                HoverHandler { id: sessionsHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.sessionsRequested(root.itemId) }
            }

            Text {
                // Stop is a filled square, not the pause glyph — explicit
                // follow-up request ("change pause icon || for stop icon
                // (filled square)"): pausing implies resumable mid-
                // session state this plugin doesn't have (stopping always
                // ends the session; starting again begins a NEW one).
                text: root.running ? "⏹" : "▶"
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
                text: "🗑"
                color: deleteHover.hovered ? Theme.abandonedColor : Theme.mutedTextColor
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
                HoverHandler { id: deleteHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.deleteRequested(root.itemId, root.name) }
            }
        }
    }
}

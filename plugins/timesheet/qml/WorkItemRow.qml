import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

// One row in the work-item list. Layout follows r-10.md's "Bug wave 1"
// spec literally: a fixed-width state indicator (a filled circle — blank
// normally, "ongoing color" while running, "abandoned color" while an
// abandoned session exists), then a fixed-width, right-aligned duration
// column (blank for non-working items — their time is still tracked,
// just not shown), then the item's name (wraps across multiple lines
// once hovered, exactly like TaskDelegate.qml's own taskText). Hover-only
// action icons (mirroring TaskDelegate's own trailing action Row) sit at
// the far right.
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

    // Same forceEditing/editing split TaskDelegate.qml uses: editing is
    // true either because this is a brand new, still-unnamed item (name
    // is empty) or because the user double-clicked to rename an existing
    // one — kept as two separate properties (not one direct getter/
    // setter) so double-clicking an EXISTING item can cleanly exit back
    // to non-editing afterward without the "editing" state trying to
    // re-derive itself from an emptied-out name field along the way.
    property bool forceEditing: false
    readonly property bool editing: root.forceEditing || root.name.length === 0
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
            ? Qt.rgba(Theme.ongoingColor.r, Theme.ongoingColor.g, Theme.ongoingColor.b, root.hovered ? 0.22 : 0.14)
            : (root.hovered ? Theme.hoverColor : "transparent")
        border.color: root.running ? Theme.ongoingColor : "transparent"
        border.width: root.running ? 1 : 0
    }

    // Measures a representative "worst case" duration string, so every
    // row's duration column gets the SAME fixed width regardless of its
    // own text length — same "FontMetrics + a representative string"
    // technique TaskDelegate.qml's own completedStatus (DONE/CANCELED)
    // uses to keep a column's width, and therefore its right-aligned
    // digits, identical across every row. Durations are unbounded (a
    // multi-day session is plausible), so unlike DONE/CANCELED this can
    // still occasionally be exceeded by a genuinely huge value —
    // harmless, that row's own text just grows past the shared column
    // edge rather than the whole list silently losing its alignment for
    // one outlier.
    FontMetrics {
        id: durationMetrics
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        spacing: 10

        // State indicator: a filled circle, "big as 1/2 size of the
        // font" (explicit spec) — a real Rectangle rather than a text
        // glyph, so its size/color are exact rather than approximated by
        // whatever a font happens to render a dot-shaped character as.
        // Blank (fully transparent) for a plain active/non-running,
        // non-abandoned item.
        Rectangle {
            id: stateIndicator
            readonly property int diameter: Math.round(Theme.taskFontPixelSize * 0.5)
            Layout.preferredWidth: diameter
            Layout.preferredHeight: diameter
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: Math.round((Theme.taskFontPixelSize - diameter) / 2)
            radius: diameter / 2
            color: root.running ? Theme.ongoingColor
                : root.hasAbandonedSession ? Theme.abandonedColor : "transparent"
        }

        // Duration column: fixed width (see durationMetrics above),
        // right-aligned — "Items beneath each other should be aligned so
        // the timestamps will appear as in a single column right
        // aligned" (explicit spec). Blank for a non-working item: "track
        // the time, but do not display it."
        Text {
            Layout.preferredWidth: durationMetrics.advanceWidth("9999:59:59")
            Layout.alignment: Qt.AlignTop
            horizontalAlignment: Text.AlignRight
            text: root.nonWorking ? "" : root.displayedDuration
            color: Theme.mutedTextColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
        }

        Text {
            id: nameText
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            visible: !root.editing
            text: root.name
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            font.italic: root.nonWorking
            wrapMode: root.hovered ? Text.Wrap : Text.NoWrap
            elide: root.hovered ? Text.ElideNone : Text.ElideRight

            TapHandler {
                onDoubleTapped: root.forceEditing = true
            }
        }

        TextField {
            id: nameField
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            visible: root.editing
            text: root.name
            placeholderText: qsTr("New work item")
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }

            // Mirrors TaskDelegate.qml's own editField exactly (same
            // focus/default-name/cancel-on-Escape behavior, explicit
            // follow-up request: "the addition behaves the same as in
            // STP") — committedViaEnter/suppressAutoSave exist for the
            // identical reason documented there: Enter's own handler
            // already applied the change, so the onEditingFinished that
            // fires right after (focus loss as a side effect of the
            // model update) must not re-apply or override it, and a
            // brand-new row's own birth-time focus grab must not be
            // undone by the spurious blur Qt delivers when the click that
            // triggered ADD returns focus in the same event-loop tick.
            property bool committedViaEnter: false
            property bool suppressAutoSave: false

            onVisibleChanged: if (visible) forceActiveFocus()
            Component.onCompleted: {
                if (visible) {
                    suppressAutoSave = true
                    Qt.callLater(function() { suppressAutoSave = false })
                    forceActiveFocus()
                }
            }
            onEditingFinished: {
                if (committedViaEnter) return
                if (suppressAutoSave && root.name.length === 0) return
                root.forceEditing = false
                if (text.length > 0) {
                    root.renamed(root.itemId, text)
                } else if (root.name.length === 0) {
                    root.renamed(root.itemId, qsTr("New work item"))
                }
                // else: existing item, user cleared all text -- cancel edit silently
            }
            Keys.onReturnPressed: (event) => {
                event.accepted = true
                committedViaEnter = true
                if (text.length > 0) {
                    root.forceEditing = false
                    root.renamed(root.itemId, text)
                } else if (root.name.length === 0) {
                    root.deleteRequested(root.itemId, "")  // never-named ADD, cancelled -- no confirmation needed
                } else {
                    root.forceEditing = false
                }
            }
            Keys.onEscapePressed: {
                if (root.name.length === 0)
                    root.deleteRequested(root.itemId, "")  // never-named ADD, cancelled -- no confirmation needed
                else
                    root.forceEditing = false
            }
        }

        // Action buttons — hover-only (explicit follow-up request: "the
        // icons... should not [be] always visible, the visual behavior
        // should mimic task row"), and pushed to the row's right edge by
        // the fillWidth name Text/TextField above rather than an
        // anchors.right (same mechanism TaskDelegate.qml's own trailing
        // action Row relies on). Single-colored glyphs only (explicit
        // follow-up request: "no red trash bin") — no color-emoji
        // characters, which ignore Text.color entirely regardless of
        // what it's set to; delete uses "✕" (already this app's own
        // "remove/close" glyph elsewhere: Main.qml's close button,
        // Toolbar.qml's clear-search icon) instead of the 🗑 emoji, and
        // "edit sessions" uses the existing calendar SVG asset (via
        // iconProvider.coloredSvgUri, already proven single-color-
        // recolorable) instead of the 🕘 clock emoji.
        Row {
            visible: root.hovered && !root.editing
            Layout.alignment: Qt.AlignTop
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

            Image {
                id: sessionsIcon
                height: Math.round(Theme.taskFontPixelSize * 1.15)
                width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
                smooth: true
                source: iconProvider.coloredSvgUri("calendar",
                    (sessionsHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor).toString())
                ToolTip.visible: sessionsHover.hovered
                ToolTip.text: qsTr("Edit sessions")
                HoverHandler { id: sessionsHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.sessionsRequested(root.itemId) }
            }

            Text {
                // Stop is a filled square, not the pause glyph — explicit
                // follow-up request ("change pause icon || for stop icon
                // (filled square)"): pausing implied a resumable mid-
                // session state this plugin doesn't have (stopping always
                // ends the session; starting again begins a new one).
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
                text: "✕"
                color: deleteHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
                HoverHandler { id: deleteHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.deleteRequested(root.itemId, root.name) }
            }
        }
    }
}

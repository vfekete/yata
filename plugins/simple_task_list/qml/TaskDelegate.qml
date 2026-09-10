import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

Item {
    id: root
    required property int index
    required property string taskId
    required property string text
    required property string status
    required property string dayLabel
    required property string completedAt
    required property string note

    property bool forceEditing: false
    readonly property bool editing: forceEditing || text.length === 0
    readonly property bool hovered: hoverHandler.hovered

    // New feature: the row's own hover-on background follows this window's
    // custom color (r-4.md, assigned via the YATAS list) instead of the
    // generic grey — CRT tints are untouched (explicit request: "already
    // done, no need to change anything there" — each one already tints its
    // own Theme.hoverColor to its own phosphor color, see ThemeImpl.qml's
    // palettes). Only kicks in for the "none" tint AND only once a custom
    // color is actually assigned — "under 'window color' I understand color
    // assigned to it in YATAS list", so absent that assignment there's no
    // such color to use and the original grey stands.
    //
    // effectiveBorderColor exists purely to coerce hostSettings.borderColor
    // (a plain string) into a real `color` value so .r/.g/.b are readable —
    // its "#000000" fallback is never actually used for that (rowHoverColor
    // only reads it in the branch where borderColor is already known
    // non-empty).
    readonly property color effectiveBorderColor: hostSettings.borderColor !== "" ? hostSettings.borderColor : "#000000"
    // Alpha 0.18, the author's own preference after trying a few values
    // live — noticeably more than the grey/white overlay it replaces
    // (Theme.hoverColor's own 0.06–0.08 for the "none" tint) needs, since a
    // specific hue has to work harder than grey to register as "this
    // window's color" rather than just a slightly different shade of grey.
    readonly property color rowHoverColor: (Theme.tintName === "none" && hostSettings.borderColor !== "")
        ? Qt.rgba(effectiveBorderColor.r, effectiveBorderColor.g, effectiveBorderColor.b, 0.18)
        : Theme.hoverColor
    // Set briefly by ListView.flashTaskId after "to task" navigation (see
    // LinksView), so the destination row reads as "selected" even though the
    // real mouse cursor didn't move there. Drives flashOverlay below rather
    // than the plain hover tint — a sudden jump to full glow brightness, then
    // an eased fade to transparent, reads as "just landed here" rather than
    // as a real (and possibly misleading) hover state.
    readonly property bool flashed: root.taskId !== "" && root.ListView.view.flashTaskId === root.taskId
    onFlashedChanged: if (flashed) {
        flashFade.stop()
        flashOverlay.opacity = 1.0
        flashFade.start()
    }

    function activateFocus() {
        editField.forceActiveFocus()
    }

    // True for the whole duration of a drag this row is the source of —
    // its own slot collapses to nothing (below) so the rest of the list
    // steps up to fill the gap, matching what the list will actually look
    // like once dropped, rather than leaving a static faded placeholder
    // behind in its original spot.
    readonly property bool dragSource: root.ListView.view.dragActive
                                        && root.index === root.ListView.view.dragFromIndex
    // True when THIS row is where the drop would land right now — driven
    // by dragHoverActive/dragHoverIndex, which Main.qml's Connections on
    // windowManager.taskDragHoverChanged keeps updated for whichever
    // window is currently the hover target (this window itself while
    // reordering in place, or a different window's list during a
    // cross-window drag — same mechanism, same properties, either way).
    readonly property bool showGapBelow: root.ListView.view.dragHoverActive
                                          && root.ListView.view.dragHoverIndex === root.index
                                          && !(root.ListView.view.dragActive
                                               && root.ListView.view.dragFromIndex === root.index)
    // A single-line-height approximation of "how tall the dropped item
    // would look here" — not the dragged task's own actual (possibly
    // multi-line) height, which would need broadcasting a third value
    // alongside DragGhost's text/status; the shaped, highlighted box
    // conveys "it goes here" without needing to be pixel-exact.
    readonly property int gapHeight: Math.max(30, Theme.taskFontPixelSize + 16)

    width: ListView.view.width
    height: (dragSource ? 0 : Math.max(30, mainRow.implicitHeight + 12)) + (showGapBelow ? gapHeight : 0)
    // Hovering toggles taskText between wrapped/elided, which changes
    // mainRow.implicitHeight and thus this row's height. Without animating
    // that change, the instant resize shifts every row below it under the
    // pointer in the same frame, so the mouse ends up over a different row
    // than the one it was just on ("jumping" — see claude-docs/freq/r-1.md).
    // The same animation now also covers dragSource's collapse-to-0 and
    // showGapBelow's placeholder growing in, so the whole list reflows
    // smoothly rather than snapping.
    Behavior on height {
        NumberAnimation { duration: 120; easing.type: Easing.InOutQuad }
    }

    // Text.linkColor is unreliable even with StyledText (Qt may ignore it).
    // Embed the color directly via <font color> so it is always applied.
    // lc is passed as an argument so the binding tracks Theme.linkColor as a
    // dependency and re-evaluates when the theme changes.
    function mdToHtml(md, lc) {
        var codes = []
        // Stash code spans so inner content isn't mangled by later passes.
        var s = md.replace(/`([^`\n]+)`/g, function(_, c) {
            codes.push(c.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'))
            return '\x00' + (codes.length - 1) + '\x00'
        })
        s = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        s = s.replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>')
        s = s.replace(/\*([^*\n]+)\*/g, '<i>$1</i>')
        s = s.replace(/~~([^~\n]+)~~/g, '<s>$1</s>')
        s = s.replace(/\[([^\]\n]*)\]\(([^)\n]*)\)/g,
            '<a href="$2"><font color="' + lc + '">$1</font></a>')
        s = s.replace(/\n/g, '<br>')
        return s.replace(/\x00(\d+)\x00/g, function(_, i) {
            return '<code>' + codes[parseInt(i)] + '</code>'
        })
    }

    HoverHandler { id: hoverHandler }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: itemMenu.popup()
    }

    // Press-and-drag from anywhere on the row (not just the up/down
    // orderControls buttons below, which are now purely a click
    // affordance) — a DragHandler
    // rather than a MouseArea specifically because it only takes the
    // exclusive grab once the pointer crosses the platform's real drag
    // threshold. A plain click/double-click (edit), a link tap, a
    // hover-button tap, or a right-click (context menu) never reaches that
    // threshold, so this handler simply never activates for those and every
    // other gesture on this row keeps working exactly as before — the
    // standard Qt Quick pattern for letting a tap and a drag coexist on the
    // same item without one stealing the other's events.
    DragHandler {
        id: rowDrag
        target: null
        enabled: !root.editing && taskModel.canReorder
        acceptedButtons: Qt.LeftButton

        // Latest known pointer position in global/screen coordinates, updated
        // by onCentroidChanged below on every raw pointer-move event (which
        // can fire far more often than the screen actually redraws). The
        // expensive per-move work — windowManager.windowAt()'s Python round
        // trip + cross-window broadcast, and moveDragGhost()'s real native
        // OS window reposition — used to run directly inside
        // onCentroidChanged, once per raw event. A fast mouse move delivers
        // many more of those than there are frames to show them in, so that
        // saturated the event loop with (comparatively costly) native window
        // moves; the cross-window placeholder update depends on that same
        // single-threaded loop finding a free moment, so it visibly lagged
        // behind the always-locally-smooth same-window case. dragUpdateTimer
        // below now does that expensive work at a capped, steady ~60fps
        // instead, reading whatever the latest position happens to be.
        property real lastGlobalX: 0
        property real lastGlobalY: 0

        onActiveChanged: {
            var view = root.ListView.view
            if (active) {
                view.dragActive = true
                view.dragFromIndex = root.index
                view.dragHoverIndex = root.index
                // Floating preview of the row being dragged (DragGhost.qml,
                // one app-wide instance) — stays visible even once the
                // pointer leaves this window's own bounds, unlike anything
                // drawn as a normal Item here.
                windowManager.showDragGhost(root.text, root.status)
                return
            }
            // Captured up front, before any model-mutating call below:
            // moving the task to another window removes it from THIS
            // window's model, which synchronously destroys this exact
            // delegate (unlike same-window reorder, where the row still
            // exists afterward, just repositioned, so the delegate
            // survives) — see 0.18.1's fix for the same reasoning, `view`
            // above already followed it too.
            var wm = windowManager
            if (view.dragActive) {
                if (view.dragTargetWindowId !== "" && view.dragTargetWindowId !== windowId) {
                    wm.moveTaskToWindow(windowId, root.taskId, view.dragTargetWindowId)
                } else if (view.dragTargetWindowId === windowId
                           && view.dragHoverIndex >= 0 && view.dragHoverIndex !== view.dragFromIndex) {
                    taskModel.moveTask(view.dragFromIndex, view.dragHoverIndex)
                }
                // else: dropped outside every window, or back on its own
                // original slot — cancel, nothing to do, the row's own
                // collapsed height (see dragSource below) springs back on
                // its own once dragActive/dragFromIndex reset below.
            }
            wm.hideDragGhost()
            wm.clearDragHover()
            view.dragActive = false
            view.dragFromIndex = -1
            view.dragHoverIndex = -1
            view.dragTargetWindowId = ""
        }

        onCentroidChanged: {
            if (!root.ListView.view.dragActive)
                return
            // Cheap and local only — just records where the pointer is right
            // now. mapToItem(null, ...) gives window-local content coords
            // (this window has no decorations to offset by), and every
            // top-level QWindow's own x/y is already in global/screen space,
            // so adding them together is the pointer's true global position
            // without needing QQuickWindow.mapToGlobal. The actual expensive
            // work (windowAt()/moveDragGhost()) happens in dragUpdateTimer
            // below, not here — see rowDrag's own comment on why.
            var win = root.Window.window
            var posInWindow = root.mapToItem(null, centroid.position.x, centroid.position.y)
            rowDrag.lastGlobalX = win.x + posInWindow.x
            rowDrag.lastGlobalY = win.y + posInWindow.y
        }
    }

    // Drives the expensive per-move drag work at a capped, steady rate
    // instead of on every raw pointer event — see rowDrag.lastGlobalX's own
    // comment for why. windowAt() no longer excludes this row's own window —
    // dragging within the source window is just "the pointer happens to be
    // over the same window's geometry", the same case as any other window,
    // so ITS OWN row-reflow/placeholder/auto-scroll is driven the identical
    // way, via windowManager's broadcast (see Main.qml's Connections on
    // taskDragHoverChanged) rather than computed locally here — one single
    // code path for both same-window and cross-window hovering, not two.
    Timer {
        id: dragUpdateTimer
        interval: 16
        repeat: true
        running: rowDrag.active
        onTriggered: {
            root.ListView.view.dragTargetWindowId =
                windowManager.windowAt(rowDrag.lastGlobalX, rowDrag.lastGlobalY)
            windowManager.moveDragGhost(rowDrag.lastGlobalX, rowDrag.lastGlobalY)
        }
    }

    // When the user clicks on a non-editing task row, take focus from whatever
    // currently has it (e.g. an editing TextField in another delegate) so that
    // its onEditingFinished fires and saves correctly.  Non-interactive items
    // (Text, Rectangle) don't accept keyboard focus, so without this handler a
    // click on another task row would silently leave focus on the editor.
    //
    // Must target `root` (this delegate's Item), NOT root.ListView.view: the
    // ListView is a Flickable and already has activeFocus=true as an ancestor
    // of the editing TextField, so forceActiveFocus() on it is a no-op.
    // Targeting `root` (a sibling of the editing delegate in the contentItem)
    // genuinely steals focus because root.activeFocus is false.
    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: !root.editing
        onTapped: root.forceActiveFocus()
    }

    Menu {
        id: itemMenu
        MenuItem { text: qsTr("Delete task"); onTriggered: taskModel.deleteTask(root.taskId); padding: 10 }
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? root.rowHoverColor : "transparent"
    }

    // "To task" navigation flash: 3 consecutive blinks totaling 1.2s. Each
    // blink jumps instantly to full-brightness glow (PropertyAction, no
    // fade-in) then fades out over the rest of its 1/3 share via
    // NumberAnimation. Uses the same glow color as the FilterBar toggle
    // buttons' active state, so it reads as "on-palette highlight" rather
    // than introducing a new color meaning.
    Rectangle {
        id: flashOverlay
        anchors.fill: parent
        radius: 4
        color: Theme.filterGlowColor
        opacity: 0
    }
    SequentialAnimation {
        id: flashFade
        loops: 3
        PropertyAction { target: flashOverlay; property: "opacity"; value: 1.0 }
        NumberAnimation {
            target: flashOverlay
            property: "opacity"
            to: 0.0
            duration: 1200 / 3
            easing.type: Easing.OutCubic
        }
    }

    // Row-shaped drop-target placeholder — reserved via showGapBelow's
    // contribution to height above, so it's real reflowed space (every row
    // after this one visibly steps down to make room), not just an overlay
    // painted on top of existing content. Bottom-anchored so it occupies
    // exactly the newly-added extra space at the bottom — this only works
    // cleanly because mainRow below is now top-anchored with a fixed
    // margin (not vertically centered in the whole, now-taller, box): a
    // centered mainRow would recentre *downward* into the placeholder's
    // own space as height grew, visibly overlapping/cutting through its
    // own content — that's exactly what this fixes, mainRow's on-screen
    // position no longer depends on how tall the placeholder makes the row.
    // filterGlowColor is the same "default cyan glow / tint's own accent
    // for CRT themes" rule already used for every other on/active glow in
    // this app (FilterBar's toggle buttons).
    Rectangle {
        id: dropPlaceholder
        visible: root.showGapBelow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: root.gapHeight
        radius: 4
        color: Qt.rgba(Theme.filterGlowColor.r, Theme.filterGlowColor.g, Theme.filterGlowColor.b, 0.15)
        border.color: Theme.filterGlowColor
        border.width: 2
    }

    opacity: root.dragSource ? 0.4 : 1.0

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        // Top-anchored with a fixed margin, NOT vertically centered — this
        // row's own height is Math.max(30, mainRow.implicitHeight + 12), so
        // a 6px top margin reproduces the same look as centering did for a
        // normal row (12px split evenly), but — unlike centering — keeps
        // mainRow's position fixed even when extra height gets appended
        // below it for the drop placeholder (see dropPlaceholder above);
        // centering would otherwise shift mainRow down into that reserved
        // space as the row grows taller, visibly overlapping it.
        anchors.top: parent.top
        anchors.topMargin: 6
        // Day-grouped view gets extra left indent so rows read as nested
        // under their day header rather than flush with it.
        anchors.leftMargin: taskModel.groupByDay ? 24 : 4
        anchors.rightMargin: 4
        spacing: 4

        Column {
            id: orderControls
            // r-7.md: replaces the old "⋮⋮" drag-handle glyph with explicit
            // up/down icon buttons (real coloredSvgUri icons — a plain "^"/
            // "v" ASCII pair, tried first, read as illustrative shorthand
            // rather than an actual UI spec and was too easy to misread at
            // a glance; same iconProvider.coloredSvgUri recolor pipeline as
            // every other themed icon in this app, e.g. noteIconImg below).
            // Moving a task this way switches ordering back to Manual
            // exactly like drag&drop does (see
            // TaskListModel.moveTaskUp/moveTaskDown). Purely a visual/click
            // affordance, same as the glyph it replaces: the row-wide drag
            // gesture (rowDrag above) still works from anywhere on the row,
            // not just here.
            visible: root.hovered && taskModel.canReorder
            Layout.alignment: Qt.AlignVCenter
            // A clear gap between the two, not a cramped stack — explicit
            // request ("bigger, and vertically a little bit apart, so it is
            // easier to spot them and know which is which").
            spacing: Math.round(Theme.taskFontPixelSize * 0.4)

            readonly property bool canMoveUp: root.index > 0
            readonly property bool canMoveDown: root.index < root.ListView.view.count - 1
            // Bigger than a normal glyph on purpose (same "easier to spot"
            // request) — noteIconImg/deleteBtn-sized icons elsewhere in
            // this row are tuned to sit quietly next to task text; these
            // two are the only controls a user needs to find at a glance
            // while skimming a whole list.
            readonly property int iconSize: Math.round(Theme.taskFontPixelSize * 1.15)

            Image {
                id: upIcon
                width: orderControls.iconSize
                height: orderControls.iconSize
                fillMode: Image.PreserveAspectFit
                smooth: true
                opacity: orderControls.canMoveUp ? 1.0 : 0.35
                source: iconProvider.coloredSvgUri("move_up",
                    (upHover.hovered && orderControls.canMoveUp ? Theme.effectiveGlowColor : Theme.mutedTextColor).toString())
                layer.enabled: upHover.hovered && orderControls.canMoveUp
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.1
                }

                HoverHandler {
                    id: upHover
                    enabled: orderControls.canMoveUp
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    enabled: orderControls.canMoveUp
                    onTapped: taskModel.moveTaskUp(root.taskId)
                }
            }
            Image {
                id: downIcon
                width: orderControls.iconSize
                height: orderControls.iconSize
                fillMode: Image.PreserveAspectFit
                smooth: true
                opacity: orderControls.canMoveDown ? 1.0 : 0.35
                source: iconProvider.coloredSvgUri("move_down",
                    (downHover.hovered && orderControls.canMoveDown ? Theme.effectiveGlowColor : Theme.mutedTextColor).toString())
                layer.enabled: downHover.hovered && orderControls.canMoveDown
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.1
                }

                HoverHandler {
                    id: downHover
                    enabled: orderControls.canMoveDown
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    enabled: orderControls.canMoveDown
                    onTapped: taskModel.moveTaskDown(root.taskId)
                }
            }
        }

        Column {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            Layout.rightMargin: 50
            visible: !root.editing
            spacing: 2

            Text {
                id: taskText
                width: parent.width
                // r-5.md: color only, no glow — this text mixes plain/bold/
                // italic prose with zero or more inline links in one
                // continuous StyledText block, and MultiEffect's glow
                // applies to a whole Item's rendered layer, not a
                // substring within it; glowing this Text would glow ALL of
                // it, not just the link portions. LinkRow.qml (Links view)
                // gets the full glow instead, since a row there is 100%
                // link text with nothing else to accidentally light up.
                text: root.mdToHtml(root.text, Theme.effectiveLinkColor)
                textFormat: Text.StyledText
                wrapMode: root.hovered ? Text.Wrap : Text.NoWrap
                elide: root.hovered ? Text.ElideNone : Text.ElideRight
                horizontalAlignment: Text.AlignJustify
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                color: {
                    if (root.status === "done") return Theme.doneColor
                    if (root.status === "cancelled") return Theme.cancelledColor
                    return Theme.textColor
                }
                font.strikeout: root.status !== "active"

                onLinkActivated: link => Qt.openUrlExternally(link)

                HoverHandler {
                    cursorShape: taskText.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor
                }

                TapHandler {
                    onDoubleTapped: root.forceEditing = true
                }
            }

            Row {
                id: completedLabel
                width: parent.width
                visible: root.status !== "active"
                spacing: 0

                // Measures "DONE"/"CANCELED" in the status text's own font so
                // completedStatus can be given a fixed width below — otherwise
                // the shorter "DONE" would let the timestamp creep left,
                // leaving timestamps unaligned across rows depending on status.
                FontMetrics {
                    id: statusFontMetrics
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
                }

                Text {
                    id: completedStatus
                    textFormat: Text.PlainText
                    text: root.status === "done" ? qsTr("DONE") : qsTr("CANCELED")
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
                    width: Math.max(statusFontMetrics.advanceWidth(qsTr("DONE")), statusFontMetrics.advanceWidth(qsTr("CANCELED"))) + statusFontMetrics.advanceWidth("     ")
                    readonly property color labelColor: root.status === "done" ? Theme.completedDoneLabelColor : Theme.completedCancelledLabelColor
                    color: labelColor
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: completedStatus.labelColor
                        shadowBlur: 1.0
                        shadowHorizontalOffset: 0
                        shadowVerticalOffset: 0
                        shadowOpacity: 1.0
                        shadowScale: 1.05
                    }
                }

                Text {
                    id: completedTimestamp
                    visible: root.completedAt !== ""
                    textFormat: Text.PlainText
                    text: {
                        if (root.completedAt === "") return ""
                        var dt = new Date(root.completedAt)
                        var dd = String(dt.getDate()).padStart(2, '0')
                        var mm = String(dt.getMonth() + 1).padStart(2, '0')
                        var HH = String(dt.getHours()).padStart(2, '0')
                        var MM = String(dt.getMinutes()).padStart(2, '0')
                        return dd + "-" + mm + "-" + dt.getFullYear() + " " + HH + ":" + MM
                    }
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
                    color: root.status === "done" ? Theme.doneColor : Theme.cancelledColor
                }

                // vfe: spacer, timestamp was too close and adding additional
                //      spaces to the timestamp text to create visual margin
                //      smells bad and feels like antipattern
                Item {
                    width: Math.round(Theme.taskFontPixelSize * 0.8)
                    height: 1
                }


                // r-6.md follow-up: always present now (not just once a
                // note exists) — clicking it opens NoteEditorView to ADD
                // one when there isn't one yet, not only to view/edit an
                // existing one. Click switches the content area to
                // NoteEditorView for this task, via the same custom-
                // property-on-listView convention TaskDelegate already
                // uses for dragActive/dragHoverIndex/flashTaskId.
                // Hover-only color/glow, matching the ✓/✕/↺/🗑 action-icon
                // convention (not completedStatus's own always-on glow) —
                // this is a neutral utility affordance, not a status
                // indicator. Placed last (after the timestamp, a bigger
                // gap than status→timestamp's own) per explicit layout
                // request: "STATUS [TIMESTAMP]  NOTE_BUTTON".
                Item {
                    width: noteIconImg.width + Theme.nonActiveActionIconGap
                    height: completedStatus.implicitHeight
                    Image {
                        id: noteIconImg
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: Theme.taskFontPixelSize
                        width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        source: iconProvider.coloredSvgUri("notes",
                            (noteIconHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor).toString())
                        layer.enabled: noteIconHover.hovered
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowColor: Theme.effectiveGlowShadowColor
                            shadowBlur: 1.0
                            shadowHorizontalOffset: 0
                            shadowVerticalOffset: 0
                            shadowOpacity: 1.0
                            shadowScale: 1.05
                        }
                        HoverHandler { id: noteIconHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: root.ListView.view.noteEditorTaskId = root.taskId }
                    }
                }

                // Moved here from the row's hover-action buttons — this
                // Row is already status-gated (visible: root.status !==
                // "active" above), so no extra guard is needed. Sits right
                // of the note icon, always visible like it (not
                // hover-gated), matching the note icon's own convention.
                Item {
                    width: reopenGlyph.implicitWidth + Theme.nonActiveActionIconGap
                    height: completedStatus.implicitHeight

                    Text {
                        id: reopenGlyph
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: "↺"
                        font.family: Theme.fontFamily
                        font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
                        color: reopenGlyphHover.hovered ? Theme.effectiveGlowColor : Theme.accentColor
                        layer.enabled: reopenGlyphHover.hovered
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowColor: Theme.effectiveGlowShadowColor
                            shadowBlur: 1.0
                            shadowHorizontalOffset: 0
                            shadowVerticalOffset: 0
                            shadowOpacity: 1.0
                            shadowScale: 1.05
                        }
                        HoverHandler { id: reopenGlyphHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: taskModel.setStatus(root.taskId, "active") }
                    }
                }
            }
        }

        TextField {
            id: editField
            // r-8.md "The glass lock": Main.qml's auto-locked exception
            // reads this via Window.activeFocusItem.objectName, rather than
            // a per-delegate signal relayed up to listView — the latter
            // would go stale if this delegate is ever destroyed (e.g. a
            // model reset from Reload) without first firing a proper
            // focus-lost signal, permanently stranding the window unlocked.
            // Window.activeFocusItem is Qt's own live focus tracking, so it
            // can never go stale that way.
            objectName: "taskDescriptionField"
            Layout.fillWidth: true
            visible: root.editing
            text: root.text
            placeholderText: qsTr("Task name")
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }

            // Set to true by Keys.onReturnPressed before calling setText so that
            // the spurious onEditingFinished that fires during _recompute()'s
            // beginResetModel() (which causes focus loss) does not overwrite the
            // value just committed by the Enter handler.
            property bool committedViaEnter: false

            // onVisibleChanged handles the double-click-to-edit path (visible
            // transitions false→true). Component.onCompleted handles new-task
            // creation (visible is already true at birth, so onVisibleChanged
            // never fires for those).
            onVisibleChanged: if (visible) forceActiveFocus()
            Component.onCompleted: {
                if (visible) {
                    // Suppress onEditingFinished for the first event-loop tick:
                    // the click that triggered addTask() causes Qt to steal focus
                    // back in the same tick, which would instantly fire
                    // onEditingFinished and auto-save "Task name" — hiding the
                    // field before the 100 ms focus timer can re-grab it.
                    suppressAutoSave = true
                    Qt.callLater(function() { suppressAutoSave = false })
                    forceActiveFocus()
                }
            }
            // True for one event-loop tick after a new-task delegate is born,
            // to block the spurious onEditingFinished that fires when Qt steals
            // focus back during click-event processing (see Component.onCompleted).
            property bool suppressAutoSave: false
            // Fires on focus loss (click-away). Enter key is handled below and
            // sets committedViaEnter=true so this handler skips the spurious fire
            // that beginResetModel() triggers inside setText().
            onEditingFinished: {
                if (committedViaEnter) return
                // Suppress the immediate spurious fire on new-task creation.
                if (suppressAutoSave && root.text.length === 0) return
                root.forceEditing = false
                if (text.length > 0) {
                    taskModel.setText(root.taskId, text)
                } else if (root.text.length === 0) {
                    taskModel.setText(root.taskId, qsTr("Task name"))
                }
                // else: existing task, user cleared all text → cancel edit silently
            }
            Keys.onReturnPressed: (event) => {
                event.accepted = true
                committedViaEnter = true
                if (text.length > 0) {
                    root.forceEditing = false
                    taskModel.setText(root.taskId, text)
                } else if (root.text.length === 0) {
                    taskModel.deleteTask(root.taskId)
                } else {
                    root.forceEditing = false
                }
            }
            Keys.onEscapePressed: {
                if (root.text.length === 0)
                    taskModel.deleteTask(root.taskId)
                else
                    root.forceEditing = false
            }
        }

        Row {
            visible: root.hovered && !root.editing
            spacing: 4
            Layout.alignment: Qt.AlignTop

            HoldToNoteButton {
                id: doneBtn
                visible: root.status === "active"
                taskId: root.taskId
                targetStatus: "done"
                glyph: "✓"
                idleColor: Theme.doneColor
                note: root.note
            }
            HoldToNoteButton {
                id: cancelBtn
                visible: root.status === "active"
                taskId: root.taskId
                targetStatus: "cancelled"
                glyph: "✕"
                idleColor: Theme.cancelledColor
                note: root.note
            }
            Text {
                id: deleteBtn
                text: "🗑"
                color: deleteBtnHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                layer.enabled: deleteBtnHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                HoverHandler { id: deleteBtnHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: deleteConfirm.open() }
            }
        }
    }

    DialogWindow {
        id: deleteConfirm
        title: qsTr("Delete task?")
        // Explicit width so implicitWidth doesn't have to be derived from
        // font-scaled content — without this, changing font.pixelSize
        // above (e.g. on every Ctrl+=/Ctrl+- zoom step) fed back into this
        // dialog's own implicitWidth calculation and Qt Quick Controls'
        // Basic style logged "Binding loop detected for property
        // implicitWidth" repeatedly. Same fix/formula as
        // DeleteWindowDialog.qml's width.
        contentWidth: Math.max(260, Math.round(Theme.taskFontPixelSize * 20))
        onAccepted: taskModel.deleteTask(root.taskId)

        Label {
            text: qsTr("This action cannot be undone.")
            color: Theme.textColor
            font.pixelSize: Theme.taskFontPixelSize
        }
    }
}

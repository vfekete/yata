import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root
    visible: true
    color: "transparent"
    // Opacity is applied to the content wrapper below, NOT to the Window
    // itself, so popup menus (rendered in the Window's Overlay layer above
    // the content) always appear at full opacity regardless of the user's
    // slider setting — preventing an irreversible "can't see the menu"
    // situation at very low opacity values.
    // Qt.WindowStaysOnBottomHint is intentionally not used: on GNOME/Mutter
    // (the primary target platform) it places the window below the desktop
    // background layer itself, making it invisible rather than merely
    // "beneath other windows, above icons". See README.md.
    flags: Qt.FramelessWindowHint

    // MonthView/YearView's currently-displayed page. Not persisted — each
    // resets to the current month/year at app start; navigating away and
    // back within a session keeps whatever was last paged to, since these
    // are plain properties on a component that's never destroyed.
    property int calYear: new Date().getFullYear()
    property int calMonth: new Date().getMonth() + 1
    property int calYearPage: new Date().getFullYear()

    // This window's own display tag (r-3.md multi-window support) — shown
    // in the top border label below. windowId is a per-window context
    // property (set once at creation in main.py, never changes); the tag
    // itself is mutable (rename via YatasView, possibly from a *different*
    // window if it's renaming this one from its own window list), so it's
    // re-read from windowManager whenever ANY window's tag changes rather
    // than cached as a one-shot value.
    property string windowTag: windowManager.tagFor(windowId)
    Connections {
        target: windowManager
        function onWindowsChanged() { root.windowTag = windowManager.tagFor(windowId) }
    }
    // Double-click the tag label (below) to rename it in place — swaps the
    // label for tagEditField while true.
    property bool editingTag: false

    // True while another window's task drag is hovering over THIS window —
    // drives the border highlight below. windowManager broadcasts one
    // shared signal for every window rather than each polling its own
    // geometry against the pointer. The same broadcast also carries the
    // pointer's global position, which — only once translated into this
    // window's own local coordinates below — drives listView's reflow
    // placeholder and edge auto-scroll (see listView's own dragHoverActive/
    // dragHoverIndex/lastDragLocalY, and TaskDelegate.qml's dragSource/
    // showGapBelow, which key off exactly those two properties whether the
    // hover target is this window's own list during a same-window drag or
    // a different window's list during a cross-window one — one mechanism,
    // not two).
    property bool dragHoverActive: false
    Connections {
        target: windowManager
        function onTaskDragHoverChanged(targetWindowId, globalX, globalY) {
            root.dragHoverActive = targetWindowId === windowId
            if (targetWindowId !== windowId) {
                listView.dragHoverActive = false
                listView.dragHoverIndex = -1
                return
            }
            // mapFromItem(null, ...) is the inverse of the mapToItem(null,
            // ...) technique TaskDelegate.qml uses to go the other
            // direction — both convert between a window's own local
            // (scene) coordinates and some other coordinate system, here
            // going from "this window's local point" to "listView's own
            // local point".
            var posInWindow = Qt.point(globalX - root.x, globalY - root.y)
            var posInListView = listView.mapFromItem(null, posInWindow.x, posInWindow.y)
            listView.dragHoverActive = true
            var idx = listView.indexAt(1, posInListView.y + listView.contentY)
            if (idx >= 0)
                listView.dragHoverIndex = idx
            listView.lastDragLocalY = posInListView.y
            // Reported back so a cross-window drop (TaskDelegate.qml calling
            // windowManager.moveTaskToWindow, in the SOURCE window) knows
            // where THIS (target) window's placeholder actually is — only
            // this window's own layout can compute it, so it can't be
            // derived from the source window's side of the drag.
            windowManager.setDragHoverIndex(listView.dragHoverIndex)
        }
    }

    Shortcut {
        sequences: [StandardKey.ZoomIn]
        onActivated: appSettings.fontScale = Math.min(appSettings.fontScale + 0.1, appSettings.maxFontScale)
    }
    Shortcut {
        sequences: [StandardKey.ZoomOut]
        onActivated: appSettings.fontScale = Math.max(appSettings.fontScale - 0.1, appSettings.minFontScale)
    }
    Shortcut {
        sequence: "Ctrl+0"
        onActivated: appSettings.fontScale = appSettings.defaultFontScale
    }

    x: appSettings.x
    y: appSettings.y
    width: appSettings.width
    height: appSettings.height
    // Twice the combined width of the ADD/RELOAD/THEME/LINKS/YATAS toolbar
    // buttons, scaling with font zoom same as they do
    // (toolbar.actionButtonsWidth is itself font-scale-dependent) — below
    // this, FilterBar's groups have nowhere reasonable left to wrap into.
    minimumWidth: toolbar.actionButtonsWidth * 2

    onXChanged: appSettings.x = x
    onYChanged: appSettings.y = y
    onWidthChanged: appSettings.width = width
    onHeightChanged: appSettings.height = height

    // Grows width up to minimumWidth when needed (e.g. a persisted width
    // from before a toolbar button existed, now narrower than the real
    // minimum — see CHANGELOG 0.15.4) — done as a plain imperative
    // assignment, NOT folded into width's own binding above
    // (width: Math.max(appSettings.width, minimumWidth)), because that
    // shape is a genuine QML binding loop: width's binding would depend on
    // appSettings.width, which onWidthChanged right above writes to on
    // every width change, and the engine's binding-loop detector correctly
    // flags that pattern (logged "Binding loop detected for property
    // width" on every startup/window creation, even though it happens to
    // converge rather than truly infinite-loop). An imperative assignment
    // here breaks/replaces the `width: appSettings.width` binding the
    // moment it actually needs to fire, exactly like a user's own resize
    // already does — width keeps persisting correctly afterward via
    // onWidthChanged either way.
    function ensureMinimumWidth() {
        if (width < minimumWidth)
            width = minimumWidth
    }
    Component.onCompleted: ensureMinimumWidth()
    onMinimumWidthChanged: ensureMinimumWidth()

    // Right-click anywhere on the background for theme + quit. Placed first so
    // real controls (declared later / painted on top) get first refusal at clicks.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: contextMenu.popup()
    }

    ThemeMenu {
        id: contextMenu
        showQuit: true
    }

    // Ctrl+Wheel zoom interceptor. Sits above all content (z:999) so its
    // WheelHandler sees Ctrl+Wheel events before the ListView's Flickable
    // can consume them for scrolling. Normal (no-modifier) wheel events are
    // not matched by acceptedModifiers and propagate to the ListView as usual.
    Item {
        z: 999
        anchors.fill: parent

        WheelHandler {
            acceptedModifiers: Qt.ControlModifier
            onWheel: (event) => {
                event.accepted = true
                var scrollingUp = event.angleDelta.y > 0
                // Default (not inverted): scroll up → zoom in, scroll down → zoom out.
                var zoomIn = appSettings.wheelZoomInverted ? !scrollingUp : scrollingUp
                if (zoomIn)
                    appSettings.fontScale = Math.min(appSettings.fontScale + 0.1, appSettings.maxFontScale)
                else
                    appSettings.fontScale = Math.max(appSettings.fontScale - 0.1, appSettings.minFontScale)
            }
        }
    }

    // Content wrapper: opacity applied here keeps popup menus (which render
    // in the Window Overlay above this Item) always at full opacity.
    Item {
        anchors.fill: parent
        opacity: Theme.windowOpacity

        // The window itself stays fully transparent (per spec); this wash is
        // what actually paints each tint's background, translucent so the
        // window still reads as "transparent" rather than opaque.
        //
        // topMargin reserves room for the tag label below to straddle this
        // Rectangle's top edge (half above it, half below — see tagLabelBg)
        // — the label can't be positioned with a negative y to achieve that
        // the usual way: a QQuickWindow's real drawable surface starts at
        // y=0, so any content above that is genuinely not rendered on a
        // live composited window (confirmed live; this was invisible in
        // offscreen grabWindow() testing, which is apparently more
        // forgiving of negative-y content than a real GPU-backed surface).
        Rectangle {
            anchors.fill: parent
            anchors.topMargin: tagLabelBg.height / 2
            radius: 6
            color: Theme.contentBackground
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 6
            // Extra headroom so the toolbar doesn't collide with the tag
            // label sitting on the border line above it (see tagLabelBg
            // near the bottom of this file) — scales with the label's own
            // (font-zoom-dependent) height rather than a fixed guess.
            anchors.topMargin: 6 + tagLabelBg.height / 2 + 4
            spacing: 2

            Toolbar {
                id: toolbar
                Layout.fillWidth: true
                linksActive: filterBar.linksActive
                onLinksToggled: filterBar.setGrouping("links", !filterBar.linksActive)
                yatasActive: filterBar.yatasActive
                onYatasToggled: filterBar.setGrouping("yatas", !filterBar.yatasActive)
                onAddWindowRequested: windowManager.createWindow({
                    themeMode: appSettings.themeMode,
                    themeTint: appSettings.themeTint,
                    opacityPercent: appSettings.opacityPercent,
                    fontScale: appSettings.fontScale,
                    wheelZoomInverted: appSettings.wheelZoomInverted,
                    x: root.x,
                    y: root.y,
                    width: root.width,
                    height: root.height
                })
            }

            FilterBar {
                id: filterBar
                Layout.fillWidth: true
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ListView {
                    id: listView
                    anchors.fill: parent
                    visible: !filterBar.monthActive && !filterBar.yearActive && !filterBar.linksActive && !filterBar.yatasActive
                    clip: true
                    spacing: 0
                    model: taskModel
                    ScrollBar.vertical: ScrollBar { id: vbar; policy: ScrollBar.AsNeeded }

                    section.property: taskModel.groupByDay ? "dayLabel" : ""
                    section.criteria: ViewSection.FullString
                    section.delegate: sectionHeader

                    // Drag-to-reorder state, read by TaskDelegate instances.
                    // dragActive/dragFromIndex are only ever set by THIS
                    // window's own row when IT is the one being dragged
                    // (they mean "I am the drag's origin", regardless of
                    // where the pointer currently is).
                    property bool dragActive: false
                    property int dragFromIndex: -1
                    // dragHoverActive/dragHoverIndex mean "I am the drag's
                    // CURRENT target right now" — driven for whichever
                    // window that is (this one, mid-reorder, or a different
                    // one during a cross-window move) by the root Window's
                    // Connections on windowManager.taskDragHoverChanged
                    // above, not computed locally here.
                    property bool dragHoverActive: false
                    property int dragHoverIndex: -1
                    // Set (to another window's id, or this window's own —
                    // windowAt() no longer excludes the caller) while a
                    // task's drag handle is hovering any window, computed by
                    // TaskDelegate.qml via windowManager.windowAt() — ""
                    // means not currently over any window at all.
                    property string dragTargetWindowId: ""
                    // Last local Y (within listView's own viewport, not
                    // content coordinates) the drag hovered at, whether via
                    // this window's own DragHandler or the cross-window
                    // Connections handler — drives edgeScrollTimer below.
                    property real lastDragLocalY: -1

                    // Auto-scrolls the list while a drag hovers near its top
                    // or bottom edge — same "if possible" clamping a manual
                    // scrollbar drag already gets for free from Flickable,
                    // done manually here since this isn't a real scrollbar
                    // drag. Runs continuously (not re-armed per pointer move)
                    // so holding near an edge keeps scrolling smoothly.
                    Timer {
                        id: edgeScrollTimer
                        interval: 16
                        repeat: true
                        running: listView.dragHoverActive
                        onTriggered: {
                            if (listView.lastDragLocalY < 0)
                                return
                            var edge = 40
                            var step = 8
                            var maxContentY = Math.max(0, listView.contentHeight - listView.height)
                            if (listView.lastDragLocalY < edge && listView.contentY > 0) {
                                listView.contentY = Math.max(0, listView.contentY - step)
                            } else if (listView.lastDragLocalY > listView.height - edge
                                       && listView.contentY < maxContentY) {
                                listView.contentY = Math.min(maxContentY, listView.contentY + step)
                            }
                        }
                    }

                    // Briefly tints the row a "to task" navigation lands on,
                    // standing in for the hover highlight the real mouse
                    // cursor doesn't produce since it never actually moved
                    // there. Cleared by flashTimer below; matches
                    // TaskDelegate's 3-blink/1.2s flash animation duration.
                    property string flashTaskId: ""
                    Timer {
                        id: flashTimer
                        interval: 1200
                        onTriggered: listView.flashTaskId = ""
                    }

                    // The scrollbar is an overlay (doesn't reserve its own width),
                    // so rows must leave room for it themselves or their hover
                    // icons render underneath its thumb.
                    property real rowWidth: width - (vbar.visible ? vbar.width : 0)

                    delegate: TaskDelegate {
                        width: listView.rowWidth
                    }
                }

                // Gradient overlay painted on top of the list: fades the
                // bottom 10% from transparent into the window background,
                // hinting that more content lies below. Hidden when already
                // scrolled to the end (nothing more to show).
                // For the "none" theme contentBackground is "transparent", so
                // fall back to a dark/light system-like colour instead.
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: parent.height * 0.1
                    visible: listView.visible && listView.contentHeight > listView.height && !listView.atYEnd
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop {
                            position: 1.0
                            color: Theme.tintName === "none"
                                   ? (Theme.dark ? "#111827" : "#f9fafb")
                                   : Theme.contentBackground
                        }
                    }
                }

                // Month/Year calendar grids replace the task list entirely
                // while active — presentational components (Main.qml owns
                // the paging state) so a click in YearView can retarget
                // MonthView's year/month via a plain property assignment
                // rather than fighting a broken two-way binding.
                MonthView {
                    anchors.fill: parent
                    visible: filterBar.monthActive
                    year: root.calYear
                    month: root.calMonth
                    onPrevMonth: {
                        if (root.calMonth <= 1) {
                            root.calMonth = 12
                            root.calYear -= 1
                        } else {
                            root.calMonth -= 1
                        }
                    }
                    onNextMonth: {
                        if (root.calMonth >= 12) {
                            root.calMonth = 1
                            root.calYear += 1
                        } else {
                            root.calMonth += 1
                        }
                    }
                    onDayClicked: (y, m, d) => {
                        filterBar.setGrouping("day", true)
                        Qt.callLater(function() {
                            var idx = taskModel.indexForDate(y, m, d)
                            if (idx >= 0)
                                listView.positionViewAtIndex(idx, ListView.Beginning)
                        })
                    }
                }

                YearView {
                    anchors.fill: parent
                    visible: filterBar.yearActive
                    year: root.calYearPage
                    onPrevYear: root.calYearPage -= 1
                    onNextYear: root.calYearPage += 1
                    onMonthClicked: (y, m) => {
                        root.calYear = y
                        root.calMonth = m
                        filterBar.setGrouping("month", true)
                    }
                }

                // Replaces the task list entirely while active, same as
                // Month/Year. "To task" just turns Links off (revealing
                // whatever the underlying list state already was — no
                // forced Day mode, unlike MonthView's dayClicked, since
                // there's no date associated with a link click to justify
                // one) and scrolls to that task once it's back.
                LinksView {
                    anchors.fill: parent
                    visible: filterBar.linksActive
                    searchText: toolbar.searchText
                    onToTaskClicked: (taskId) => {
                        filterBar.setGrouping("links", false)
                        Qt.callLater(function() {
                            var idx = taskModel.indexForTask(taskId)
                            if (idx >= 0) {
                                listView.positionViewAtIndex(idx, ListView.Beginning)
                                listView.flashTaskId = taskId
                                flashTimer.restart()
                            }
                        })
                    }
                }

                // Replaces the task list entirely while active, same as
                // Links/Month/Year (r-3.md). Row click intentionally does
                // nothing beyond rename (double-click) and delete (trash
                // icon) — there's no "switch to that window" affordance,
                // by explicit design choice.
                YatasView {
                    anchors.fill: parent
                    visible: filterBar.yatasActive
                    searchText: toolbar.searchText
                }
            }
        }

        // After addTask() the model emits taskAdded. We wait one short timer
        // interval (~2 frames) before focusing the new delegate, so the
        // ToolButton's own click-completion handling can't steal focus back.
        // After addTask() the model emits taskAdded. The 100 ms delay lets any
        // click-event processing finish before we re-grab focus, so it sticks.
        // The suppressAutoSave flag in editField ensures the spurious
        // onEditingFinished that fires in the first tick doesn't save "Task name"
        // and hide the field before we get here.
        Timer {
            id: newTaskFocusTimer
            property string pendingId: ""
            interval: 100
            repeat: false
            onTriggered: {
                for (var i = 0; i < Math.min(listView.count, 3); i++) {
                    var item = listView.itemAtIndex(i)
                    if (item && item.taskId === pendingId) {
                        item.activateFocus()
                        break
                    }
                }
            }
        }

        Connections {
            target: taskModel
            function onTaskAdded(taskId) {
                newTaskFocusTimer.pendingId = taskId
                newTaskFocusTimer.restart()
            }
        }

        Component {
            id: sectionHeader
            Rectangle {
                width: listView.rowWidth
                height: headerText.implicitHeight + 10
                color: "transparent"
                Text {
                    id: headerText
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: section
                    color: Theme.mutedTextColor
                    font.bold: true
                    // Day name reads as a heading over the task list below it.
                    font.pixelSize: Theme.taskFontPixelSize * 1.5
                    font.family: Theme.fontFamily
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            anchors.topMargin: tagLabelBg.height / 2
            color: "transparent"
            radius: 6
            // Drop-target affordance for cross-window task drag (see
            // TaskDelegate.qml's drag handle / windowManager.windowAt()) —
            // filterGlowColor is the default cyan for "none", or the
            // selected tint's own accent color, same rule as every other
            // on/active glow in this app (FilterBar's toggle buttons, and
            // now TaskDelegate's drop placeholder too).
            border.color: root.dragHoverActive ? Theme.filterGlowColor : Theme.borderColor
            border.width: root.dragHoverActive ? 2 : 1
        }

        // This window's tag, drawn "cutting into" the top border line like
        // a fieldset legend (r-3.md's ASCII mockup: "+--[ TAG NAME ]---+").
        // Double-click to rename in place (also possible via YatasView's
        // row, unchanged) — editingTag swaps this label out for
        // tagEditField below, matching the read/edit-field-swap convention
        // used throughout this app (TaskDelegate, YatasRow).
        //
        // y is 0, not -height/2 — the two Rectangles above reserve exactly
        // height/2 of real space for it via their own topMargin, so its
        // vertical center still lands exactly on their (now inset) top
        // edge, without any part of the label needing a negative,
        // off-surface y (see the wash Rectangle's comment above for why
        // that doesn't render on a live window).
        Rectangle {
            id: tagLabelBg
            x: 14
            y: 0
            visible: !root.editingTag
            radius: 3
            color: Theme.tintName === "none"
                   ? (Theme.dark ? "#111827" : "#f9fafb")
                   : Theme.contentBackground
            // Capped so a long custom tag (or a large font zoom) can never
            // push this label past the window's own right edge, where it'd
            // just get clipped by the window itself — elide instead.
            width: Math.min(tagLabelText.implicitWidth, root.width - x - 14) + 12
            height: tagLabelText.implicitHeight + 4

            Text {
                id: tagLabelText
                anchors.centerIn: parent
                width: parent.width - 12
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                text: root.windowTag
                color: Theme.textColor
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.8)
            }

            TapHandler {
                onDoubleTapped: root.editingTag = true
            }
        }

        // Edit-mode swap-in for the tag label above, styled like the
        // toolbar search field (same rounded Theme.fieldColor background)
        // per explicit request. Spans from the label's own start x to half
        // the window's width, rather than matching tagLabelBg's own
        // (much narrower, elide-capped) width.
        TextField {
            id: tagEditField
            x: tagLabelBg.x
            y: 0
            width: root.width / 2 - x
            visible: root.editingTag
            text: root.windowTag
            color: Theme.textColor
            font.bold: true
            font.family: Theme.fontFamily
            font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.8)
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }

            onVisibleChanged: if (visible) { selectAll(); forceActiveFocus() }

            function commit() {
                root.editingTag = false
                var trimmed = text.trim()
                if (trimmed.length > 0 && trimmed !== root.windowTag)
                    windowManager.renameWindow(windowId, trimmed)
            }
            onEditingFinished: commit()
            Keys.onReturnPressed: commit()
            Keys.onEscapePressed: root.editingTag = false
        }
    }
}

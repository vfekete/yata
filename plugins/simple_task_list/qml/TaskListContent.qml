import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

// r-9.md step 4: this plugin's whole content area — everything that used
// to live directly in yata-src/qml/Main.qml except the host's own chrome
// (border, tag label/rename, lock, close, blur/glass effect), which stays
// there. Loaded into Main.qml's content Loader; Main.qml itself applies
// the same margins/topMargin this used to have as "contentColumn" (it
// needs tagLabelBg's height, a host-owned id this file can't see).
//
// context properties this relies on (all set by main.py, unchanged from
// before this file existed): taskModel, appSettings (this plugin's own
// TaskListSettings — same name QML always used), Theme, iconProvider,
// windowManager, windowId.
Item {
    id: contentRoot
    anchors.fill: parent

    // Read back by Main.qml (host) for its own minimumWidth — a plain
    // Loader.item property read, not a context property, since it's
    // specific to this one plugin's own Toolbar layout.
    readonly property alias actionButtonsWidth: toolbar.actionButtonsWidth
    // Read back by Main.qml (host) for auto-locked's hover-to-unlock
    // check — see contentHoverHandler below for why it's nested here
    // rather than a sibling overlay.
    readonly property alias contentHovered: contentHoverHandler.hovered
    // Read back by Main.qml (host) for the content wrapper's own opacity —
    // appSettings.opacityPercent is plugin-owned, so Theme.windowOpacity
    // (which already computes this) is forwarded rather than duplicated.
    readonly property real windowOpacity: Theme.windowOpacity

    // MonthView/YearView's currently-displayed page. Not persisted — each
    // resets to the current month/year at app start; navigating away and
    // back within a session keeps whatever was last paged to, since these
    // are plain properties on a component that's never destroyed.
    property int calYear: new Date().getFullYear()
    property int calMonth: new Date().getMonth() + 1
    property int calYearPage: new Date().getFullYear()

    // r-6.md: true precisely when NoteEditorView should be the on-screen
    // content — not merely whenever a task's note is "pending" (i.e. it
    // stays covered-but-mounted, not this), which is why Links/Yatas are
    // excluded here: clicking either while the editor is open shows their
    // own view on top instead (see listView.visible/NoteEditorView.visible
    // below, and FilterBar's subToolbarDisabled), and clicking them off
    // again brings this back automatically since noteEditorTaskId itself
    // is never cleared by that round trip.
    readonly property bool noteEditorVisible: listView.noteEditorTaskId !== "" && !filterBar.linksActive && !filterBar.yatasActive

    // Right-click anywhere on the content for theme + quit. No lock guard
    // needed here (unlike before r-9.md) — Main.qml's own input-blocking
    // overlay sits above this whole Loader whenever the window is locked,
    // so this MouseArea simply never receives events in that case.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: contextMenu.popup()
    }

    ThemeMenu {
        id: contextMenu
        showQuit: true
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

    // True while another window's task drag is hovering over THIS window —
    // computed independently of Main.qml's own copy (used there for its
    // border highlight); this one just drives listView's own reflow
    // placeholder/edge auto-scroll, since only this content's own layout
    // knows about listView's coordinates at all.
    Connections {
        target: windowManager
        function onTaskDragHoverChanged(targetWindowId, globalX, globalY) {
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
            //
            // contentRoot.Window.window, NOT the bare "Window.window" this
            // line originally had (before r-9.md step 4, this file's whole
            // content lived directly inside Main.qml, i.e. the Window's own
            // QML document, where the bare form happened to resolve) — from
            // inside a Connections function body in a separately-loaded
            // file, the bare attached-property lookup silently resolves to
            // null instead of walking up to the enclosing Window, throwing
            // here and aborting the handler before dragHoverActive/
            // dragHoverIndex ever got set. Confirmed live: cross-window drag
            // stopped updating the target window's own list placeholder the
            // moment this file stopped being inlined in Main.qml. Same
            // qualified-id pattern TaskDelegate.qml's own onCentroidChanged
            // already uses for exactly this reason (root.Window.window).
            var win = contentRoot.Window.window
            var posInWindow = Qt.point(globalX - win.x, globalY - win.y)
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

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        spacing: 2

        // r-8.md "The glass lock": tracks whether the mouse is anywhere
        // over the content area, for auto-locked's hover-to-unlock
        // behavior — forwarded to Main.qml (host) via contentHovered
        // above. Nested here as a child of contentColumn itself — NOT a
        // separate overlay Item stacked on top of it — precisely because a
        // HoverHandler on a sibling placed above contentColumn was
        // confirmed to exclusively claim hover and block it from ever
        // reaching TaskDelegate rows/LinksView/YatasView's own hover-driven
        // highlighting underneath. A HoverHandler nested as a PARENT of
        // items that have their own HoverHandlers coexists with all of
        // them correctly — confirmed live.
        HoverHandler {
            id: contentHoverHandler
        }

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
                x: Window.window.x,
                y: Window.window.y,
                width: Window.window.width,
                height: Window.window.height
            })
        }

        FilterBar {
            id: filterBar
            Layout.fillWidth: true
            subToolbarDisabled: contentRoot.noteEditorVisible
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ListView {
                id: listView
                anchors.fill: parent
                visible: !filterBar.monthActive && !filterBar.yearActive && !filterBar.linksActive && !filterBar.yatasActive && listView.noteEditorTaskId === ""
                clip: true
                spacing: 0
                model: taskModel
                ScrollBar.vertical: ScrollBar { id: vbar; policy: ScrollBar.AsNeeded }

                section.property: taskModel.groupByDay ? "dayLabel" : ""
                section.criteria: ViewSection.FullString
                section.delegate: sectionHeader

                // Drag-to-reorder state, read by TaskDelegate instances.
                // dragActive/dragFromIndex are only ever set by THIS
                // window's own row when IT is the one being dragged (they
                // mean "I am the drag's origin", regardless of where the
                // pointer currently is).
                property bool dragActive: false
                property int dragFromIndex: -1
                // dragHoverActive/dragHoverIndex mean "I am the drag's
                // CURRENT target right now" — driven for whichever window
                // that is (this one, mid-reorder, or a different one
                // during a cross-window move) by the Connections on
                // windowManager.taskDragHoverChanged above, not computed
                // locally here.
                property bool dragHoverActive: false
                property int dragHoverIndex: -1
                // Set (to another window's id, or this window's own —
                // windowAt() no longer excludes the caller) while a task's
                // drag handle is hovering any window, computed by
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

                // r-6.md: the task whose note is currently being viewed/
                // edited in NoteEditorView below, "" when none — set by
                // TaskDelegate's note icon (same convention as
                // dragActive/flashTaskId above: a custom property added
                // directly onto listView, read/written via
                // root.ListView.view.xxx from the delegate). Stays set
                // while Links/Yatas cover it (see noteEditorVisible above),
                // so returning from them restores the editor instead of
                // the plain list.
                property string noteEditorTaskId: ""

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
            // while active — presentational components (this file owns
            // the paging state) so a click in YearView can retarget
            // MonthView's year/month via a plain property assignment
            // rather than fighting a broken two-way binding.
            MonthView {
                anchors.fill: parent
                visible: filterBar.monthActive
                year: contentRoot.calYear
                month: contentRoot.calMonth
                onPrevMonth: {
                    if (contentRoot.calMonth <= 1) {
                        contentRoot.calMonth = 12
                        contentRoot.calYear -= 1
                    } else {
                        contentRoot.calMonth -= 1
                    }
                }
                onNextMonth: {
                    if (contentRoot.calMonth >= 12) {
                        contentRoot.calMonth = 1
                        contentRoot.calYear += 1
                    } else {
                        contentRoot.calMonth += 1
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
                year: contentRoot.calYearPage
                onPrevYear: contentRoot.calYearPage -= 1
                onNextYear: contentRoot.calYearPage += 1
                onMonthClicked: (y, m) => {
                    contentRoot.calYear = y
                    contentRoot.calMonth = m
                    filterBar.setGrouping("month", true)
                }
            }

            // Replaces the task list entirely while active, same as
            // Month/Year. "To task" just turns Links off (revealing
            // whatever the underlying list state already was — no forced
            // Day mode, unlike MonthView's dayClicked, since there's no
            // date associated with a link click to justify one) and
            // scrolls to that task once it's back.
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
            // icon) — there's no "switch to that window" affordance, by
            // explicit design choice.
            YatasView {
                anchors.fill: parent
                visible: filterBar.yatasActive
                showActive: filterBar.yatasShowActive
                showDeleted: filterBar.yatasShowDeleted
                sortMode: filterBar.yatasSortMode
                searchText: toolbar.searchText
            }

            // r-6.md: replaces the task list while a note is being
            // viewed/edited. Stays mounted (visible: false, not
            // destroyed) while Links/Yatas cover it, so in-progress edits
            // survive that round trip — see contentRoot.noteEditorVisible
            // above and listView.noteEditorTaskId's own comment.
            NoteEditorView {
                anchors.fill: parent
                visible: contentRoot.noteEditorVisible
                taskId: listView.noteEditorTaskId
                onClosed: listView.noteEditorTaskId = ""
            }
        }
    }

    // After addTask() the model emits taskAdded. We wait one short timer
    // interval (~2 frames) before focusing the new delegate, so the
    // ToolButton's own click-completion handling can't steal focus back.
    // The 100 ms delay lets any click-event processing finish before we
    // re-grab focus, so it sticks. The suppressAutoSave flag in editField
    // ensures the spurious onEditingFinished that fires in the first tick
    // doesn't save "Task name" and hide the field before we get here.
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
}

import QtQuick
import QtQuick.Controls
import QtQuick.Effects
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

    // r-6.md: true precisely when NoteEditorView should be the on-screen
    // content — not merely whenever a task's note is "pending" (i.e. it
    // stays covered-but-mounted, not this), which is why Links/Yatas are
    // excluded here: clicking either while the editor is open shows their
    // own view on top instead (see listView.visible/NoteEditorView.visible
    // below, and FilterBar's subToolbarDisabled), and clicking them off
    // again brings this back automatically since noteEditorTaskId itself
    // is never cleared by that round trip.
    readonly property bool noteEditorVisible: listView.noteEditorTaskId !== "" && !filterBar.linksActive && !filterBar.yatasActive

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

    // r-8.md "The glass lock": three-state persisted mode, cycled by
    // clicking the lock icon (see lockIcon near the bottom of this file).
    // "unlocked": normal, no blur, no restrictions. "locked": content
    // permanently blurred and inert (toolbar/menu included). "auto-locked":
    // same as locked, except automatically/temporarily unlocked while the
    // mouse is inside the content area (or another window drops a task into
    // it, see dragHoverActive above) or while a task's description is being
    // actively typed (see editingTaskDescription below) — reverting once the
    // mouse leaves (or, for the editing exception, once editing finishes and
    // the mouse already isn't inside).
    //
    // contentHovered is read from contentHoverHandler, declared further
    // down alongside the content overlay it belongs to.
    //
    // editingTaskDescription reads Qt's own live Window.activeFocusItem
    // (via its objectName, set on TaskDelegate's editField) rather than a
    // custom per-delegate signal relayed up through listView — the latter
    // would go stale if a delegate is ever destroyed (e.g. a model reset
    // from RELOAD) without first firing a proper focus-lost signal,
    // permanently stranding the window unlocked. activeFocusItem can never
    // go stale that way: it's always Qt's current, authoritative answer.
    readonly property bool editingTaskDescription: root.activeFocusItem !== null
        && root.activeFocusItem.objectName === "taskDescriptionField"

    readonly property bool contentLocked: {
        if (appSettings.lockState === "unlocked") return false
        if (appSettings.lockState === "locked") return true
        if (root.editingTaskDescription) return false
        return !contentHoverHandler.hovered && !root.dragHoverActive
    }

    // Drives the blur amount smoothly (see contentColumn's MultiEffect
    // below) rather than snapping instantly — 0 (fully clear) to 1 (fully
    // blurred, i.e. MultiEffect's blurMax radius). 150ms per explicit
    // request (shortened from the original 1-second spec in r-8.md).
    property real blurAmount: root.contentLocked ? 1.0 : 0.0
    Behavior on blurAmount {
        NumberAnimation { duration: 150 }
    }

    function nextLockState() {
        if (appSettings.lockState === "unlocked") return "auto-locked"
        if (appSettings.lockState === "auto-locked") return "locked"
        return "unlocked"
    }

    // Right-click anywhere on the background for theme + quit. Placed first so
    // real controls (declared later / painted on top) get first refusal at
    // clicks. Also part of "the menu items ... too" that a locked window must
    // not react to (r-8.md).
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        enabled: !root.contentLocked
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

        // r-8.md "The glass lock", follow-up: the background wash AND the
        // toolbar/list are blurred together as ONE frosted pane (originally
        // only the toolbar/list column had the effect, leaving the plain
        // background rectangle behind them crisp — "I expected everything
        // will be blurred (together with background)"). Wrapping both in a
        // single layered Item means one MultiEffect pass covers the whole
        // panel, not two effects that could each render/settle slightly
        // differently.
        //
        // This is a live GPU-rendered layer, not a one-off blurred snapshot
        // — it re-renders every frame from whatever contentColumn/the wash
        // actually look like right now, so it can never go stale or briefly
        // reveal crisp content while the window is being moved/resized.
        Item {
            id: frostedContent
            anchors.fill: parent

            // blur: 0 (root.blurAmount, unlocked) renders identically to no
            // effect at all, so layer.enabled can stay unconditionally true
            // with no always-unlocked-window visual cost. blurMax: 48 is a
            // heavy/"frosted" radius, picked after the original blurMax: 5
            // was confirmed live to leave task text still fully readable —
            // this one was confirmed live to genuinely obscure it instead.
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blur: root.blurAmount
                blurMax: 48
                autoPaddingEnabled: true
            }

            // The window itself stays fully transparent (per spec); this wash
            // is what actually paints each tint's background, translucent so
            // the window still reads as "transparent" rather than opaque.
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
                id: contentColumn
                anchors.fill: parent
                anchors.margins: 15
                // Extra headroom so the toolbar doesn't collide with the tag
                // label sitting on the border line above it (see tagLabelBg
                // near the bottom of this file) — scales with the label's own
                // (font-zoom-dependent) height rather than a fixed guess.
                anchors.topMargin: 15 + tagLabelBg.height / 2 + 4
                spacing: 2

                // r-8.md "The glass lock": tracks whether the mouse is
                // anywhere over the content area, for auto-locked's
                // hover-to-unlock behavior (see root.contentLocked above).
                // Nested here as a child of contentColumn itself — NOT a
                // separate overlay Item stacked on top of it — precisely
                // because a HoverHandler on a sibling placed above
                // contentColumn was confirmed to exclusively claim hover and
                // block it from ever reaching TaskDelegate rows/LinksView/
                // YatasView's own hover-driven highlighting underneath (see
                // contentOverlay's own comment, below, for the full
                // reasoning and the minimal reproduction that confirmed it).
                // A HoverHandler nested as a PARENT of items that have their
                // own HoverHandlers coexists with all of them correctly —
                // confirmed live — which is exactly this relationship
                // (contentColumn is the parent of the toolbar/list/etc, not
                // a same-level competing sibling of them).
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
                    x: root.x,
                    y: root.y,
                    width: root.width,
                    height: root.height
                })
            }

            FilterBar {
                id: filterBar
                Layout.fillWidth: true
                subToolbarDisabled: root.noteEditorVisible
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

                    // r-6.md: the task whose note is currently being viewed/
                    // edited in NoteEditorView below, "" when none — set by
                    // TaskDelegate's note icon (same convention as
                    // dragActive/flashTaskId above: a custom property added
                    // directly onto listView, read/written via
                    // root.ListView.view.xxx from the delegate). Stays set
                    // while Links/Yatas cover it (see noteEditorVisible on
                    // the root Window below), so returning from them
                    // restores the editor instead of the plain list.
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
                    showActive: filterBar.yatasShowActive
                    showDeleted: filterBar.yatasShowDeleted
                    sortMode: filterBar.yatasSortMode
                    searchText: toolbar.searchText
                }

                // r-6.md: replaces the task list while a note is being
                // viewed/edited. Stays mounted (visible: false, not
                // destroyed) while Links/Yatas cover it, so in-progress
                // edits survive that round trip — see root.noteEditorVisible
                // above and listView.noteEditorTaskId's own comment.
                NoteEditorView {
                    anchors.fill: parent
                    visible: root.noteEditorVisible
                    taskId: listView.noteEditorTaskId
                    onClosed: listView.noteEditorTaskId = ""
                }
            }
        } // ColumnLayout (contentColumn)
        } // Item (frostedContent)

        // Frosted-glass tint: a flat, NOT-blurred scrim sitting on top of
        // frostedContent's own blurred layer (drawn after it, so it paints
        // above) — a plain translucent color doesn't change when blurred, so
        // it has to live outside the layered item to have any visible effect
        // of its own. This is what gives the "milky glass" look ("look and
        // feel of glass / frosted overlay") rather than just a blurred photo
        // of the task list — confirmed live: blur alone still let shapes read
        // as clearly "the task list, blurred"; the added haze reads as glass.
        // Fades in/out with the same blurAmount Behavior as the blur itself,
        // so both always move together.
        //
        // Tinted with Theme.effectiveGlowColor per explicit request ("let the
        // milk tint be the tint color of the window") rather than a fixed
        // white — the same "this window's effective accent color" property
        // already used for the border/tag-text glow and markdown link color
        // elsewhere in this file, so it stays in sync with whatever's
        // actually set: a CRT/terminal tint's own phosphor color ("in case
        // of terminal colors, major color for the terminal" — green/
        // goldenrod/white/black all resolve through this same property),
        // this window's custom border color if one is set (r-4.md), or the
        // theme's own default accent otherwise.
        Rectangle {
            anchors.fill: frostedContent
            radius: 6
            color: Theme.effectiveGlowColor
            opacity: root.blurAmount * 0.35
        }

        // r-8.md "The glass lock": sits on top of contentColumn (declared
        // after frostedContent, so it paints/hit-tests above it — the
        // frosted tint scrim above is purely visual and never intercepts
        // input, hence no effect on hit-testing order here). contentBlocker
        // is a MouseArea that, while enabled, grabs and swallows every mouse
        // press/click/wheel event over this area before contentColumn's own
        // toolbar/list ever sees it — exactly "does not react on mouse
        // movement or mouse clicks" for "menu items and toolbar too"
        // (r-8.md). While disabled (unlocked, or auto-locked-and-currently-
        // hovered), it's excluded from hit-testing entirely and every event
        // passes through to the real controls beneath, untouched.
        //
        // hoverEnabled: true is deliberate, not an oversight: while enabled
        // (plain "locked"), it must ALSO claim hover away from TaskDelegate
        // rows/LinksView/YatasView underneath, or their own hover highlight
        // and hover-revealed action icons would keep visibly reacting to the
        // mouse even though the window is supposed to be fully locked/inert
        // (user feedback: hover worked again after the fix below, "but it
        // also works when the window is locked... events should not go to
        // underlying items"). Exploits the exact mechanism the next
        // paragraph describes as a bug when it was accidental: an enabled
        // hover-aware item above another in the same z-stack exclusively
        // claims hover from what's underneath — undesirable when *nothing*
        // should claim it (unlocked), wanted here specifically because
        // contentBlocker's own `enabled` is already correctly gated to
        // exactly the states (locked; auto-locked-and-not-hovering) where
        // that blocking is supposed to happen.
        //
        // The hover *detection* (for auto-locked's own "has the mouse
        // arrived" check) used to live here too, as a second HoverHandler
        // alongside contentBlocker — but an always-on HoverHandler in this
        // position broke every hover-driven control underneath regardless of
        // lock state, including while fully unlocked — confirmed via a
        // minimal reproduction: an Item with an enabled HoverHandler placed
        // ABOVE another item in the same z-stack (siblings, even with no
        // MouseArea/grab at all) exclusively claims hover for itself and
        // blocks it from ever reaching anything underneath, contrary to
        // HoverHandler's own "non-exclusive, siblings can all respond"
        // documentation — that non-exclusivity turned out to only cover
        // multiple handlers on the SAME item, not separate items competing
        // in a z-stack. A second reproduction confirmed the fix: nesting a
        // HoverHandler as a PARENT of items that have their own HoverHandlers
        // (ancestor/descendant, not sibling-on-top) lets both the parent's
        // and every descendant's hover state update independently and
        // correctly. So the auto-locked
        // hover detection (contentHoverHandler) now lives nested inside
        // contentColumn itself instead — see there.
        //
        // Deliberately still scoped to contentColumn, NOT the wider
        // frostedContent (background + margins) that now gets blurred as one
        // unit — the visual extent of the blur and the functional "mouse is
        // inside the interactive area" boundary are two different concerns.
        // Widening this to frostedContent was tried and reverted: frostedContent
        // spans the *entire* window (anchors.fill: parent, no margin), so
        // every point in the window — including over the tag label, the lock
        // icon's corner, or the plain border gutter — would count as
        // "hovering content", making auto-locked impossible to ever leave
        // short of moving the mouse outside the window's edges entirely
        // (confirmed live: the "moves outside content, should re-lock" test
        // then failed since there was no more "outside content but inside
        // the window" position left to move to).
        //
        // x/y/width/height read directly from contentColumn instead of
        // anchors.fill: contentColumn — QML anchoring only works between a
        // parent/child or direct siblings, and contentColumn is now nested
        // one level deeper inside frostedContent, so a direct anchor errors
        // at runtime ("Cannot anchor to an item that isn't a parent or
        // sibling", confirmed live). contentColumn.x/y (relative to
        // frostedContent) can be used as-is (rather than mapped into
        // contentOverlay's own parent's coordinates) because frostedContent
        // itself sits at (0, 0) with no margin relative to that same parent
        // (anchors.fill: parent, no offset) — so the two coordinate spaces
        // coincide exactly. (mapToItem() was tried first and reverted: its
        // return value isn't tracked as a live binding dependency the way a
        // plain property read is, so x/y silently froze at whatever
        // contentColumn's position happened to be at the very first
        // evaluation — before the ColumnLayout had actually positioned it —
        // and never updated again; confirmed live via the resulting
        // MouseArea sitting at (0,0) instead of contentColumn's real
        // position.)
        Item {
            id: contentOverlay
            x: contentColumn.x
            y: contentColumn.y
            width: contentColumn.width
            height: contentColumn.height

            MouseArea {
                id: contentBlocker
                anchors.fill: parent
                enabled: root.contentLocked
                // Only for plain "locked", NOT "auto-locked" — see the
                // comment above for why claiming hover here is wanted at
                // all, but doing it for auto-locked's transient "enabled
                // because not yet hovering" phase creates a deadlock: that
                // phase's own enabled-ness depends on contentHoverHandler
                // (nested inside contentColumn, i.e. underneath this sibling
                // in the z-stack) detecting the mouse's arrival, and once
                // this claims hover for itself first, contentHoverHandler
                // never gets a turn to notice anything ever arrived —
                // confirmed live: auto-locked got stuck locked forever,
                // hovering content no longer unlocked it at all. Plain
                // "locked" has no such cycle (its enabled-ness doesn't
                // depend on hover at all, only on appSettings.lockState), so
                // it's safe to claim hover there unconditionally.
                hoverEnabled: appSettings.lockState === "locked"
                acceptedButtons: Qt.AllButtons
                onWheel: (event) => { event.accepted = true }
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
            id: windowBorder
            anchors.fill: parent
            anchors.topMargin: tagLabelBg.height / 2
            color: "transparent"
            radius: 6
            // Drop-target affordance for cross-window task drag (see
            // TaskDelegate.qml's drag handle / windowManager.windowAt()) —
            // filterGlowColor is the default cyan for "none", or the
            // selected tint's own accent color, same rule as every other
            // on/active glow in this app (FilterBar's toggle buttons, and
            // now TaskDelegate's drop placeholder too). Takes priority over
            // the user's own custom border color below — it's a separate,
            // transient "you're dropping here" signal, not this window's
            // persistent identity color.
            //
            // appSettings.borderColor !== "" is r-4.md's per-window custom
            // color (YatasView's paint-bucket button) — "" (the default)
            // means no override, follow the theme exactly as before.
            border.color: root.dragHoverActive ? Theme.filterGlowColor
                          : (appSettings.borderColor !== "" ? appSettings.borderColor : Theme.borderColor)
            // A 1px stroke doesn't give MultiEffect's blur enough alpha
            // "mass" to build a visible halo from — confirmed live: at
            // width 1 the glow was barely a tint. Width 4 is what reads as
            // an actual neon-tube glow (isolated side-by-side comparison
            // against TaskDelegate's own deleteBtn glow, the vividness
            // target); blurMax had negligible effect by comparison, so
            // width is the real lever here. This is now the border's
            // permanent width, not just a custom-color-only look — the
            // glow itself is on by default (see layer.enabled below), so
            // it needs this width whether or not a custom color is set.
            // Drag-hover keeps its own distinct 2px highlight width.
            border.width: root.dragHoverActive ? 2 : 4

            // shadowScale: 1.0 (NOT the usual >1.0 outward-bleed used
            // everywhere else in this app for icon glows/tag text) — a
            // nonzero scale factor makes MultiEffect draw an entirely
            // separate, differently-sized COPY of the whole border shape;
            // for a small icon that copy is close enough to read as a tight
            // halo, but for this Rectangle (anchors.fill: parent of the
            // whole window) even a 10% scale is tens of pixels of absolute
            // displacement — visibly a second, disconnected rectangle
            // floating inside, not a glow hugging the real border (caught
            // live: exactly this "detached rounded box" artifact). Also,
            // any *outward* scale specifically has nowhere to bleed at all
            // — a real window surface has zero pixels past its own true
            // boundary, on any platform (confirmed: even a 40px margin
            // barely made outward bleed visible, an unacceptable layout
            // change). shadowScale: 1.0 draws the shadow at the exact same
            // geometry as the source, so shadowBlur alone softens it into a
            // halo that hugs the real line and bleeds inward (where there's
            // always room) with zero displacement and zero margin needed.
            // On by default now, not just when a custom color (r-4.md) is
            // set — shadowColor reads border.color itself (already the
            // full drag-hover > custom-color > theme-default fallback
            // chain above), so the glow always matches whatever's
            // actually drawn, with no separate default-vs-custom branch
            // to keep in sync.
            layer.enabled: !root.dragHoverActive
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: windowBorder.border.color
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.0
            }
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
                // Same custom-color-with-glow treatment as the border above
                // (r-4.md) — "" (default) means no override, unchanged from
                // before.
                color: appSettings.borderColor !== "" ? appSettings.borderColor : Theme.textColor
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.8)

                // On by default now, not just when a custom color (r-4.md)
                // is set — same reasoning as windowBorder's glow above.
                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: tagLabelText.color
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
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

        // r-8.md "The glass lock": mirrors tagLabelBg's placement — same
        // margin (14) from the right edge that the tag label has from the
        // left, same y (0, straddling the border line), same height ("icons
        // has same height as the window title"). Always clickable/crisp
        // regardless of lock state: it lives outside contentColumn/
        // contentOverlay entirely, so it's never blurred or blocked — the
        // one control that must always work, or a locked window could never
        // be unlocked again.
        //
        // Sits on the same solid background box as the tag label (same
        // color/radius as tagLabelBg) rather than directly on the border
        // line — without it, windowBorder's stroke ran straight through the
        // icon and made it hard to see, especially when the border color was
        // close to the icon's own color (user feedback: "the border passes
        // through it and it is not very well visible").
        Rectangle {
            id: lockIconBg
            y: 0
            height: tagLabelBg.height
            radius: 3
            color: Theme.tintName === "none"
                   ? (Theme.dark ? "#111827" : "#f9fafb")
                   : Theme.contentBackground
            width: lockIcon.width + 12
            x: root.width - 14 - width

            Image {
                id: lockIcon
                readonly property string iconName: appSettings.lockState === "locked" ? "lock_locked"
                    : appSettings.lockState === "auto-locked" ? "lock_autolocked" : "lock_unlocked"
                readonly property color iconColor: appSettings.borderColor !== "" ? appSettings.borderColor : Theme.borderColor

                anchors.centerIn: parent
                height: parent.height - 4
                width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                fillMode: Image.PreserveAspectFit
                smooth: true
                source: iconProvider.coloredSvgUri(iconName, iconColor.toString())
            }

            MouseArea {
                anchors.fill: parent
                anchors.margins: -4
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: appSettings.lockState = root.nextLockState()
                ToolTip.visible: containsMouse
                ToolTip.text: lockIcon.iconName === "lock_locked" ? qsTr("Locked — click to unlock")
                    : lockIcon.iconName === "lock_autolocked" ? qsTr("Auto-locked — click to lock")
                    : qsTr("Unlocked — click to auto-lock")
            }
        }
    }
}

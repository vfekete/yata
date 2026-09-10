import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Window

// r-9.md step 4: this is now a thin host shell, not the whole app. It owns
// exactly what the master application controls per the plugin architecture:
// border color, the lock state machine + glass/blur effect (color
// included), the close button, and the window title (tag display +
// rename). Everything else — toolbar, filters, the task list, calendar
// views, links/notes, the whole theme system, multi-window management UI —
// lives in the plugin's own content, loaded into contentLoader below (see
// plugins/simple_task_list/qml/TaskListContent.qml).
//
// Host chrome deliberately does NOT use the plugin's Theme (color/font)
// system — a different plugin could look completely different, and this
// chrome must look the same regardless. Its colors/font below are today's
// dark-mode/"none"-tint values, frozen as fixed constants (explicit user
// decision) rather than reactive to whatever theme the plugin's content
// picks. One consequence: this chrome no longer resizes with the plugin's
// own Ctrl+scroll/Ctrl+-+ zoom (that's plugin-owned fontScale now) — it
// stays fixed-size.
Window {
    id: root
    visible: true
    color: "transparent"
    // Opacity is applied to the content wrapper below, NOT to the Window
    // itself, so popup menus (rendered in the Window's Overlay layer above
    // the content) always appear at full opacity regardless of the user's
    // slider setting — preventing an irreversible "can't see the menu"
    // situation at very low opacity values. windowOpacity is plugin-owned
    // now (appSettings.opacityPercent lives in the plugin's own settings),
    // so it's read back from the loaded content the same way
    // actionButtonsWidth/contentHovered are.
    // Qt.WindowStaysOnBottomHint is intentionally not used: on GNOME/Mutter
    // (the primary target platform) it places the window below the desktop
    // background layer itself, making it invisible rather than merely
    // "beneath other windows, above icons". See README.md.
    flags: Qt.FramelessWindowHint

    // Fixed host-chrome palette (see this file's own header comment for
    // why these are hardcoded rather than Theme.* reads) — today's exact
    // dark-mode/"none"-tint values, so nothing visibly changes for anyone
    // currently on the default theme.
    function chromeBoxColor(hovered) {
        return hovered ? "#1f2937" : "#111827"
    }
    readonly property color chromeTextColor: "#f3f4f6"
    readonly property color chromeMutedTextColor: "#9ca3af"
    readonly property color chromeAccentColor: hostSettings.borderColor !== "" ? hostSettings.borderColor : "#64748b"
    readonly property color chromeDragHoverColor: "#00FFFF"
    readonly property string chromeFontFamily: "Noto Sans"
    readonly property int chromeFontPixelSize: 14

    x: hostSettings.x
    y: hostSettings.y
    width: hostSettings.width
    height: hostSettings.height
    // Twice the combined width of the plugin's own toolbar buttons — below
    // this, its filter groups have nowhere reasonable left to wrap into.
    // Read back from the Loader's own item (a plugin-specific property,
    // not a context property) since only the plugin's Toolbar knows its
    // own width; falls back to a sane default before the Loader's item
    // exists.
    minimumWidth: (contentLoader.item ? contentLoader.item.actionButtonsWidth : 300) * 2

    onXChanged: hostSettings.x = x
    onYChanged: hostSettings.y = y
    onWidthChanged: hostSettings.width = width
    onHeightChanged: hostSettings.height = height

    // Grows width up to minimumWidth when needed (e.g. a persisted width
    // from before a toolbar button existed, now narrower than the real
    // minimum) — done as a plain imperative assignment, NOT folded into
    // width's own binding above, because that shape is a genuine QML
    // binding loop (width's binding would depend on hostSettings.width,
    // which onWidthChanged right above writes to on every width change).
    // An imperative assignment here breaks/replaces the binding the moment
    // it actually needs to fire, exactly like a user's own resize already
    // does — width keeps persisting correctly afterward via onWidthChanged
    // either way.
    function ensureMinimumWidth() {
        if (width < minimumWidth)
            width = minimumWidth
    }
    Component.onCompleted: ensureMinimumWidth()
    onMinimumWidthChanged: ensureMinimumWidth()

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
    // drives the border highlight below. The plugin's own content
    // independently listens to the same windowManager.taskDragHoverChanged
    // broadcast for its own list-reflow purposes (see TaskListContent.qml)
    // — two independent listeners on one shared signal, not a property
    // forwarded between host and plugin.
    property bool dragHoverActive: false
    Connections {
        target: windowManager
        function onTaskDragHoverChanged(targetWindowId, globalX, globalY) {
            root.dragHoverActive = targetWindowId === windowId
        }
    }

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
    // contentLoader.item.contentHovered is the plugin's own forwarded
    // hover-detection (see TaskListContent.qml's contentHoverHandler) —
    // guarded against the Loader's item not existing yet.
    //
    // editingTaskDescription reads Qt's own live Window.activeFocusItem
    // (via its objectName, set on TaskDelegate's editField) rather than a
    // custom per-delegate signal relayed up through listView — the latter
    // would go stale if a delegate is ever destroyed (e.g. a model reset
    // from RELOAD) without first firing a proper focus-lost signal,
    // permanently stranding the window unlocked. activeFocusItem can never
    // go stale that way: it's always Qt's current, authoritative answer.
    // This keeps working unchanged across the Loader boundary — it's a
    // Window-level property, not scoped to any one QML file.
    readonly property bool editingTaskDescription: root.activeFocusItem !== null
        && root.activeFocusItem.objectName === "taskDescriptionField"

    // Window management (the "Y" chrome icon below, toggling yatasView in
    // place of the plugin's own content) is host-owned, unlike everything
    // the Loader shows — see yatasView's own YatasView.qml header for why.
    property bool yatasActive: false

    readonly property bool contentLocked: {
        if (hostSettings.lockState === "unlocked") return false
        if (hostSettings.lockState === "locked") return true
        if (root.editingTaskDescription) return false
        // Whichever of the two is actually showing right now — auto-locked
        // must unlock on hover regardless of which one that is.
        var hovered = root.yatasActive ? yatasView.contentHovered
            : (contentLoader.item ? contentLoader.item.contentHovered : false)
        return !hovered && !root.dragHoverActive
    }

    // Drives the blur amount smoothly (see frostedContent's MultiEffect
    // below) rather than snapping instantly — 0 (fully clear) to 1 (fully
    // blurred, i.e. MultiEffect's blurMax radius). 150ms per explicit
    // request (shortened from the original 1-second spec in r-8.md).
    property real blurAmount: root.contentLocked ? 1.0 : 0.0
    Behavior on blurAmount {
        NumberAnimation { duration: 150 }
    }

    // Small transparent gap between the lock and close icon boxes (near the
    // bottom of this file), so they read as "two separate things near each
    // other" rather than one merged box.
    readonly property int lockCloseIconGap: Math.round(root.chromeFontPixelSize * 0.4)

    // Mirrors WindowManager.closeWindow()'s own "at least one must stay
    // open" guard, so the close button LOOKS disabled (dimmed, no hover
    // reaction, not clickable) rather than silently no-op-ing while still
    // appearing fully interactive.
    readonly property bool canCloseThisWindow: windowManager.openWindowCount > 1

    function nextLockState() {
        if (hostSettings.lockState === "unlocked") return "auto-locked"
        if (hostSettings.lockState === "auto-locked") return "locked"
        return "unlocked"
    }

    // Content wrapper: opacity applied here keeps popup menus (which render
    // in the Window Overlay above this Item) always at full opacity.
    // windowOpacity is plugin-owned (appSettings.opacityPercent) — read
    // back from the loaded content, defaulting to fully opaque before it
    // exists.
    Item {
        anchors.fill: parent
        opacity: contentLoader.item ? contentLoader.item.windowOpacity : 1.0

        // r-8.md "The glass lock": the background wash AND the plugin's
        // whole content are blurred together as ONE frosted pane. This is
        // a live GPU-rendered layer, not a one-off blurred snapshot — it
        // re-renders every frame from whatever the plugin's content
        // actually looks like right now.
        Item {
            id: frostedContent
            anchors.fill: parent
            // Inset to start exactly at the border line (half the tag
            // label's height down, same as windowBorder/the wash Rectangle
            // below), and clipped to that bound.
            anchors.topMargin: tagLabelBg.height / 2
            clip: true

            // blur: 0 (root.blurAmount, unlocked) renders identically to no
            // effect at all, so layer.enabled can stay unconditionally true
            // with no always-unlocked-window visual cost.
            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blur: root.blurAmount
                blurMax: 48
                autoPaddingEnabled: true
            }

            // The window itself stays fully transparent (per spec); this
            // wash is what actually paints the content panel's background,
            // translucent so the window still reads as "transparent"
            // rather than opaque. Still reads the plugin's own
            // Theme.contentBackground — this is the content panel's own
            // themed background, not one of the four host-chrome elements
            // this file otherwise keeps independent of the plugin's theme.
            Rectangle {
                anchors.fill: parent
                radius: 6
                color: Theme.contentBackground
            }

            // Same anchors/margins the old inline "contentColumn" ColumnLayout
            // used to have — applied here rather than inside the plugin's own
            // content, since only the host knows tagLabelBg's height (the
            // plugin has no visibility into host-owned chrome geometry).
            //
            // Stays loaded (never re-sourced) while yatasView is showing
            // instead — just hidden, so switching back to it is instant and
            // doesn't lose any in-progress plugin state (e.g. a half-typed
            // task, a scroll position).
            Loader {
                id: contentLoader
                anchors.fill: parent
                anchors.margins: 15
                anchors.topMargin: 15 + tagLabelBg.height / 2 + 4
                source: pluginContentUrl
                visible: !root.yatasActive
            }

            // Window management (r-3.md's original "YATAS" feature) — host
            // chrome, not plugin content, see YatasView.qml's own header.
            // Same geometry as contentLoader so contentOverlay's lock-time
            // input blocker (below, anchored off contentLoader's own x/y/
            // width/height) already covers this too with no extra wiring.
            YatasView {
                id: yatasView
                anchors.fill: contentLoader
                visible: root.yatasActive
                chromeTextColor: root.chromeTextColor
                chromeMutedTextColor: root.chromeMutedTextColor
                chromeAccentColor: root.chromeAccentColor
                chromeFontFamily: root.chromeFontFamily
                chromeFontPixelSize: root.chromeFontPixelSize
                chromeBoxColor: root.chromeBoxColor
            }
        }

        // Frosted-glass tint: a flat, NOT-blurred scrim sitting on top of
        // frostedContent's own blurred layer — a plain translucent color
        // doesn't change when blurred, so it has to live outside the
        // layered item to have any visible effect of its own. This is what
        // gives the "milky glass" look. Fades in/out with the same
        // blurAmount Behavior as the blur itself. Host-owned color (r-9.md:
        // "lock glass effect color" is explicitly the master application's
        // to control) — the user's custom border color if set, else the
        // same fixed cyan this app has always defaulted to, independent of
        // whatever tint the plugin's content is showing.
        Rectangle {
            anchors.fill: frostedContent
            radius: 6
            color: hostSettings.borderColor !== "" ? hostSettings.borderColor : root.chromeDragHoverColor
            opacity: root.blurAmount * 0.35
        }

        // r-8.md "The glass lock": sits on top of frostedContent (painting/
        // hit-testing above it — the frosted tint scrim above is purely
        // visual and never intercepts input). contentBlocker is a
        // MouseArea that, while enabled, grabs and swallows every mouse
        // press/click/wheel event over this area before the plugin's own
        // content ever sees it. While disabled (unlocked, or auto-locked-
        // and-currently-hovered), it's excluded from hit-testing entirely
        // and every event passes through to the real controls beneath,
        // untouched. This also means the plugin's own content no longer
        // needs any lock-awareness of its own (e.g. its right-click menu) —
        // it simply never receives input while blocked here.
        //
        // hoverEnabled: true is deliberate, not an oversight: while enabled
        // (plain "locked"), it must ALSO claim hover away from the
        // plugin's own rows/views underneath, or their own hover highlight
        // and hover-revealed action icons would keep visibly reacting to
        // the mouse even though the window is supposed to be fully locked/
        // inert.
        //
        // x/y/width/height read directly from contentLoader (replacing the
        // old "contentColumn") instead of anchors.fill: contentLoader —
        // QML anchoring only works between a parent/child or direct
        // siblings, and contentLoader is nested one level deeper inside
        // frostedContent.
        Item {
            id: contentOverlay
            x: contentLoader.x
            y: contentLoader.y
            width: contentLoader.width
            height: contentLoader.height

            MouseArea {
                id: contentBlocker
                anchors.fill: parent
                enabled: root.contentLocked
                // Only for plain "locked", NOT "auto-locked" — claiming
                // hover here for auto-locked's transient "enabled because
                // not yet hovering" phase would create a deadlock: that
                // phase's own enabled-ness depends on the plugin's own
                // hover detection (nested inside its content, i.e.
                // underneath this sibling in the z-stack) detecting the
                // mouse's arrival, and once this claims hover for itself
                // first, the plugin's hover handler never gets a turn to
                // notice anything ever arrived. Plain "locked" has no such
                // cycle (its enabled-ness doesn't depend on hover at all,
                // only on hostSettings.lockState), so it's safe to claim
                // hover there unconditionally.
                hoverEnabled: hostSettings.lockState === "locked"
                acceptedButtons: Qt.AllButtons
                onWheel: (event) => { event.accepted = true }
            }
        }

        Rectangle {
            id: windowBorder
            anchors.fill: parent
            anchors.topMargin: tagLabelBg.height / 2
            color: "transparent"
            radius: 6
            // Drop-target affordance for cross-window task drag — takes
            // priority over the user's own custom border color below —
            // it's a separate, transient "you're dropping here" signal,
            // not this window's persistent identity color.
            border.color: root.dragHoverActive ? root.chromeDragHoverColor : root.chromeAccentColor
            // A 1px stroke doesn't give MultiEffect's blur enough alpha
            // "mass" to build a visible halo from. Width 4 is what reads
            // as an actual neon-tube glow; drag-hover keeps its own
            // distinct 2px highlight width.
            border.width: root.dragHoverActive ? 2 : 4

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
        // tagEditField below.
        //
        // y is 0, not -height/2 — the two Rectangles above reserve exactly
        // height/2 of real space for it via their own topMargin, so its
        // vertical center still lands exactly on their (now inset) top
        // edge, without any part of the label needing a negative,
        // off-surface y.
        Rectangle {
            id: tagLabelBg
            x: 14
            y: 0
            visible: !root.editingTag
            radius: 3
            color: root.chromeBoxColor(false)
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
                color: hostSettings.borderColor !== "" ? hostSettings.borderColor : root.chromeTextColor
                font.bold: true
                font.family: root.chromeFontFamily
                font.pixelSize: Math.round(root.chromeFontPixelSize * 0.8)

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

            // Also doubles as the window's drag-to-move handle, now that
            // the plugin's own Toolbar no longer spans host-owned space —
            // its empty background used to serve that role. A DragHandler
            // (not a plain MouseArea.onPressed) deliberately: startSystemMove()
            // hands the pointer grab to the window manager the instant it's
            // called, so calling it unconditionally on every press (as a
            // MouseArea would) ate the second click of the double-click
            // above before Qt's own TapHandler ever saw it — confirmed live,
            // double-click-to-rename silently stopped working the moment this
            // drag handle was added. DragHandler only goes active once the
            // press has actually moved past Qt's drag threshold, so a plain
            // double-click (no movement in between) never triggers it at all.
            DragHandler {
                target: null
                onActiveChanged: if (active) root.startSystemMove()
            }
        }

        // Edit-mode swap-in for the tag label above, styled like a simple
        // input field. Spans from the label's own start x to half the
        // window's width, rather than matching tagLabelBg's own (much
        // narrower, elide-capped) width.
        TextField {
            id: tagEditField
            x: tagLabelBg.x
            y: 0
            width: root.width / 2 - x
            visible: root.editingTag
            text: root.windowTag
            color: root.chromeTextColor
            font.bold: true
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 0.8)
            background: Rectangle {
                radius: 4
                color: root.chromeBoxColor(false)
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

        // Classic "X" close-window button — closes (hides, per
        // WindowManager.closeWindow) THIS window, same as YatasView's own
        // SHOW toggle does for any window from the list; a no-op if this is
        // the only window currently open (guarded inside closeWindow itself).
        // Sits at the very right edge, in the outermost position, with the
        // lock icon positioned to its left below.
        Rectangle {
            id: closeIconBg
            y: 0
            height: tagLabelBg.height
            radius: 3
            // Dimmed and inert once this is the only open window — closing
            // it would already be a no-op server-side (WindowManager.
            // closeWindow's own guard), but it must also LOOK disabled
            // rather than fully interactive-looking while quietly doing
            // nothing. closeMouseArea.enabled below being false makes
            // containsMouse never turn true on its own, so no extra
            // guarding is needed in the color/glow bindings.
            opacity: root.canCloseThisWindow ? 1.0 : 0.35
            color: root.chromeBoxColor(closeMouseArea.containsMouse)
            width: closeGlyph.implicitWidth + 16
            x: root.width - 14 - width

            layer.enabled: closeMouseArea.containsMouse
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: closeGlyph.color
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.08
            }

            Text {
                id: closeGlyph
                anchors.centerIn: parent
                text: "✕"
                font.bold: true
                font.pixelSize: Math.round(closeIconBg.height * 0.85)
                color: root.chromeAccentColor
            }

            MouseArea {
                id: closeMouseArea
                anchors.fill: parent
                anchors.margins: -4
                enabled: root.canCloseThisWindow
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: windowManager.closeWindow(windowId)
                ToolTip.visible: containsMouse
                ToolTip.text: qsTr("Close window")
            }
        }

        // r-8.md "The glass lock": same margin (14) from the right edge that
        // the tag label has from the left, same y (0, straddling the border
        // line), same height. Always clickable/crisp regardless of lock
        // state: it lives outside contentLoader/contentOverlay entirely, so
        // it's never blurred or blocked — the one control that must always
        // work, or a locked window could never be unlocked again.
        Rectangle {
            id: lockIconBg
            y: 0
            height: tagLabelBg.height
            radius: 3
            color: root.chromeBoxColor(lockMouseArea.containsMouse)
            width: lockIcon.width + 12
            x: closeIconBg.x - root.lockCloseIconGap - width

            layer.enabled: lockMouseArea.containsMouse
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: lockIcon.iconColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.08
            }

            Image {
                id: lockIcon
                readonly property string iconName: hostSettings.lockState === "locked" ? "lock_locked"
                    : hostSettings.lockState === "auto-locked" ? "lock_autolocked" : "lock_unlocked"
                readonly property color iconColor: root.chromeAccentColor

                anchors.centerIn: parent
                height: parent.height - 4
                width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                fillMode: Image.PreserveAspectFit
                smooth: true
                source: iconProvider.coloredSvgUri(iconName, iconColor.toString())
            }

            MouseArea {
                id: lockMouseArea
                anchors.fill: parent
                anchors.margins: -4
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: hostSettings.lockState = root.nextLockState()
                ToolTip.visible: containsMouse
                ToolTip.text: lockIcon.iconName === "lock_locked" ? qsTr("Locked — click to unlock")
                    : lockIcon.iconName === "lock_autolocked" ? qsTr("Auto-locked — click to lock")
                    : qsTr("Unlocked — click to auto-lock")
            }
        }

        // Window management (r-3.md's original "YATAS" feature) toggle —
        // host chrome, always available regardless of which plugin this
        // window is running (see YatasView.qml's own header for why this
        // moved out of the plugin). Same box style/size as the lock icon,
        // sitting just to its left. "Y" is a placeholder glyph (explicit
        // request) — swap for a real icon later the same way lock/close
        // already use iconProvider.coloredSvgUri().
        Rectangle {
            id: yatasIconBg
            y: 0
            height: tagLabelBg.height
            radius: 3
            // Active state lights the BOX, not the glyph — same convention
            // lock/close already use (their own glyph color never changes;
            // only the box reacts, to hover there). Matches the old
            // plugin-owned Yatas toolbar button's own look before this
            // moved to host chrome.
            color: root.yatasActive ? root.chromeAccentColor : root.chromeBoxColor(yatasMouseArea.containsMouse)
            width: yatasGlyph.implicitWidth + 16
            x: lockIconBg.x - root.lockCloseIconGap - width

            layer.enabled: yatasMouseArea.containsMouse || root.yatasActive
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.08
            }

            Text {
                id: yatasGlyph
                anchors.centerIn: parent
                text: "Y"
                font.bold: true
                font.family: root.chromeFontFamily
                font.pixelSize: Math.round(yatasIconBg.height * 0.6)
                color: root.chromeTextColor
            }

            MouseArea {
                id: yatasMouseArea
                anchors.fill: parent
                anchors.margins: -4
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.yatasActive = !root.yatasActive
                ToolTip.visible: containsMouse
                ToolTip.text: qsTr("Manage windows")
            }
        }
    }
}

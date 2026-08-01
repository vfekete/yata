import QtQuick
import QtQuick.Controls

// Shown instead of the task ListView when Toolbar's "Yatas" button is
// active: every known YATA window (id + tag), across the whole registry —
// not just ones currently open (r-3.md: you can rename/delete a window
// that isn't running right now).
Item {
    id: root
    property string searchText: ""

    // Driven by FilterBar's own ACTIVE/DELETED visibility+order buttons
    // (relayed down via Main.qml, same pattern as searchText above) —
    // mirrors taskModel's showActive/showDone/showCancelled + statusSortMode
    // shape: showActive/showDeleted are independent toggles (both can be on
    // at once, showing both categories together in one list), sortMode
    // picks which category sorts to the top when both are visible.
    property bool showActive: true
    property bool showDeleted: false
    property string sortMode: ""

    property var allWindows: []
    function refresh() { root.allWindows = windowManager.listWindows() }

    onVisibleChanged: if (visible) refresh()
    Connections {
        target: windowManager
        function onWindowsChanged() { if (root.visible) root.refresh() }
    }

    // Passed down to every row so it can hide its own SHOW toggle when it's
    // the last open window — closing it would leave nothing on screen and
    // no YatasView left to reopen anything from (WindowManager.closeWindow
    // enforces the same guard independently, this just keeps the button
    // from offering an action that would silently no-op).
    readonly property int openWindowCount: root.allWindows.filter(function(w) { return w.open }).length

    readonly property var filteredWindows: {
        var needle = root.searchText.trim().toLowerCase()
        var items = root.allWindows.filter(function(w) {
            if (w.deleted ? !root.showDeleted : !root.showActive)
                return false
            if (needle.length > 0 && String(w.tag).toLowerCase().indexOf(needle) === -1)
                return false
            return true
        })
        // Stable sort (Array.prototype.sort is spec-guaranteed stable) —
        // brings the selected category to the top while leaving each
        // category's own relative order (registry order) unchanged
        // otherwise, same "insert after" instinct as taskModel's own
        // statusSortMode, just with an explicit wantDeleted flag instead of
        // a status string.
        if (root.sortMode === "active" || root.sortMode === "deleted") {
            var wantDeleted = root.sortMode === "deleted"
            items = items.slice().sort(function(a, b) {
                return (a.deleted === wantDeleted ? 0 : 1) - (b.deleted === wantDeleted ? 0 : 1)
            })
        }
        return items
    }

    ListView {
        id: windowsList
        anchors.fill: parent
        clip: true
        spacing: 0
        model: root.filteredWindows
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        delegate: YatasRow {
            required property var modelData
            width: windowsList.width
            windowId: modelData.id
            tag: modelData.tag
            open: modelData.open
            deleted: modelData.deleted
            openWindowCount: root.openWindowCount
            onRenamed: (id, newTag) => windowManager.renameWindow(id, newTag)
            onDeleteRequested: (id, tag) => deleteDialog.openFor(id, tag)
            onShowToggled: (id, show) => show ? windowManager.openWindow(id) : windowManager.closeWindow(id)
            onRecreateRequested: (id) => windowManager.recreateWindow(id)
            onPurgeRequested: (id, tag) => purgeDialog.openFor(id, tag)
            onBorderColorPicked: (id, color) => windowManager.setBorderColor(id, color)
        }
    }

    Text {
        anchors.centerIn: parent
        visible: root.filteredWindows.length === 0
        text: root.allWindows.length === 0 ? qsTr("No windows") : qsTr("No windows match your search or filters")
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }

    DeleteWindowDialog {
        id: deleteDialog
        onConfirmed: (id) => windowManager.deleteWindow(id)
    }

    PurgeWindowDialog {
        id: purgeDialog
        onConfirmed: (id) => windowManager.purgeWindow(id)
    }
}

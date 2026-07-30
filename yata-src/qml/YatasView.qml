import QtQuick
import QtQuick.Controls

// Shown instead of the task ListView when Toolbar's "Yatas" button is
// active: every known YATA window (id + tag), across the whole registry —
// not just ones currently open (r-3.md: you can rename/delete a window
// that isn't running right now).
Item {
    id: root
    property string searchText: ""

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
        if (needle.length === 0)
            return root.allWindows
        return root.allWindows.filter(function(w) {
            return String(w.tag).toLowerCase().indexOf(needle) !== -1
        })
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
            openWindowCount: root.openWindowCount
            onRenamed: (id, newTag) => windowManager.renameWindow(id, newTag)
            onDeleteRequested: (id, tag) => deleteDialog.openFor(id, tag)
            onShowToggled: (id, show) => show ? windowManager.openWindow(id) : windowManager.closeWindow(id)
        }
    }

    Text {
        anchors.centerIn: parent
        visible: root.filteredWindows.length === 0
        text: root.allWindows.length === 0 ? "No windows" : "No windows match your search"
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }

    DeleteWindowDialog {
        id: deleteDialog
        onConfirmed: (id, deleteData) => windowManager.deleteWindow(id, deleteData)
    }
}

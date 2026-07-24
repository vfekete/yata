import QtQuick
import QtQuick.Controls

// Shown instead of the task ListView when Toolbar's "Links" button is
// active: every task that mentions at least one Markdown [label](url) link,
// regardless of status or the current visibility/search filters (a lookup
// across ALL tasks, matching taskModel.linkedTasks()'s own semantics).
Item {
    id: root
    signal toTaskClicked(string taskId)

    // Set from Main.qml, mirroring the toolbar search field while Links is
    // active. Filtering happens client-side against the already-fetched
    // linkedTasks below, not via taskModel — this is a separate search
    // context from the main list's, matching a link's label/url, not the
    // task's raw text.
    property string searchText: ""

    // Plain property, not reactively bound to task mutations — same known
    // limitation as MonthView/YearView's countsByDay/countsByMonth (no
    // "any task changed" signal to bind to); re-evaluated each time this
    // view becomes visible via the visible-changed handler below.
    property var linkedTasks: []

    onVisibleChanged: if (visible) linkedTasks = taskModel.linkedTasks()

    readonly property var filteredTasks: {
        var needle = root.searchText.trim().toLowerCase()
        if (needle.length === 0)
            return root.linkedTasks
        return root.linkedTasks.filter(function(t) {
            for (var i = 0; i < t.links.length; i++) {
                var l = t.links[i]
                if (String(l.label).toLowerCase().indexOf(needle) !== -1
                    || String(l.url).toLowerCase().indexOf(needle) !== -1)
                    return true
            }
            return false
        })
    }

    ListView {
        id: linksList
        anchors.fill: parent
        clip: true
        spacing: 0
        model: root.filteredTasks
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        delegate: LinkRow {
            required property var modelData
            width: linksList.width
            taskId: modelData.taskId
            status: modelData.status
            completedAt: modelData.completedAt
            links: modelData.links
            onToTaskClicked: (taskId) => root.toTaskClicked(taskId)
        }
    }

    Text {
        anchors.centerIn: parent
        visible: root.filteredTasks.length === 0
        text: root.linkedTasks.length === 0 ? "No links found in any task" : "No links match your search"
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }
}

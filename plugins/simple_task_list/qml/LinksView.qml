import QtQuick
import QtQuick.Controls

Item {
    id: root
    signal toTaskClicked(string taskId)

    property string searchText: ""

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
        text: root.linkedTasks.length === 0 ? qsTr("No links found in any task") : qsTr("No links match your search")
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }
}

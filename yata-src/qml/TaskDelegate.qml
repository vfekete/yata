import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property int index
    required property string taskId
    required property string text
    required property string status
    required property string dayLabel

    property bool forceEditing: false
    readonly property bool editing: forceEditing || text.length === 0
    readonly property bool hovered: hoverHandler.hovered

    width: ListView.view.width
    height: Math.max(30, mainRow.implicitHeight + 12)

    HoverHandler { id: hoverHandler }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: itemMenu.popup()
    }

    Menu {
        id: itemMenu
        MenuItem { text: "Delete task"; onTriggered: taskModel.deleteTask(root.taskId); padding: 10 }
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? Theme.hoverColor : "transparent"
    }

    // Marks the current drop target while a drag is in progress.
    Rectangle {
        visible: root.ListView.view.dragActive
                 && root.ListView.view.dragHoverIndex === root.index
                 && root.index !== root.ListView.view.dragFromIndex
        anchors.top: parent.top
        width: parent.width
        height: 2
        color: Theme.accentColor
    }

    opacity: root.ListView.view.dragActive && root.ListView.view.dragFromIndex === root.index ? 0.4 : 1.0

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        // Day-grouped view gets extra left indent so rows read as nested
        // under their day header rather than flush with it.
        anchors.leftMargin: taskModel.groupByDay ? 24 : 4
        anchors.rightMargin: 4
        spacing: 4

        Text {
            id: dragHandle
            text: "⋮⋮"
            color: Theme.mutedTextColor
            font.family: Theme.fontFamily
            visible: root.hovered && taskModel.canReorder
            Layout.alignment: Qt.AlignVCenter

            MouseArea {
                anchors.fill: parent
                anchors.margins: -4
                cursorShape: Qt.SizeVerCursor
                preventStealing: true

                onPressed: {
                    var view = root.ListView.view
                    view.dragActive = true
                    view.dragFromIndex = root.index
                    view.dragHoverIndex = root.index
                }
                onPositionChanged: (mouse) => {
                    var view = root.ListView.view
                    if (!view.dragActive)
                        return
                    var posInView = mapToItem(view, mouse.x, mouse.y)
                    var idx = view.indexAt(1, posInView.y + view.contentY)
                    if (idx >= 0)
                        view.dragHoverIndex = idx
                }
                onReleased: {
                    var view = root.ListView.view
                    if (view.dragActive && view.dragHoverIndex >= 0 && view.dragHoverIndex !== view.dragFromIndex)
                        taskModel.moveTask(view.dragFromIndex, view.dragHoverIndex)
                    view.dragActive = false
                    view.dragFromIndex = -1
                    view.dragHoverIndex = -1
                }
            }
        }

        Text {
            id: statusIcon
            visible: !root.editing && root.status !== "active"
            text: root.status === "done" ? "✓" : "✕"
            color: root.status === "done" ? Theme.checkIconColor : Theme.crossIconColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize * 0.85
            Layout.alignment: Qt.AlignVCenter
        }

        Text {
            Layout.fillWidth: true
            visible: !root.editing
            text: root.text
            textFormat: Text.MarkdownText
            wrapMode: Text.Wrap
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            color: {
                if (root.status === "done") return Theme.doneColor
                if (root.status === "cancelled") return Theme.cancelledColor
                return Theme.textColor
            }
            font.strikeout: root.status !== "active"

            TapHandler {
                onDoubleTapped: root.forceEditing = true
            }
        }

        TextField {
            id: editField
            Layout.fillWidth: true
            visible: root.editing
            text: root.text
            placeholderText: "Task name"
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }
            onVisibleChanged: if (visible) forceActiveFocus()
            Component.onCompleted: if (visible) forceActiveFocus()
            onEditingFinished: {
                root.forceEditing = false
                taskModel.setText(root.taskId, text)
            }
        }

        Row {
            visible: root.hovered && !root.editing
            spacing: 4
            Layout.alignment: Qt.AlignVCenter

            // 2x the task text size (was unset/default-sized), per user
            // feedback that these hover action targets were hard to hit.
            Text {
                text: "✓"
                color: Theme.doneColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                TapHandler { onTapped: taskModel.setStatus(root.taskId, "done") }
            }
            Text {
                text: "✕"
                color: Theme.cancelledColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                TapHandler { onTapped: taskModel.setStatus(root.taskId, "cancelled") }
            }
            Text {
                text: "↺"
                color: Theme.accentColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                visible: root.status !== "active"
                TapHandler { onTapped: taskModel.setStatus(root.taskId, "active") }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: contentRoot
    anchors.fill: parent

    readonly property alias actionButtonsWidth: toolbar.actionButtonsWidth
    readonly property alias contentHovered: contentHoverHandler.hovered
    readonly property real windowOpacity: Theme.windowOpacity

    property int calYear: new Date().getFullYear()
    property int calMonth: new Date().getMonth() + 1
    property int calYearPage: new Date().getFullYear()

    readonly property bool noteEditorVisible: listView.noteEditorTaskId !== "" && !filterBar.linksActive

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: contextMenu.popup()
    }

    ThemeMenu {
        id: contextMenu
        showQuit: true
    }

    Connections {
        target: windowManager
        function onTaskDragHoverChanged(targetWindowId, globalX, globalY) {
            if (targetWindowId !== windowId) {
                listView.dragHoverActive = false
                listView.dragHoverIndex = -1
                return
            }
            var win = contentRoot.Window.window
            var posInWindow = Qt.point(globalX - win.x, globalY - win.y)
            var posInListView = listView.mapFromItem(null, posInWindow.x, posInWindow.y)
            listView.dragHoverActive = true
            var idx = listView.indexAt(1, posInListView.y + listView.contentY)
            if (idx >= 0)
                listView.dragHoverIndex = idx
            listView.lastDragLocalY = posInListView.y
            windowManager.setDragHoverIndex(listView.dragHoverIndex)
        }
    }

    ColumnLayout {
        id: contentColumn
        anchors.fill: parent
        spacing: 2

        HoverHandler {
            id: contentHoverHandler
        }

        Toolbar {
            id: toolbar
            Layout.fillWidth: true
            linksActive: filterBar.linksActive
            onLinksToggled: filterBar.setGrouping("links", !filterBar.linksActive)
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
                visible: !filterBar.monthActive && !filterBar.yearActive && !filterBar.linksActive && listView.noteEditorTaskId === ""
                clip: true
                spacing: 0
                model: taskModel
                ScrollBar.vertical: ScrollBar { id: vbar; policy: ScrollBar.AsNeeded }

                section.property: taskModel.groupByDay ? "dayLabel" : ""
                section.criteria: ViewSection.FullString
                section.delegate: sectionHeader

                property bool dragActive: false
                property int dragFromIndex: -1
                property bool dragHoverActive: false
                property int dragHoverIndex: -1
                property string dragTargetWindowId: ""
                property real lastDragLocalY: -1

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

                property string flashTaskId: ""
                Timer {
                    id: flashTimer
                    interval: 1200
                    onTriggered: listView.flashTaskId = ""
                }

                property string noteEditorTaskId: ""

                property real rowWidth: width - (vbar.visible ? vbar.width : 0)

                delegate: TaskDelegate {
                    width: listView.rowWidth
                }
            }

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

            NoteEditorView {
                anchors.fill: parent
                visible: contentRoot.noteEditorVisible
                taskId: listView.noteEditorTaskId
                onClosed: listView.noteEditorTaskId = ""
            }
        }
    }

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
                font.pixelSize: Theme.taskFontPixelSize * 1.5
                font.family: Theme.fontFamily
            }
        }
    }
}

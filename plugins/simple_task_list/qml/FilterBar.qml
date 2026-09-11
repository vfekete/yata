import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Item {
    id: root
    implicitHeight: flow.implicitHeight + 4

    property bool monthActive: false
    property bool yearActive: false
    property bool linksActive: false

    property bool subToolbarDisabled: false

    function setGrouping(which, checked) {
        if (checked) {
            root.monthActive = (which === "month")
            root.yearActive = (which === "year")
            root.linksActive = (which === "links")
            taskModel.setGroupByDay(which === "day")
        } else if (which === "day") {
            taskModel.setGroupByDay(false)
        } else if (which === "month") {
            root.monthActive = false
        } else if (which === "year") {
            root.yearActive = false
        } else {
            root.linksActive = false
        }
    }

    MouseArea {
        anchors.fill: parent
        onPressed: Window.window.startSystemMove()
    }

    readonly property int buttonSpacing: Math.round(Theme.taskFontPixelSize * 8 / 14)
    readonly property int groupGap: Math.round(Theme.taskFontPixelSize * 18 / 14)

    Flow {
        id: flow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: root.groupGap
        enabled: !root.subToolbarDisabled
        opacity: root.subToolbarDisabled ? 0.4 : 1.0

        RowLayout {
            spacing: root.buttonSpacing
            IconIndicator { iconName: "calendar"; sizeScale: 0.9 }
            FilterButton {
                label: qsTr("Day")
                active: taskModel.groupByDay
                onToggled: (checked) => root.setGrouping("day", checked)
            }
            FilterButton {
                label: qsTr("Month")
                active: root.monthActive
                onToggled: (checked) => root.setGrouping("month", checked)
            }
            FilterButton {
                label: qsTr("Year")
                active: root.yearActive
                onToggled: (checked) => root.setGrouping("year", checked)
            }
        }

        RowLayout {
            spacing: root.buttonSpacing
            IconIndicator { iconName: "visibility"; sizeScale: 0.9 }
            FilterButton {
                label: qsTr("Active")
                active: taskModel.showActive
                onToggled: (checked) => taskModel.setShowActive(checked)
            }
            FilterButton {
                label: qsTr("Done")
                active: taskModel.showDone
                onToggled: (checked) => taskModel.setShowDone(checked)
            }
            FilterButton {
                label: qsTr("Cancel")
                active: taskModel.showCancelled
                onToggled: (checked) => taskModel.setShowCancelled(checked)
            }
        }

        Item {
            id: orderGroup
            implicitWidth: orderRow.implicitWidth
            implicitHeight: orderRow.implicitHeight
            opacity: orderBlocker.enabled ? 0.4 : 1.0

            RowLayout {
                id: orderRow
                anchors.fill: parent
                spacing: root.buttonSpacing
                IconIndicator { iconName: "order"; sizeScale: 0.9 }
                FilterButton {
                    label: qsTr("Active")
                    active: taskModel.statusSortMode === "active"
                    onToggled: (checked) => taskModel.setStatusSortMode(checked ? "active" : "")
                }
                FilterButton {
                    label: qsTr("Done")
                    active: taskModel.statusSortMode === "done"
                    onToggled: (checked) => taskModel.setStatusSortMode(checked ? "done" : "")
                }
                FilterButton {
                    label: qsTr("Cancel")
                    active: taskModel.statusSortMode === "cancelled"
                    onToggled: (checked) => taskModel.setStatusSortMode(checked ? "cancelled" : "")
                }
            }

            MouseArea {
                id: orderBlocker
                anchors.fill: parent
                enabled: root.monthActive || root.yearActive
                hoverEnabled: true
                onPressed: {}
            }
        }
    }
}

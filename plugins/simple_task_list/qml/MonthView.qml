import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property int year
    property int month
    signal dayClicked(int year, int month, int day)
    signal prevMonth()
    signal nextMonth()

    readonly property var monthNames: [qsTr("January"), qsTr("February"), qsTr("March"), qsTr("April"),
        qsTr("May"), qsTr("June"), qsTr("July"), qsTr("August"), qsTr("September"), qsTr("October"),
        qsTr("November"), qsTr("December")]
    readonly property var weekdayLabels: [qsTr("Mon"), qsTr("Tue"), qsTr("Wed"), qsTr("Thu"),
        qsTr("Fri"), qsTr("Sat"), qsTr("Sun")]

    function daysInMonth(y, m) {
        return new Date(y, m, 0).getDate()
    }
    function firstWeekdayIndex(y, m) {
        return (new Date(y, m - 1, 1).getDay() + 6) % 7
    }

    property var countsByDay: {
        var raw = taskModel.monthCounts(root.year, root.month)
        var map = {}
        for (var i = 0; i < raw.length; i++)
            map[raw[i].day] = raw[i]
        return map
    }

    readonly property real cellSize: {
        var availW = (width - 6 * dayGrid.columnSpacing) / 7
        var usedH = pagerRow.height + outerCol.spacing + weekdayRow.height + calendarBlock.spacing
        var availH = (height - usedH - 5 * dayGrid.rowSpacing) / 6
        return Math.max(20, Math.min(availW, availH))
    }

    ColumnLayout {
        id: outerCol
        anchors.fill: parent
        anchors.margins: 8
        spacing: 8

        RowLayout {
            id: pagerRow
            Layout.fillWidth: true
            PagerArrow { symbol: "‹"; onClicked: root.prevMonth() }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: qsTr("%1 %2").arg(root.monthNames[root.month - 1]).arg(root.year)
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.3)
                color: Theme.textColor
            }
            PagerArrow { symbol: "›"; onClicked: root.nextMonth() }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            ColumnLayout {
                id: calendarBlock
                x: Math.round((parent.width - width) / 2)
                spacing: 4

                RowLayout {
                    id: weekdayRow
                    spacing: dayGrid.columnSpacing

                    Repeater {
                        model: root.weekdayLabels
                        delegate: Text {
                            required property string modelData
                            Layout.preferredWidth: root.cellSize
                            horizontalAlignment: Text.AlignHCenter
                            text: modelData
                            color: Theme.mutedTextColor
                            font.family: Theme.fontFamily
                            font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.8)
                        }
                    }
                }

                GridLayout {
                    id: dayGrid
                    columns: 7
                    rowSpacing: 4
                    columnSpacing: 4

                    Repeater {
                        model: 42
                        delegate: CalendarCell {
                            id: dayCell
                            required property int index
                            readonly property int dayNum: index - root.firstWeekdayIndex(root.year, root.month) + 1
                            readonly property bool inMonth: dayNum >= 1 && dayNum <= root.daysInMonth(root.year, root.month)
                            readonly property var dayCounts: inMonth ? root.countsByDay[dayNum] : undefined

                            Layout.preferredWidth: root.cellSize
                            Layout.preferredHeight: root.cellSize
                            valid: dayCell.inMonth
                            label: dayCell.inMonth ? String(dayCell.dayNum) : ""
                            activeCount: dayCell.dayCounts ? dayCell.dayCounts.active : 0
                            doneCount: dayCell.dayCounts ? dayCell.dayCounts.done : 0
                            cancelledCount: dayCell.dayCounts ? dayCell.dayCounts.cancelled : 0
                            onClicked: root.dayClicked(root.year, root.month, dayCell.dayNum)
                        }
                    }
                }
            }
        }
    }
}

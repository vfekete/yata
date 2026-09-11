import QtQuick
import QtQuick.Layouts

Item {
    id: root
    property int year
    signal monthClicked(int year, int month)
    signal prevYear()
    signal nextYear()

    readonly property var monthNames: [qsTr("January"), qsTr("February"), qsTr("March"), qsTr("April"),
        qsTr("May"), qsTr("June"), qsTr("July"), qsTr("August"), qsTr("September"), qsTr("October"),
        qsTr("November"), qsTr("December")]

    property var countsByMonth: {
        var raw = taskModel.yearCounts(root.year)
        var map = {}
        for (var i = 0; i < raw.length; i++)
            map[raw[i].month] = raw[i]
        return map
    }

    readonly property real cellSize: {
        var availW = (width - 3 * monthGrid.columnSpacing) / 4
        var usedH = pagerRow.height + outerCol.spacing
        var availH = (height - usedH - 2 * monthGrid.rowSpacing) / 3
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
            PagerArrow { symbol: "‹"; onClicked: root.prevYear() }
            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: String(root.year)
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.3)
                color: Theme.textColor
            }
            PagerArrow { symbol: "›"; onClicked: root.nextYear() }
        }

        Item {
            Layout.fillWidth: true
            Layout.fillHeight: true

            GridLayout {
                id: monthGrid
                x: Math.round((parent.width - width) / 2)
                columns: 4
                rowSpacing: 6
                columnSpacing: 6

                Repeater {
                    model: 12
                    delegate: CalendarCell {
                        id: monthCell
                        required property int index
                        readonly property var monthCounts: root.countsByMonth[index + 1]

                        Layout.preferredWidth: root.cellSize
                        Layout.preferredHeight: root.cellSize
                        label: root.monthNames[index]
                        activeCount: monthCell.monthCounts ? monthCell.monthCounts.active : 0
                        doneCount: monthCell.monthCounts ? monthCell.monthCounts.done : 0
                        cancelledCount: monthCell.monthCounts ? monthCell.monthCounts.cancelled : 0
                        onClicked: root.monthClicked(root.year, monthCell.index + 1)
                    }
                }
            }
        }
    }
}

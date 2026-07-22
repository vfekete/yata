import QtQuick
import QtQuick.Layouts

// Year grid (12 months, 4x3), shown instead of the task ListView when
// FilterBar's "Year" button is active. Same presentational/props-in-signals-
// out shape as MonthView, for the same reason (Main.qml owns `year` so the
// binding from Main.qml never gets clobbered by internal reassignment).
Item {
    id: root
    property int year
    signal monthClicked(int year, int month)
    signal prevYear()
    signal nextYear()

    readonly property var monthNames: ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"]

    property var countsByMonth: {
        var raw = taskModel.yearCounts(root.year)
        var map = {}
        for (var i = 0; i < raw.length; i++)
            map[raw[i].month] = raw[i]
        return map
    }

    // Square cells, same reasoning as MonthView.cellSize: sized off
    // whichever dimension (4 columns wide, 3 rows tall) is tighter.
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

        // Plain Item wrapper, not itself Layout-managed alignment: GridLayout's
        // x is bound directly to its OWN current width below, rather than via
        // Layout.alignment: Qt.AlignHCenter. That attached property positions
        // the item using the *previous* layout pass's implicit width, one
        // frame behind the grid's actual rendered width (which reacts to
        // cellSize-driven Layout.preferredWidth on each cell) — during a fast
        // window-width drag this one-frame lag was visible as the grid
        // overflowing past the right edge while the left gap stayed "correct"
        // (confirmed: at one width, grid.x=8 but grid.width overflowed the
        // container by 10px). Binding x directly to `width` here means both
        // update together in the same pass, no separate stale-alignment step.
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

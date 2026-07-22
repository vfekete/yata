import QtQuick
import QtQuick.Layouts

// Month calendar grid, shown instead of the task ListView when FilterBar's
// "Month" button is active. Always 7 columns (Monday-first) regardless of
// window width — cells shrink, the grid never reflows — per explicit
// request. Purely presentational: year/month are owned by Main.qml (which
// also owns the prev/next paging logic, via prevMonth()/nextMonth()) so the
// year/month property bindings from Main.qml never get clobbered by this
// component reassigning them internally.
Item {
    id: root
    property int year
    property int month  // 1-12
    signal dayClicked(int year, int month, int day)
    signal prevMonth()
    signal nextMonth()

    readonly property var monthNames: ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"]
    readonly property var weekdayLabels: ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    function daysInMonth(y, m) {
        return new Date(y, m, 0).getDate()
    }
    // JS Date.getDay() is 0=Sunday..6=Saturday; convert to 0=Monday..6=Sunday.
    function firstWeekdayIndex(y, m) {
        return (new Date(y, m - 1, 1).getDay() + 6) % 7
    }

    // Sparse day->{active,done,cancelled} lookup, rebuilt whenever the shown
    // month changes or the model's data does (taskModel has no changed
    // signal for "any task at all changed" that we bind to directly here;
    // Main.qml re-reads this on every dayClicked/mutation-driven view swap
    // since the component is never destroyed, and reopening Month after
    // editing tasks re-evaluates this binding via year/month re-assignment
    // in practice — see project memory for the known limitation if counts
    // ever look stale after an edit made while already on this view).
    property var countsByDay: {
        var raw = taskModel.monthCounts(root.year, root.month)
        var map = {}
        for (var i = 0; i < raw.length; i++)
            map[raw[i].day] = raw[i]
        return map
    }

    // Each day cell is square, sized off whichever dimension is tighter:
    // width so 7 columns exactly fill the available width, or height so 6
    // rows exactly fill the space left under the pager/weekday-label rows.
    // Previously each cell just used Layout.fillWidth/fillHeight, which left
    // GridLayout to size each COLUMN off its children's own implicitWidth —
    // for the weekday-label row that meant each column's width came from
    // that abbreviation's natural (proportional-font) text width ("Fri"'s
    // narrow "i" vs "Tue"/"Sat"'s wider letters), not a shared value, so
    // columns ended up visibly uneven.
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
                text: root.monthNames[root.month - 1] + " " + root.year
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.3)
                color: Theme.textColor
            }
            PagerArrow { symbol: "›"; onClicked: root.nextMonth() }
        }

        // Plain Item wrapper, not itself Layout-managed alignment: the block
        // below is positioned by binding its x directly to its OWN current
        // width, rather than via Layout.alignment: Qt.AlignHCenter on each
        // row individually. That attached property positions using the
        // *previous* layout pass's implicit width, one frame behind the
        // actual rendered width (which reacts to cellSize-driven
        // Layout.preferredWidth on each cell) — during a fast window-width
        // drag this one-frame lag was visible as the grid overflowing past
        // the right edge while the left gap stayed "correct". Binding x
        // directly to `width` here means both update together in the same
        // pass. Weekday labels and day cells are grouped into one nested
        // ColumnLayout (calendarBlock) and centered as a single unit so the
        // two rows can't drift out of alignment with each other either.
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

                    // 6 weeks x 7 days covers every possible month layout.
                    // Cells before day 1 or after the month's last day render
                    // blank (see CalendarCell's valid: false handling) but
                    // still occupy their grid slot, keeping the 7-column
                    // alignment intact.
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

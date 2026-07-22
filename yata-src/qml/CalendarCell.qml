import QtQuick
import QtQuick.Layouts

// One box in MonthView's day grid or YearView's month grid: a label (day
// number / month name) plus active/done/cancelled counts, clickable.
// `valid: false` (MonthView's leading/trailing blanks outside the shown
// month) keeps the Rectangle present — so GridLayout still reserves its
// column slot, preserving the fixed 7-per-row grid — but renders it blank
// and non-interactive instead of removing it from layout entirely.
Rectangle {
    id: cell
    property string label: ""
    property int activeCount: 0
    property int doneCount: 0
    property int cancelledCount: 0
    property bool valid: true
    signal clicked()

    color: !valid ? "transparent" : (hh.hovered ? Theme.hoverColor : Theme.fieldColor)
    radius: 4
    border.width: valid ? 1 : 0
    border.color: Theme.borderColor

    HoverHandler { id: hh; enabled: cell.valid; cursorShape: Qt.PointingHandCursor }
    TapHandler { enabled: cell.valid; onTapped: cell.clicked() }

    // Font sizes are fractions of the cell's OWN size, not a fixed multiple
    // of Theme.taskFontPixelSize — cellSize (set by MonthView/YearView) is
    // already the tighter of "window width / 7" and "window height / 6", so
    // deriving from it keeps the label/counts scaling with whatever actually
    // shrinks or grows the cell (window resize) *and* with font zoom, since
    // MonthView's own cellSize shrinks as the zoomed weekday-header row
    // takes more space. A fixed task-font multiple didn't track either —
    // at a small window or high zoom the numbers could outgrow their square.
    readonly property real boxSize: Math.min(width, height)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 2
        visible: cell.valid

        Text {
            text: cell.label
            font.bold: true
            font.family: Theme.fontFamily
            font.pixelSize: Math.max(8, Math.round(cell.boxSize * 0.18))
            color: Theme.textColor
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            spacing: 8
            // checkIconColor/crossIconColor (not doneColor/cancelledColor)
            // match the green check / red cross used elsewhere in the app:
            // doneColor is the muted strikethrough *text* color (deliberately
            // gray, not green, for "none" theme), which read as "wrong"/
            // uncolored here even though it's correct for the task list.
            Text {
                text: cell.activeCount
                visible: cell.activeCount > 0
                color: Theme.textColor
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.max(8, Math.round(cell.boxSize * 0.22))
            }
            Text {
                text: cell.doneCount
                visible: cell.doneCount > 0
                color: Theme.checkIconColor
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.max(8, Math.round(cell.boxSize * 0.22))
            }
            Text {
                text: cell.cancelledCount
                visible: cell.cancelledCount > 0
                color: Theme.crossIconColor
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.max(8, Math.round(cell.boxSize * 0.22))
            }
        }
    }
}

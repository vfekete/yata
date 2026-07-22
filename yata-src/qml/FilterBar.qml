import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

// Sub-toolbar combining three icon-prefixed button groups: Day/Month/Year
// (grouping), Active/Done/Cancel (visibility filters), and
// Manual/Active/Done/Cancel (taskModel.statusSortMode — previously its own
// OrderBar.qml row, merged in here per explicit request). Each group's icon
// is a static, non-clickable label (IconIndicator), not a control.
//
// Groups are laid out in a Flow (not a single RowLayout) so that as the
// window narrows, whole groups wrap to their own line instead of the row
// silently overflowing off the right edge: order wraps below day+visibility
// first, then visibility wraps below day too (leaving order on its own line
// beneath that) once day+visibility themselves don't fit side by side. Each
// group is its own inner RowLayout so it wraps as one unit — Flow itself has
// no concept of "keep these N children together".
Item {
    id: root
    implicitHeight: flow.implicitHeight + 4

    // Month/Year switch the content area to MonthView/YearView (Main.qml
    // reads these two properties to decide what to show instead of the task
    // ListView) — unlike Day, taskModel has no month/year-grouping concept
    // of its own, these are purely local UI state. All three are mutually
    // exclusive (at most one active at a time); activating any one clears
    // the other two, and the active one can be switched off entirely
    // (clicking it again turns it off, nothing turns back on — back to the
    // plain task list).
    property bool monthActive: false
    property bool yearActive: false

    function setGrouping(which, checked) {
        if (checked) {
            root.monthActive = (which === "month")
            root.yearActive = (which === "year")
            taskModel.setGroupByDay(which === "day")
        } else if (which === "day") {
            taskModel.setGroupByDay(false)
        } else if (which === "month") {
            root.monthActive = false
        } else {
            root.yearActive = false
        }
    }

    // Background doubles as drag handle — same pattern as Toolbar.
    MouseArea {
        anchors.fill: parent
        onPressed: Window.window.startSystemMove()
    }

    // 8px at the default 14px task font — scaled with it (via Ctrl+=/Ctrl+-
    // font zoom) so the gap stays proportional instead of a fixed pixel
    // amount that looks progressively wider as the surrounding text shrinks.
    readonly property int buttonSpacing: Math.round(Theme.taskFontPixelSize * 8 / 14)
    // Gap between the three button groups (both side-by-side and, once
    // wrapped, between lines — Flow uses a single spacing for both axes).
    readonly property int groupGap: Math.round(Theme.taskFontPixelSize * 18 / 14)

    Flow {
        id: flow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: root.groupGap

        // ── Day / Month / Year ───────────────────────────────────────────
        RowLayout {
            spacing: root.buttonSpacing
            IconIndicator { iconName: "calendar"; sizeScale: 0.9 }
            FilterButton {
                label: "Day"
                active: taskModel.groupByDay
                onToggled: (checked) => root.setGrouping("day", checked)
            }
            FilterButton {
                label: "Month"
                active: root.monthActive
                onToggled: (checked) => root.setGrouping("month", checked)
            }
            FilterButton {
                label: "Year"
                active: root.yearActive
                onToggled: (checked) => root.setGrouping("year", checked)
            }
        }

        // ── Active / Done / Cancel (visibility filters) ─────────────────
        RowLayout {
            spacing: root.buttonSpacing
            IconIndicator { iconName: "visibility"; sizeScale: 0.9 }
            FilterButton {
                label: "Active"
                active: taskModel.showActive
                onToggled: (checked) => taskModel.setShowActive(checked)
            }
            FilterButton {
                label: "Done"
                active: taskModel.showDone
                onToggled: (checked) => taskModel.setShowDone(checked)
            }
            FilterButton {
                label: "Cancel"
                active: taskModel.showCancelled
                onToggled: (checked) => taskModel.setShowCancelled(checked)
            }
        }

        // ── Manual / Active / Done / Cancel (sort order) ────────────────
        // statusSortMode is single-valued (""|"active"|"done"|"cancelled"),
        // so each button always selects its own value on tap rather than
        // toggling — clicking the already-active one is a harmless no-op.
        RowLayout {
            spacing: root.buttonSpacing
            IconIndicator { iconName: "order"; sizeScale: 0.9 }
            FilterButton {
                label: "Manual"
                active: taskModel.statusSortMode === ""
                onToggled: taskModel.setStatusSortMode("")
            }
            FilterButton {
                label: "Active"
                active: taskModel.statusSortMode === "active"
                onToggled: taskModel.setStatusSortMode("active")
            }
            FilterButton {
                label: "Done"
                active: taskModel.statusSortMode === "done"
                onToggled: taskModel.setStatusSortMode("done")
            }
            FilterButton {
                label: "Cancel"
                active: taskModel.statusSortMode === "cancelled"
                onToggled: taskModel.setStatusSortMode("cancelled")
            }
        }
    }
}

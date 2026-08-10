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

    // Month/Year/Links/Yatas switch the content area to MonthView/YearView/
    // LinksView/YatasView (Main.qml reads these properties to decide what to
    // show instead of the task ListView) — unlike Day, taskModel has no
    // month/year/links/yatas-grouping concept of its own, these are purely
    // local UI state. All five (Day/Month/Year/Links/Yatas) are mutually
    // exclusive (at most one active at a time); activating any one clears
    // the other four, and the active one can be switched off entirely
    // (clicking it again turns it off, nothing turns back on — back to the
    // plain task list). Links'/Yatas' own toggle buttons live in
    // Toolbar.qml, not here (see Main.qml for how the components are wired
    // together), but the mutual-exclusivity state and logic stays
    // centralized in this one function regardless of which component's
    // button triggered it.
    property bool monthActive: false
    property bool yearActive: false
    property bool linksActive: false
    property bool yatasActive: false

    // YatasView's own visibility/order state (r-3.md follow-up: ACTIVE/
    // DELETED categories for windows) — purely local UI state, same as
    // monthActive/yearActive above, not persisted. Lives here rather than
    // on YatasView itself so this bar's own ACTIVE/DELETED buttons (below)
    // can bind directly to it, then Main.qml relays it down into YatasView
    // the same way it already relays toolbar.searchText into LinksView/
    // YatasView. Deliberately mirrors taskModel's showActive/showDone/
    // showCancelled + statusSortMode shape: showX are independent toggles
    // (both can be on at once, showing both categories together in one
    // list), sortMode is single-valued and picks which category (if both
    // are visible) is sorted to the top — same "insert after" instinct as
    // task ordering, just with two categories instead of three and no
    // "Manual" entry (there are always exactly the same two buttons in both
    // rows here, per explicit request).
    property bool yatasShowActive: true
    property bool yatasShowDeleted: false
    property string yatasSortMode: ""

    // r-6.md: true while NoteEditorView is the actually-visible content
    // (set from Main.qml's noteEditorVisible) — disables (not hides) the
    // whole Flow below, per explicit request ("calendar, visibility and
    // ordering sub-toolbar actions are disabled"). Links/Yatas toggle
    // buttons live in the separate Toolbar.qml and are deliberately never
    // touched by this — they stay clickable so the note editor can be
    // covered/uncovered without losing in-progress edits (see Main.qml).
    property bool subToolbarDisabled: false

    function setGrouping(which, checked) {
        if (checked) {
            root.monthActive = (which === "month")
            root.yearActive = (which === "year")
            root.linksActive = (which === "links")
            root.yatasActive = (which === "yatas")
            taskModel.setGroupByDay(which === "day")
        } else if (which === "day") {
            taskModel.setGroupByDay(false)
        } else if (which === "month") {
            root.monthActive = false
        } else if (which === "year") {
            root.yearActive = false
        } else if (which === "links") {
            root.linksActive = false
        } else {
            root.yatasActive = false
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
        enabled: !root.subToolbarDisabled
        opacity: root.subToolbarDisabled ? 0.4 : 1.0

        // ── Day / Month / Year ───────────────────────────────────────────
        // Hidden entirely while Yatas is active — a window list has no
        // calendar/date concept to group by.
        RowLayout {
            visible: !root.yatasActive
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

        // ── Active / Done / Cancel (visibility filters) ─────────────────
        RowLayout {
            visible: !root.yatasActive
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

        // ── Active / Deleted (Yatas visibility filters) ──────────────────
        // Same independent-toggle mechanic as the task visibility group
        // above, just two categories instead of three: both can be shown
        // together (YatasView then uses yatasSortMode below to decide which
        // one sorts first), or either can be hidden entirely.
        RowLayout {
            visible: root.yatasActive
            spacing: root.buttonSpacing
            IconIndicator { iconName: "visibility"; sizeScale: 0.9 }
            FilterButton {
                label: qsTr("Active")
                active: root.yatasShowActive
                onToggled: (checked) => root.yatasShowActive = checked
            }
            FilterButton {
                label: qsTr("Deleted")
                active: root.yatasShowDeleted
                onToggled: (checked) => root.yatasShowDeleted = checked
            }
        }

        // ── Manual / Active / Done / Cancel (sort order) ────────────────
        // statusSortMode is single-valued (""|"active"|"done"|"cancelled"),
        // so each button always selects its own value on tap rather than
        // toggling — clicking the already-active one is a harmless no-op.
        RowLayout {
            visible: !root.yatasActive
            spacing: root.buttonSpacing
            IconIndicator { iconName: "order"; sizeScale: 0.9 }
            FilterButton {
                label: qsTr("Manual")
                active: taskModel.statusSortMode === ""
                onToggled: taskModel.setStatusSortMode("")
            }
            FilterButton {
                label: qsTr("Active")
                active: taskModel.statusSortMode === "active"
                onToggled: taskModel.setStatusSortMode("active")
            }
            FilterButton {
                label: qsTr("Done")
                active: taskModel.statusSortMode === "done"
                onToggled: taskModel.setStatusSortMode("done")
            }
            FilterButton {
                label: qsTr("Cancel")
                active: taskModel.statusSortMode === "cancelled"
                onToggled: taskModel.setStatusSortMode("cancelled")
            }
        }

        // ── Active / Deleted (Yatas sort order) ──────────────────────────
        // Same two options as the Yatas visibility group above (per
        // explicit request — no extra "Manual" entry the way the task order
        // group has one). Single-valued and radio-style like statusSortMode:
        // picks which category sorts first when both are visible at once;
        // tapping the already-selected one clears it back to no override
        // (there's no separate "Manual" button to do that with here).
        RowLayout {
            visible: root.yatasActive
            spacing: root.buttonSpacing
            IconIndicator { iconName: "order"; sizeScale: 0.9 }
            FilterButton {
                label: qsTr("Active")
                active: root.yatasSortMode === "active"
                onToggled: (checked) => root.yatasSortMode = checked ? "active" : ""
            }
            FilterButton {
                label: qsTr("Deleted")
                active: root.yatasSortMode === "deleted"
                onToggled: (checked) => root.yatasSortMode = checked ? "deleted" : ""
            }
        }
    }
}

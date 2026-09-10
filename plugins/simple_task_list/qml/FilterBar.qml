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

    // Month/Year/Links switch the content area to MonthView/YearView/
    // LinksView (Main.qml reads these properties to decide what to show
    // instead of the task ListView) — unlike Day, taskModel has no
    // month/year/links-grouping concept of its own, these are purely local
    // UI state. All four (Day/Month/Year/Links) are mutually exclusive (at
    // most one active at a time); activating any one clears the other
    // three, and the active one can be switched off entirely (clicking it
    // again turns it off, nothing turns back on — back to the plain task
    // list). Links' own toggle button lives in Toolbar.qml, not here (see
    // Main.qml for how the components are wired together), but the mutual-
    // exclusivity state and logic stays centralized in this one function
    // regardless of which component's button triggered it.
    //
    // Window management ("Yatas" here previously) moved to host chrome —
    // see yata-src/qml/YatasView.qml's own header — so it's no longer part
    // of this grouping at all.
    property bool monthActive: false
    property bool yearActive: false
    property bool linksActive: false

    // r-6.md: true while NoteEditorView is the actually-visible content
    // (set from Main.qml's noteEditorVisible) — disables (not hides) the
    // whole Flow below, per explicit request ("calendar, visibility and
    // ordering sub-toolbar actions are disabled"). Links' toggle button
    // lives in the separate Toolbar.qml and is deliberately never touched
    // by this — it stays clickable so the note editor can be covered/
    // uncovered without losing in-progress edits (see Main.qml).
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

        // ── Active / Done / Cancel (visibility filters) ─────────────────
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

        // ── Active / Done / Cancel (sort order) ──────────────────────────
        // r-7.md: no more separate "Manual" button — statusSortMode is
        // still single-valued (""|"active"|"done"|"cancelled"), but each of
        // these three now toggles (tapping the already-active one clears
        // back to "", i.e. Manual) instead of always selecting its own
        // value. Disabled (not hidden) during Month/Year: those views have
        // no per-task order for this to apply to (spec: "ordering has no
        // meaning and cannot be changed"). Deliberately NOT done via plain
        // `enabled: false` on orderRow itself: an Item.enabled=false is
        // excluded from hit-testing entirely rather than "present but
        // inert", so the press/hover would simply fall through to whatever
        // is BEHIND it in the z-stack — here, this whole bar's own
        // background MouseArea (above, "doubles as drag handle") — letting
        // a click-drag over these dimmed buttons drag the WHOLE WINDOW
        // around, and letting FilterButton's own HoverHandler still glow on
        // mouseover. Confirmed live as an actual reported bug. Fixed with
        // the same "enabled hover-claiming blocker stacked on top" idiom
        // already used for the glass lock's contentBlocker (Main.qml) —
        // orderBlocker below, not orderRow.enabled, is what's actually
        // disabled/enabled here.
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

            // While enabled, grabs and swallows every press/click/hover
            // over this group before orderRow's buttons OR this bar's own
            // background drag-handle MouseArea (behind everything, see
            // above) ever see it. While disabled, excluded from
            // hit-testing entirely, same as everywhere else this pattern
            // is used.
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

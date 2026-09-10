import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

// r-10.md: this plugin's whole content area — the work-time-tracker
// equivalent of simple_task_list's own TaskListContent.qml. Loaded into
// Main.qml's content Loader; same host-owned margins/contract that file
// documents (actionButtonsWidth/contentHovered/windowOpacity read back by
// Main.qml, zoom handled once generically there, window management
// entirely host chrome now).
//
// context properties this relies on (set by plugin.py's create_content):
// timesheetModel, appSettings (TimesheetSettings), holidaysProvider,
// Theme, iconProvider, windowManager, windowId, hostSettings.
Item {
    id: contentRoot
    anchors.fill: parent

    readonly property alias actionButtonsWidth: menuRow.implicitWidth
    readonly property alias contentHovered: contentHoverHandler.hovered
    readonly property real windowOpacity: Theme.windowOpacity

    // "" (no period selected) shows the work-item list; otherwise the
    // summary view replaces it wholesale — spec: "at most one can be
    // selected, if selected, work items list is replaced by the summary."
    property string activePeriod: ""
    property date summaryReferenceDate: new Date()

    // Holidays for the year(s) the current summary period could touch —
    // a week/month can straddle a year boundary, so all three of
    // (year-1, year, year+1) are merged rather than just the reference
    // year alone. Cheap after the first fetch: holidaysProvider caches to
    // disk per (country, year) already.
    readonly property var holidayDates: {
        var merged = {}
        var y = contentRoot.summaryReferenceDate.getFullYear()
        for (var offset = -1; offset <= 1; offset++) {
            var yearHolidays = holidaysProvider.holidaysFor(appSettings.countryCode, y + offset)
            for (var key in yearHolidays)
                merged[key] = yearHolidays[key]
        }
        return merged
    }

    Component.onCompleted: {
        if (appSettings.countryCode === "")
            pdfSettingsDialog.openSettings()
    }

    // Same "sibling of the content, not a wrapping overlay Item" placement
    // TaskListContent.qml's own contentHoverHandler documents — a
    // HoverHandler declared on a SEPARATE Item stacked on top was
    // confirmed elsewhere in this app to exclusively claim hover and
    // block it from reaching rows/controls underneath; as a sibling
    // attached directly to contentRoot (this Item), it coexists correctly
    // with every child's own HoverHandler instead.
    HoverHandler {
        id: contentHoverHandler
    }

    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: pdfSettingsDialog.openSettings()
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            id: menuRow
            Layout.fillWidth: true
            spacing: 10

            Text {
                text: qsTr("ADD")
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                color: addHover.hovered ? Theme.effectiveGlowColor : Theme.textColor
                HoverHandler { id: addHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: {
                        contentRoot.activePeriod = ""
                        timesheetModel.addItem()
                        itemsList.positionViewAtEnd()
                    }
                }
            }

            Item { Layout.preferredWidth: 12 }

            PeriodToggle {
                label: qsTr("Day")
                active: contentRoot.activePeriod === "day"
                onTapped: contentRoot.activePeriod = contentRoot.activePeriod === "day" ? "" : "day"
            }
            PeriodToggle {
                label: qsTr("Week")
                active: contentRoot.activePeriod === "week"
                onTapped: contentRoot.activePeriod = contentRoot.activePeriod === "week" ? "" : "week"
            }
            PeriodToggle {
                label: qsTr("Month")
                active: contentRoot.activePeriod === "month"
                onTapped: contentRoot.activePeriod = contentRoot.activePeriod === "month" ? "" : "month"
            }
            PeriodToggle {
                label: qsTr("Year")
                active: contentRoot.activePeriod === "year"
                onTapped: contentRoot.activePeriod = contentRoot.activePeriod === "year" ? "" : "year"
            }

            Item { Layout.fillWidth: true }

            Text {
                text: qsTr("EXPORT")
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                color: exportHover.hovered ? Theme.effectiveGlowColor : Theme.textColor
                HoverHandler { id: exportHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: exportDialog.openFor(
                        contentRoot.activePeriod === "" ? "month" : contentRoot.activePeriod,
                        contentRoot.summaryReferenceDate, contentRoot.holidayDates,
                        appSettings.defaultDailyHours)
                }
            }

            Text {
                text: "⚙"
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
                color: settingsHover.hovered ? Theme.effectiveGlowColor : Theme.textColor
                HoverHandler { id: settingsHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: pdfSettingsDialog.openSettings() }
            }
        }

        ListView {
            id: itemsList
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: contentRoot.activePeriod === ""
            clip: true
            model: timesheetModel
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: WorkItemRow {
                // itemId/name/nonWorking/running/durationLabel are all
                // declared as `required property` on WorkItemRow.qml's own
                // root already, and auto-populated straight from
                // timesheetModel's role names (itemId/name/nonWorking/
                // running/durationLabel) — same "no wrapper, no manual
                // mapping needed" pattern TaskDelegate.qml already
                // established for TaskListModel's own roles. Only
                // hasAbandonedSession needs an explicit binding: it's
                // derived, not a model role.
                width: itemsList.width
                hasAbandonedSession: {
                    var sessions = timesheetModel.sessionsFor(itemId)
                    for (var i = 0; i < sessions.length; i++)
                        if (sessions[i].abandoned) return true
                    return false
                }

                onRenamed: (itemId, newName) => timesheetModel.renameItem(itemId, newName)
                onStartRequested: (itemId) => timesheetModel.startItem(itemId)
                onStopRequested: (itemId) => timesheetModel.stopItem(itemId)
                onDeleteRequested: (itemId, name) => {
                    if (name === "")
                        timesheetModel.deleteItem(itemId)  // abandoned, never-named ADD -- no confirmation needed
                    else
                        deleteDialog.openFor(itemId, name)
                }
                onNonWorkingToggled: (itemId, nonWorking) => timesheetModel.setNonWorking(itemId, nonWorking)
                onSessionsRequested: (itemId) => sessionsDialog.openFor(itemId, name)
            }

            Text {
                anchors.centerIn: parent
                visible: timesheetModel.rowCount() === 0
                text: qsTr("No work items yet -- click ADD to create one")
                color: Theme.mutedTextColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
        }

        SummaryView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            visible: contentRoot.activePeriod !== ""
            period: contentRoot.activePeriod === "" ? "day" : contentRoot.activePeriod
            holidayDates: contentRoot.holidayDates
            dailyHours: appSettings.defaultDailyHours
            referenceDate: contentRoot.summaryReferenceDate
            onReferenceDateChanged: contentRoot.summaryReferenceDate = referenceDate
        }
    }

    DeleteWorkItemDialog {
        id: deleteDialog
        onConfirmed: (itemId) => timesheetModel.deleteItem(itemId)
    }

    SessionsDialog {
        id: sessionsDialog
    }

    PdfSettingsDialog {
        id: pdfSettingsDialog
    }

    ExportPdfDialog {
        id: exportDialog
        onExportFailed: exportFailedNotice.visible = true
        onExportSucceeded: exportFailedNotice.visible = false
    }

    Text {
        id: exportFailedNotice
        visible: false
        anchors.bottom: parent.bottom
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.bottomMargin: 8
        text: qsTr("Export failed -- check the destination is writable")
        color: Theme.abandonedColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }
}

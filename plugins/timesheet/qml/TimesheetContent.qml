import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
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
// "Bug wave 1" (r-10.md follow-up) asked this to copy as much of
// simple_task_list's own UI/UX as possible: two header rows — an upper
// menu (ADD/EXPORT/SETTINGS/search, mirroring Toolbar.qml) and a
// sub-toolbar (the period selector, mirroring FilterBar.qml's own
// icon-prefixed button groups) — rather than one flat row.
//
// context properties this relies on (set by plugin.py's create_content):
// timesheetModel, appSettings (TimesheetSettings), holidaysProvider,
// Theme, iconProvider, windowManager, windowId, hostSettings.
Item {
    id: contentRoot
    anchors.fill: parent

    // Sum of ONLY the fixed-width buttons plus the spacing between them —
    // same technique Toolbar.qml's own actionButtonsWidth uses — NOT
    // upperMenu.implicitWidth (tried first): a RowLayout's own
    // implicitWidth folds in its fillWidth child's own preferred size
    // too, so it included the search field's own natural width and
    // inflated Main.qml's minimumWidth (2x this) far past what the fixed
    // buttons alone actually need — confirmed live: the window couldn't
    // shrink nearly as small as Simple Task List's own, despite having
    // fewer buttons.
    readonly property real actionButtonsWidth: addButton.width + exportButton.width + settingsButton.width + upperMenu.spacing * 2
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

    function openExportDialog() {
        exportDialog.openFor(
            contentRoot.activePeriod === "" ? "month" : contentRoot.activePeriod,
            contentRoot.summaryReferenceDate, contentRoot.holidayDates,
            appSettings.defaultDailyHours)
    }

    // First-run country prompt: opens the (now comprehensive) export
    // dialog the first time this window's countryCode comes back empty
    // (system locale was unset/C/POSIX, so there was nothing to default
    // to) — same dialog the EXPORT button and SETTINGS menu's own
    // "Export..." item open, since customer/contractor/country/PDF-part
    // settings now all live there together (see ExportPdfDialog.qml's
    // own header for why they were merged in).
    Component.onCompleted: {
        if (appSettings.countryCode === "")
            contentRoot.openExportDialog()
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

    ColumnLayout {
        anchors.fill: parent
        spacing: 4

        // ── Upper menu (mirrors Toolbar.qml) ─────────────────────────────
        RowLayout {
            id: upperMenu
            Layout.fillWidth: true
            spacing: 10

            Text {
                id: addButton
                text: qsTr("ADD")
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                color: addHover.hovered ? Theme.effectiveGlowColor : Theme.textColor
                HoverHandler { id: addHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    // Behaves the same as STP's own ADD (explicit
                    // follow-up request): switches back to the item list
                    // if a summary is showing, then creates a new,
                    // still-unnamed item that WorkItemRow.qml's own
                    // nameField immediately focuses for typing.
                    onTapped: {
                        contentRoot.activePeriod = ""
                        timesheetModel.addItem()
                        itemsList.positionViewAtEnd()
                    }
                }
            }

            Text {
                id: exportButton
                text: qsTr("EXPORT")
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                color: exportHover.hovered ? Theme.effectiveGlowColor : Theme.textColor
                HoverHandler { id: exportHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: contentRoot.openExportDialog() }
            }

            Text {
                id: settingsButton
                text: qsTr("SETTINGS")
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.capitalization: Font.AllUppercase
                color: settingsHover.hovered ? Theme.effectiveGlowColor : Theme.textColor
                HoverHandler { id: settingsHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: settingsMenu.popup() }

                Menu {
                    id: settingsMenu

                    MenuItem {
                        text: qsTr("Export...")
                        padding: 10
                        onTriggered: contentRoot.openExportDialog()
                    }

                    MenuSeparator {}

                    // "Co" = a filled circle in the currently-picked
                    // color, right after the label — explicit spec
                    // wording ("'Co' part of the text represents
                    // 'C'olor circle").
                    MenuItem {
                        padding: 10
                        onTriggered: ongoingColorDialog.open()
                        contentItem: RowLayout {
                            spacing: 8
                            Text {
                                Layout.fillWidth: true
                                text: qsTr("Ongoing color")
                                color: Theme.textColor
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.taskFontPixelSize
                            }
                            Rectangle {
                                width: Theme.taskFontPixelSize
                                height: Theme.taskFontPixelSize
                                radius: width / 2
                                color: Theme.ongoingColor
                            }
                        }
                    }
                    MenuItem {
                        padding: 10
                        onTriggered: abandonedColorDialog.open()
                        contentItem: RowLayout {
                            spacing: 8
                            Text {
                                Layout.fillWidth: true
                                text: qsTr("Abandoned color")
                                color: Theme.textColor
                                font.family: Theme.fontFamily
                                font.pixelSize: Theme.taskFontPixelSize
                            }
                            Rectangle {
                                width: Theme.taskFontPixelSize
                                height: Theme.taskFontPixelSize
                                radius: width / 2
                                color: Theme.abandonedColor
                            }
                        }
                    }
                }

                ColorDialog {
                    id: ongoingColorDialog
                    title: qsTr("Ongoing color")
                    selectedColor: Theme.ongoingColor
                    onAccepted: appSettings.ongoingColor = selectedColor.toString()
                }
                ColorDialog {
                    id: abandonedColorDialog
                    title: qsTr("Abandoned color")
                    selectedColor: Theme.abandonedColor
                    onAccepted: appSettings.abandonedColor = selectedColor.toString()
                }
            }

            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: qsTr("Search for item")
                placeholderTextColor: Theme.mutedTextColor
                leftPadding: searchIcon.width + 12
                rightPadding: clearIcon.width + 14
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                onTextChanged: timesheetModel.setSearchText(text)
                background: Rectangle {
                    radius: 4
                    color: Theme.fieldColor
                }

                Image {
                    id: searchIcon
                    source: iconProvider.coloredSvgUri("search", Theme.mutedTextColor.toString())
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    height: Math.round(Theme.taskFontPixelSize * 1.15)
                    width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                    anchors.left: parent.left
                    anchors.leftMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                }

                Text {
                    id: clearIcon
                    visible: searchField.text.length > 0
                    anchors.right: parent.right
                    anchors.rightMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                    text: "✕"
                    color: Theme.mutedTextColor

                    TapHandler { onTapped: searchField.text = "" }
                }
            }
        }

        // ── Sub-toolbar (mirrors FilterBar.qml) ──────────────────────────
        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            // Temporary placeholder, not a real icon (explicit follow-up
            // request — will be replaced by a proper icon from the nuon
            // project later): a static, non-interactive marker before the
            // DAY/WEEK/MONTH/YEAR group, same role IconIndicator.qml
            // plays before simple_task_list's own FilterBar button groups
            // (e.g. a calendar icon before its own Day/Month/Year set).
            Text {
                text: "Σ"
                color: Theme.mutedTextColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }

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
                // itemId/name/nonWorking/running/durationLabel/
                // hasAbandonedSession are all declared as `required
                // property` on WorkItemRow.qml's own root already, and
                // auto-populated straight from timesheetModel's matching
                // role names — same "no wrapper, no manual mapping
                // needed" pattern TaskDelegate.qml already established
                // for TaskListModel's own roles.
                width: itemsList.width

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
                // itemsList.count, NOT timesheetModel.rowCount() -- the
                // latter is a plain method call, invisible to QML's
                // binding dependency tracker (same class of bug as the
                // ComboBox.currentIndex one fixed in YatasView.qml this
                // session), so this stayed permanently "true" the moment
                // it was first evaluated regardless of later additions.
                // ListView.count is a real, change-notifying property.
                visible: itemsList.count === 0
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

    ExportPdfDialog {
        id: exportDialog
        onPeriodChosen: (period, referenceDate, holidayDates, dailyHours) => {
            pdfFileDialog._period = period
            pdfFileDialog._referenceDate = referenceDate
            pdfFileDialog._holidayDates = holidayDates
            pdfFileDialog._dailyHours = dailyHours
            pdfFileDialog.open()
        }
    }

    // Declared here (a plain Item's own child), NOT nested inside
    // ExportPdfDialog (a separate top-level Window in its own right, see
    // DialogWindow.qml) — confirmed as the actual cause of "timesheet is
    // not exported": nesting a FileDialog inside another custom Window-
    // based dialog is a Window-within-a-Window arrangement nothing else
    // in this codebase uses, unlike the one proven-working precedent
    // (YatasRow.qml's own ColorDialog, declared directly inside its
    // window's own content, not inside another dialog window). Moved
    // here to match that pattern instead of guessing further at the
    // native/portal-dialog specifics.
    FileDialog {
        id: pdfFileDialog
        property string _period: "month"
        property date _referenceDate: new Date()
        property var _holidayDates: ({})
        property real _dailyHours: 8.0

        fileMode: FileDialog.SaveFile
        nameFilters: [qsTr("PDF files (*.pdf)")]
        defaultSuffix: "pdf"
        onAccepted: {
            var path = String(selectedFile).replace(/^file:\/\//, "")
            var ok = timesheetModel.exportPdf(
                path, pdfFileDialog._period, Qt.formatDate(pdfFileDialog._referenceDate, "yyyy-MM-dd"),
                pdfFileDialog._holidayDates, pdfFileDialog._dailyHours,
                {
                    customerName: appSettings.customerName,
                    customerAddress: appSettings.customerAddress,
                    contractorName: appSettings.contractorName,
                    includeCustomer: appSettings.pdfIncludeCustomer,
                    includeContractor: appSettings.pdfIncludeContractor,
                    includeSignatures: appSettings.pdfIncludeSignatures,
                }
            )
            exportFailedNotice.visible = !ok
        }
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

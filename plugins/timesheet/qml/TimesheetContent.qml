import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

Item {
    id: contentRoot
    anchors.fill: parent

    readonly property real actionButtonsWidth: addButton.width + exportButton.width + settingsButton.width + upperMenu.spacing * 2
    readonly property alias contentHovered: contentHoverHandler.hovered
    readonly property real windowOpacity: Theme.windowOpacity

    property string activePeriod: ""
    property date summaryReferenceDate: new Date()

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

    Component.onCompleted: {
        if (appSettings.countryCode === "")
            contentRoot.openExportDialog()
    }

    HoverHandler {
        id: contentHoverHandler
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 4

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

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Image {
                id: summaryIcon
                Layout.preferredHeight: Math.round(Theme.taskFontPixelSize * 1.0)
                Layout.preferredWidth: implicitHeight > 0
                    ? Math.round(Layout.preferredHeight * implicitWidth / implicitHeight)
                    : Layout.preferredHeight
                fillMode: Image.PreserveAspectFit
                smooth: true
                source: iconProvider.coloredSvgUri("summary", Theme.mutedTextColor.toString())
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
                width: itemsList.width

                onRenamed: (itemId, newName) => timesheetModel.renameItem(itemId, newName)
                onStartRequested: (itemId) => timesheetModel.startItem(itemId)
                onStopRequested: (itemId) => timesheetModel.stopItem(itemId)
                onDeleteRequested: (itemId, name) => {
                    if (name === "")
                        timesheetModel.deleteItem(itemId)
                    else
                        deleteDialog.openFor(itemId, name)
                }
                onNonWorkingToggled: (itemId, nonWorking) => timesheetModel.setNonWorking(itemId, nonWorking)
                onSessionsRequested: (itemId) => sessionsDialog.openFor(itemId, name)
            }

            Text {
                anchors.centerIn: parent
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

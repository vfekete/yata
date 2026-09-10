import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts

// Period + destination picker for "Export to PDF" (spec: "per-day,
// per-week and per-month summary to PDF"). Uses whatever the summary
// view's own reference date/period currently is as the default, but the
// user can change either before exporting.
DialogWindow {
    id: root
    title: qsTr("Export to PDF")
    okText: qsTr("Export")

    property string period: "month"
    property date referenceDate: new Date()
    property var holidayDates: ({})
    property real dailyHours: 8.0

    signal exportFailed()
    signal exportSucceeded(string path)

    function openFor(period, referenceDate, holidayDates, dailyHours) {
        root.period = period
        root.referenceDate = referenceDate
        root.holidayDates = holidayDates
        root.dailyHours = dailyHours
        root.open()
    }

    onAccepted: fileDialog.open()

    FileDialog {
        id: fileDialog
        fileMode: FileDialog.SaveFile
        nameFilters: [qsTr("PDF files (*.pdf)")]
        defaultSuffix: "pdf"
        onAccepted: {
            var path = String(selectedFile).replace(/^file:\/\//, "")
            var ok = timesheetModel.exportPdf(
                path, root.period, Qt.formatDate(root.referenceDate, "yyyy-MM-dd"),
                root.holidayDates, root.dailyHours,
                {
                    customerName: appSettings.customerName,
                    customerAddress: appSettings.customerAddress,
                    contractorName: appSettings.contractorName,
                    includeCustomer: appSettings.pdfIncludeCustomer,
                    includeContractor: appSettings.pdfIncludeContractor,
                    includeSignatures: appSettings.pdfIncludeSignatures,
                }
            )
            if (ok) root.exportSucceeded(path)
            else root.exportFailed()
        }
    }

    RowLayout {
        Layout.fillWidth: true
        spacing: 6

        Label {
            text: qsTr("Period")
            color: Theme.mutedTextColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
        }
        ComboBox {
            Layout.fillWidth: true
            model: [qsTr("Day"), qsTr("Week"), qsTr("Month")]
            currentIndex: root.period === "day" ? 0 : root.period === "week" ? 1 : 2
            onActivated: root.period = ["day", "week", "month"][currentIndex]
        }
    }

    Label {
        Layout.fillWidth: true
        wrapMode: Text.Wrap
        text: qsTr("Exports the %1 containing %2, using the customer/contractor/PDF-part settings from Timesheet settings.")
            .arg(root.period).arg(Qt.formatDate(root.referenceDate, "yyyy-MM-dd"))
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.85)
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Period picker for "Export to PDF" (spec: "per-day, per-week and
// per-month summary to PDF"). Uses whatever the summary view's own
// reference date/period currently is as the default, but the user can
// change either before exporting. The actual file destination picker
// (FileDialog) lives one level up, in TimesheetContent.qml — NOT nested
// in here (tried first): a FileDialog nested inside this dialog's own
// Window (DialogWindow.qml is a real top-level Window, see its own
// header) is a Window-within-a-Window arrangement nothing else in this
// codebase uses, and was the actual cause of exports silently never
// happening. periodChosen fires once the user confirms the period here;
// TimesheetContent.qml is what actually opens the file picker and calls
// timesheetModel.exportPdf.
DialogWindow {
    id: root
    title: qsTr("Export to PDF")
    okText: qsTr("Export")

    property string period: "month"
    property date referenceDate: new Date()
    property var holidayDates: ({})
    property real dailyHours: 8.0

    signal periodChosen(string period, date referenceDate, var holidayDates, real dailyHours)

    function openFor(period, referenceDate, holidayDates, dailyHours) {
        root.period = period
        root.referenceDate = referenceDate
        root.holidayDates = holidayDates
        root.dailyHours = dailyHours
        root.open()
    }

    onAccepted: root.periodChosen(root.period, root.referenceDate, root.holidayDates, root.dailyHours)

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

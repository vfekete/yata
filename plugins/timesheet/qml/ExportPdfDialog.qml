import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Everything needed for "Export to PDF" in one place: period, customer/
// contractor identity, country (drives holiday lookup), default daily
// target hours, and which optional PDF parts to include — all per-window
// (r-10.md decision). Reachable three ways, all opening this same dialog:
// the top-level EXPORT button, SETTINGS menu's "Export..." item, and
// (as a first-run country prompt) TimesheetContent.qml's own
// Component.onCompleted the first time a window's countryCode comes back
// empty. Identity/PDF-part fields save immediately as they're edited
// (matching their own previous home, PdfSettingsDialog.qml, now merged
// in here); only "period" is threaded through periodChosen, once Export
// is actually clicked.
//
// The actual file destination picker (FileDialog) lives one level up, in
// TimesheetContent.qml — NOT nested in here: a FileDialog nested inside
// this dialog's own Window (DialogWindow.qml is a real top-level Window,
// see its own header) is a Window-within-a-Window arrangement nothing
// else in this codebase uses, and was the actual cause of exports
// silently never happening. periodChosen fires once the user confirms
// here; TimesheetContent.qml is what actually opens the file picker and
// calls timesheetModel.exportPdf.
DialogWindow {
    id: root
    title: qsTr("Export to PDF")
    okText: qsTr("Export")
    contentWidth: Math.max(380, Math.round(Theme.taskFontPixelSize * 28))

    property string period: "month"
    property date referenceDate: new Date()
    property var holidayDates: ({})
    property real dailyHours: 8.0
    property var countries: []  // [{code, name}] -- populated on open()

    signal periodChosen(string period, date referenceDate, var holidayDates, real dailyHours)

    function openFor(period, referenceDate, holidayDates, dailyHours) {
        root.period = period
        root.referenceDate = referenceDate
        root.holidayDates = holidayDates
        root.dailyHours = dailyHours
        root.countries = holidaysProvider.countries()
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
        text: qsTr("Country (for public holidays)")
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.85)
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 6

        ComboBox {
            id: countryCombo
            Layout.fillWidth: true
            model: root.countries
            textRole: "name"
            valueRole: "code"
            // A plain search over root.countries/appSettings.countryCode
            // directly, not indexOfValue(appSettings.countryCode) — the
            // latter's dependencies (this combo's own model/valueRole)
            // are invisible to QML's binding tracker, so the binding
            // would never re-evaluate once they settle into place
            // (confirmed live elsewhere this session: exactly this
            // shape left a ComboBox's currentIndex stuck at -1 forever).
            currentIndex: {
                for (var i = 0; i < root.countries.length; i++)
                    if (root.countries[i].code === appSettings.countryCode) return i
                return -1
            }
            onActivated: appSettings.countryCode = currentValue
        }

        Button {
            text: qsTr("Refresh holidays")
            onClicked: holidaysProvider.refreshHolidaysFor(appSettings.countryCode, new Date().getFullYear())
        }
    }

    Label {
        Layout.fillWidth: true
        Layout.topMargin: 8
        text: qsTr("Customer")
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.85)
    }
    TextField {
        Layout.fillWidth: true
        text: appSettings.customerName
        color: Theme.textColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
        background: Rectangle { radius: 4; color: Theme.fieldColor }
        onEditingFinished: appSettings.customerName = text
    }
    TextField {
        Layout.fillWidth: true
        placeholderText: qsTr("Customer address")
        text: appSettings.customerAddress
        color: Theme.textColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
        background: Rectangle { radius: 4; color: Theme.fieldColor }
        onEditingFinished: appSettings.customerAddress = text
    }

    Label {
        Layout.fillWidth: true
        Layout.topMargin: 8
        text: qsTr("Contractor (you)")
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.85)
    }
    TextField {
        Layout.fillWidth: true
        text: appSettings.contractorName
        color: Theme.textColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
        background: Rectangle { radius: 4; color: Theme.fieldColor }
        onEditingFinished: appSettings.contractorName = text
    }

    RowLayout {
        Layout.fillWidth: true
        Layout.topMargin: 8
        spacing: 6

        Label {
            text: qsTr("Default daily hours")
            color: Theme.mutedTextColor
            font.family: Theme.fontFamily
            font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.85)
        }
        SpinBox {
            from: 1
            to: 24
            value: Math.round(appSettings.defaultDailyHours)
            onValueModified: appSettings.defaultDailyHours = value
        }
    }

    Label {
        Layout.fillWidth: true
        Layout.topMargin: 8
        text: qsTr("Include in PDF export")
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.85)
    }
    CheckBox {
        text: qsTr("Customer header")
        checked: appSettings.pdfIncludeCustomer
        onToggled: appSettings.pdfIncludeCustomer = checked
    }
    CheckBox {
        text: qsTr("Contractor header")
        checked: appSettings.pdfIncludeContractor
        onToggled: appSettings.pdfIncludeContractor = checked
    }
    CheckBox {
        text: qsTr("Signature lines")
        checked: appSettings.pdfIncludeSignatures
        onToggled: appSettings.pdfIncludeSignatures = checked
    }
}

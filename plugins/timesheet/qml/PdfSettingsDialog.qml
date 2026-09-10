import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Customer/contractor identity, country (drives holiday lookup), default
// daily target hours, and which optional PDF parts to include — all
// per-window (r-10.md decision). Also doubles as the first-run country
// prompt: TimesheetContent.qml opens this automatically the first time a
// window's countryCode comes back empty (system locale was unset/C/POSIX,
// so there was nothing to default to).
DialogWindow {
    id: root
    title: qsTr("Timesheet settings")
    showCancel: false
    okText: qsTr("Done")
    contentWidth: Math.max(380, Math.round(Theme.taskFontPixelSize * 28))

    property var countries: []  // [{code, name}] -- populated on open()

    function openSettings() {
        root.countries = holidaysProvider.countries()
        root.open()
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
            Component.onCompleted: currentIndex = indexOfValue(appSettings.countryCode)
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

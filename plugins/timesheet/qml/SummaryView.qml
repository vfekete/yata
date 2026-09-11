import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root
    required property string period
    required property var holidayDates
    required property real dailyHours

    property date referenceDate: new Date()

    function _isoDate(d) {
        return Qt.formatDate(d, "yyyy-MM-dd")
    }

    readonly property var summaryData: timesheetModel.summary(
        root.period, root._isoDate(root.referenceDate), root.holidayDates, root.dailyHours)

    function shiftPeriod(direction) {
        var d = new Date(root.referenceDate)
        if (root.period === "day") d.setDate(d.getDate() + direction)
        else if (root.period === "week") d.setDate(d.getDate() + direction * 7)
        else if (root.period === "month") d.setMonth(d.getMonth() + direction)
        else if (root.period === "year") d.setFullYear(d.getFullYear() + direction)
        root.referenceDate = d
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Text {
                text: "◀"
                color: Theme.textColor
                font.pixelSize: Theme.taskFontPixelSize
                TapHandler { onTapped: root.shiftPeriod(-1) }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }

            Text {
                Layout.fillWidth: true
                horizontalAlignment: Text.AlignHCenter
                text: root.summaryData.start === root.summaryData.end
                    ? root.summaryData.start
                    : root.summaryData.start + " – " + root.summaryData.end
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                font.bold: true
            }

            Text {
                text: "▶"
                color: Theme.textColor
                font.pixelSize: Theme.taskFontPixelSize
                TapHandler { onTapped: root.shiftPeriod(1) }
                HoverHandler { cursorShape: Qt.PointingHandCursor }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 16

            Text {
                text: qsTr("Worked: %1").arg(root.summaryData.workedTotalLabel)
                color: Theme.textColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
            Text {
                text: qsTr("Target: %1").arg(root.summaryData.targetTotalLabel)
                color: Theme.mutedTextColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
            Text {
                visible: root.summaryData.overtimeLabel !== "0:00:00"
                text: qsTr("Overtime: %1").arg(root.summaryData.overtimeLabel)
                color: Theme.onSiteColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
            Text {
                visible: root.summaryData.overtimeLabel === "0:00:00"
                text: qsTr("Remaining: %1").arg(root.summaryData.remainingLabel)
                color: Theme.remoteColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
            }
        }

        ListView {
            id: daysList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: root.summaryData.days
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: Item {
                required property var modelData
                width: daysList.width
                height: dayRow.implicitHeight + 8

                RowLayout {
                    id: dayRow
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.verticalCenter: parent.verticalCenter
                    spacing: 10

                    Text {
                        Layout.preferredWidth: 110
                        text: modelData.date
                        color: modelData.isWorkingDay ? Theme.textColor : Theme.mutedTextColor
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.taskFontPixelSize
                    }
                    Text {
                        Layout.preferredWidth: 70
                        text: modelData.workedLabel
                        color: Theme.textColor
                        font.family: Theme.fontFamily
                        font.pixelSize: Theme.taskFontPixelSize
                    }
                    Text {
                        visible: modelData.isHoliday
                        Layout.fillWidth: true
                        text: modelData.holidayName
                        color: Theme.mutedTextColor
                        font.italic: true
                        font.family: Theme.fontFamily
                        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.85)
                        elide: Text.ElideRight
                    }
                    Item { visible: !modelData.isHoliday; Layout.fillWidth: true }

                    Text {
                        visible: modelData.location !== ""
                        text: modelData.location === "on-site" ? qsTr("ON-SITE")
                            : modelData.location === "remote" ? qsTr("REMOTE") : ""
                        color: modelData.location === "on-site" ? Theme.onSiteColor : Theme.remoteColor
                        font.family: Theme.fontFamily
                        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
                        font.capitalization: Font.AllUppercase
                    }
                }
            }
        }
    }
}

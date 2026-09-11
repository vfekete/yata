import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

DialogWindow {
    id: root
    title: qsTr("Sessions for “%1”").arg(root.itemName)
    showCancel: false
    okText: qsTr("Close")
    contentWidth: Math.max(420, Math.round(Theme.taskFontPixelSize * 32))

    property string itemId: ""
    property string itemName: ""
    property var sessions: []

    function openFor(id, name) {
        root.itemId = id
        root.itemName = name
        root.sessions = timesheetModel.sessionsFor(id)
        root.open()
    }

    function _toDisplay(iso) {
        if (!iso) return ""
        var d = new Date(iso)
        return Qt.formatDateTime(d, "yyyy-MM-dd HH:mm")
    }
    function _toIso(display) {
        var d = Date.fromLocaleString(Qt.locale(), display, "yyyy-MM-dd HH:mm")
        return isNaN(d.getTime()) ? null : d.toISOString()
    }

    Label {
        Layout.fillWidth: true
        visible: root.sessions.length === 0
        text: qsTr("No sessions yet.")
        color: Theme.mutedTextColor
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }

    ListView {
        Layout.fillWidth: true
        Layout.preferredHeight: Math.min(300, contentHeight)
        visible: root.sessions.length > 0
        clip: true
        model: root.sessions
        spacing: 6
        ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

        delegate: ColumnLayout {
            id: sessionRow
            required property var modelData
            width: ListView.view.width
            spacing: 2

            RowLayout {
                Layout.fillWidth: true
                spacing: 6

                TextField {
                    id: startField
                    Layout.fillWidth: true
                    text: root._toDisplay(sessionRow.modelData.start)
                    color: Theme.textColor
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.9)
                    background: Rectangle { radius: 4; color: Theme.fieldColor }
                    onEditingFinished: sessionRow.commit()
                }

                Text {
                    text: "→"
                    color: Theme.mutedTextColor
                    font.pixelSize: Theme.taskFontPixelSize
                }

                TextField {
                    id: stopField
                    Layout.fillWidth: true
                    text: root._toDisplay(sessionRow.modelData.stop)
                    placeholderText: qsTr("(running)")
                    color: Theme.textColor
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.9)
                    background: Rectangle { radius: 4; color: Theme.fieldColor }
                    onEditingFinished: sessionRow.commit()
                }
            }

            Text {
                visible: sessionRow.modelData.abandoned
                text: qsTr("⚠ abandoned -- stop time was auto-set; edit it to clear this flag")
                color: Theme.abandonedColor
                font.family: Theme.fontFamily
                font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.7)
            }

            function commit() {
                var startIso = root._toIso(startField.text)
                var stopIso = stopField.text.length === 0 ? "" : root._toIso(stopField.text)
                if (startIso === null || (stopField.text.length > 0 && stopIso === null))
                    return
                timesheetModel.updateSession(root.itemId, sessionRow.modelData.id, startIso, stopIso)
                sessionRow.modelData = Object.assign({}, sessionRow.modelData, {
                    start: startIso, stop: stopIso, abandoned: false
                })
            }
        }
    }
}

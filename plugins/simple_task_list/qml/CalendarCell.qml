import QtQuick
import QtQuick.Layouts

Rectangle {
    id: cell
    property string label: ""
    property int activeCount: 0
    property int doneCount: 0
    property int cancelledCount: 0
    property bool valid: true
    signal clicked()

    color: !valid ? "transparent" : (hh.hovered ? Theme.hoverColor : Theme.fieldColor)
    radius: 4
    border.width: valid ? 1 : 0
    border.color: Theme.borderColor

    HoverHandler { id: hh; enabled: cell.valid; cursorShape: Qt.PointingHandCursor }
    TapHandler { enabled: cell.valid; onTapped: cell.clicked() }

    readonly property real boxSize: Math.min(width, height)

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 4
        spacing: 2
        visible: cell.valid

        Text {
            text: cell.label
            font.bold: true
            font.family: Theme.fontFamily
            font.pixelSize: Math.max(8, Math.round(cell.boxSize * 0.18))
            color: Theme.textColor
        }

        Item { Layout.fillHeight: true }

        RowLayout {
            spacing: 8
            Text {
                text: cell.activeCount
                visible: cell.activeCount > 0
                color: Theme.textColor
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.max(8, Math.round(cell.boxSize * 0.22))
            }
            Text {
                text: cell.doneCount
                visible: cell.doneCount > 0
                color: Theme.checkIconColor
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.max(8, Math.round(cell.boxSize * 0.22))
            }
            Text {
                text: cell.cancelledCount
                visible: cell.cancelledCount > 0
                color: Theme.crossIconColor
                font.bold: true
                font.family: Theme.fontFamily
                font.pixelSize: Math.max(8, Math.round(cell.boxSize * 0.22))
            }
        }
    }
}

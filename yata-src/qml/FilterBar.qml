import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

Item {
    id: root
    implicitHeight: row.implicitHeight + 6

    // Background doubles as drag handle — same pattern as Toolbar.
    MouseArea {
        anchors.fill: parent
        onPressed: Window.window.startSystemMove()
    }

    // Toggle button: ON state looks identical to hover (cyan glow + #00FFFF
    // text) so toggled state is unmistakable regardless of theme palette.
    component FilterButton : Item {
        id: btn
        property string label: ""
        property bool active: true
        signal toggled(bool newChecked)

        implicitWidth: lbl.implicitWidth + 8
        implicitHeight: lbl.implicitHeight + 2

        HoverHandler { id: bh; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: btn.toggled(!btn.active) }

        Text {
            id: lbl
            anchors.centerIn: parent
            text: btn.label
            font.family: Theme.fontFamily
            font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.8)
            font.capitalization: Font.AllUppercase
            color: bh.hovered ? Theme.filterHoverColor : (btn.active ? Theme.filterGlowColor : Theme.mutedTextColor)
            layer.enabled: bh.hovered || btn.active
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: bh.hovered ? Theme.filterHoverColor : Theme.filterGlowColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
        }
    }

    RowLayout {
        id: row
        anchors.fill: parent
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: 10

        FilterButton {
            label: "Day"
            active: taskModel.groupByDay
            onToggled: (checked) => taskModel.setGroupByDay(checked)
        }
        FilterButton {
            label: "Active"
            active: taskModel.showActive
            onToggled: (checked) => taskModel.setShowActive(checked)
        }
        FilterButton {
            label: "Done"
            active: taskModel.showDone
            onToggled: (checked) => taskModel.setShowDone(checked)
        }
        FilterButton {
            label: "Cancelled"
            active: taskModel.showCancelled
            onToggled: (checked) => taskModel.setShowCancelled(checked)
        }

        Item { Layout.fillWidth: true }
    }
}

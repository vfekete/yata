import QtQuick
import QtQuick.Effects

Row {
    id: root
    property string status: "active"
    property string completedAt: ""
    spacing: 0

    readonly property color tagColor: {
        if (status === "done") return Theme.completedDoneLabelColor
        if (status === "cancelled") return Theme.completedCancelledLabelColor
        return Theme.activeTagColor
    }

    Text {
        id: statusText
        textFormat: Text.PlainText
        text: root.status === "done" ? qsTr("DONE") : root.status === "cancelled" ? qsTr("CANCELED") : qsTr("ACTIVE")
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
        color: root.tagColor
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: root.tagColor
            shadowBlur: 1.0
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0
            shadowOpacity: 1.0
            shadowScale: 1.05
        }
    }

    Text {
        visible: root.status !== "active" && root.completedAt !== ""
        textFormat: Text.PlainText
        text: {
            if (root.completedAt === "") return ""
            var dt = new Date(root.completedAt)
            var dd = String(dt.getDate()).padStart(2, '0')
            var mm = String(dt.getMonth() + 1).padStart(2, '0')
            var HH = String(dt.getHours()).padStart(2, '0')
            var MM = String(dt.getMinutes()).padStart(2, '0')
            return " [" + dd + "-" + mm + "-" + dt.getFullYear() + " " + HH + ":" + MM + "]"
        }
        font.family: Theme.fontFamily
        font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
        color: root.status === "done" ? Theme.doneColor : Theme.cancelledColor
    }
}

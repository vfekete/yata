import QtQuick
import QtQuick.Effects

// Status tag used by LinksView's rows: colored status word + glow, plus a
// timestamp for done/cancelled. Mirrors TaskDelegate.qml's existing
// completedLabel Row (kept as-is there, per explicit decision not to change
// the main task list), extended with an "active" case — every Links row
// needs a status indicator since, unlike the main list, there's no
// strikethrough/muted-text to convey status instead.
Row {
    id: root
    property string status: "active"  // "active" | "done" | "cancelled"
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
        text: root.status === "done" ? "DONE" : root.status === "cancelled" ? "CANCELED" : "ACTIVE"
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

    // No timestamp for "active" — spec: "doesn't have timestamp, just status".
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

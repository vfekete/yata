import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

// Confirmation dialog for deleting a YATA window from YatasView, per
// r-3.md: must be theme-colored but NOT affected by the opacity slider.
// The "not opacity" part comes for free — Dialog/Popup content renders in
// the Window's Overlay layer, outside the opacity-affected content wrapper
// Item in Main.qml (same reason ThemeMenu's popups already ignore opacity;
// see Main.qml's own comment on that wrapper).
Dialog {
    id: root
    modal: true
    title: "Delete window?"
    font.pixelSize: Theme.taskFontPixelSize
    standardButtons: Dialog.Ok | Dialog.Cancel
    // Scales with font zoom like every other sized-by-font element in this
    // app (e.g. ThemeMenu's width) — a fixed pixel width didn't grow with
    // Ctrl+=/Ctrl+- zoom, so at a larger zoom the text ran right up to (and
    // past) the dialog's edges.
    width: Math.max(300, Math.round(Theme.taskFontPixelSize * 26))

    property string targetId: ""
    property string targetTag: ""
    signal confirmed(string windowId, bool deleteData)

    function openFor(windowId, tag) {
        root.targetId = windowId
        root.targetTag = tag
        deleteDataCheck.checked = false
        root.open()
    }

    onAccepted: root.confirmed(root.targetId, deleteDataCheck.checked)

    // "none" theme's contentBackground is literally "transparent" (the main
    // window's wash is a translucent Rectangle underneath it) — a dialog
    // needs a real solid color to stay readable, same fallback Main.qml's
    // own bottom gradient overlay already uses for the same reason.
    background: Rectangle {
        radius: 4
        color: Theme.tintName === "none"
               ? (Theme.dark ? "#111827" : "#f9fafb")
               : Theme.contentBackground
        border.color: Theme.borderColor
        border.width: 1
    }

    header: Label {
        text: root.title
        color: Theme.textColor
        font.bold: true
        font.pixelSize: Theme.taskFontPixelSize * 1.2
        padding: 12
    }

    ColumnLayout {
        width: parent.width
        spacing: 10

        Label {
            Layout.fillWidth: true
            wrapMode: Text.Wrap
            text: "Are you sure you want to delete “" + root.targetTag + "”?"
            color: Theme.textColor
            font.pixelSize: Theme.taskFontPixelSize
        }

        Label {
            text: "This action cannot be undone."
            color: Theme.mutedTextColor
            font.pixelSize: Theme.taskFontPixelSize
        }

        // A plain CheckBox (default indicator, no custom contentItem) next
        // to its own label, rather than putting the label in CheckBox's
        // contentItem — that fought the Basic style's own indicator/
        // contentItem positioning (indicator ended up floating mid-sentence
        // in the label text, and its actual clickable area didn't line up
        // with what was visually shown). The label is also tap-to-toggle,
        // for a larger, easier-to-hit target than the indicator alone.
        RowLayout {
            Layout.fillWidth: true
            spacing: 6

            CheckBox {
                id: deleteDataCheck
                checked: false
            }

            Label {
                Layout.fillWidth: true
                text: "Also delete this window's tasks and settings"
                wrapMode: Text.Wrap
                color: Theme.textColor
                font.pixelSize: Theme.taskFontPixelSize

                TapHandler {
                    onTapped: deleteDataCheck.checked = !deleteDataCheck.checked
                }
            }
        }
    }
}

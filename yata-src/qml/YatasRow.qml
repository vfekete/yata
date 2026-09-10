import QtQuick
import QtQuick.Controls
import QtQuick.Dialogs
import QtQuick.Layouts
import QtQuick.Effects

// One row in YatasView: a window's tag (double-click to rename, matching
// TaskDelegate's double-click-to-edit convention) plus a right-hand button
// set that depends on which category the row is in (see `deleted` below):
// an ACTIVE row gets the SHOW toggle + a trash icon that soft-deletes it
// (moves it to DELETED, keeping its data — see WindowManager.deleteWindow);
// a DELETED row instead gets exactly two buttons, "Re-create" (restores it
// back to ACTIVE and reopens it from its still-on-disk data) and "Purge"
// (permanently discards its registry entry and data) — never both sets at
// once, per r-3.md's follow-up spec.
//
// Host-owned (window management is master-application chrome, not plugin
// content — see yata-src/qml/YatasView.qml's own header) — styled off the
// fixed chrome palette passed down from Main.qml, not any plugin's Theme.
// Icons use plain Image + iconProvider.coloredSvgUri() directly (not the
// plugin's IconIndicator.qml, which sizes itself off Theme.taskFontPixelSize
// — a plugin-owned, zoomable value chrome must not depend on).
Item {
    id: root
    required property string windowId
    required property string tag
    required property bool open
    required property bool deleted
    required property int openWindowCount
    // This window's own custom border color (r-4.md), "" if unset.
    required property string borderColor
    signal renamed(string windowId, string newTag)
    signal deleteRequested(string windowId, string tag)
    signal showToggled(string windowId, bool show)
    signal recreateRequested(string windowId)
    signal purgeRequested(string windowId, string tag)
    signal borderColorPicked(string windowId, color newColor)

    required property color chromeTextColor
    required property color chromeMutedTextColor
    required property color chromeAccentColor
    required property string chromeFontFamily
    required property int chromeFontPixelSize
    required property var chromeBoxColor
    required property color chromeFieldColor
    required property color chromeHoverColor
    required property color chromeDangerColor

    property bool editing: false
    readonly property bool hovered: hoverHandler.hovered

    // Matches IconIndicator.qml's own boxHeight formula (1.15 * a 0.65
    // sizeScale, applied to the font size chrome equivalent uses here) —
    // same visual proportions, just off chromeFontPixelSize instead of the
    // plugin's own (zoomable) Theme.taskFontPixelSize.
    readonly property int iconBoxHeight: Math.round(root.chromeFontPixelSize * 0.86)

    width: ListView.view.width
    // A touch taller for a DELETED row, to make room for deletedLabel
    // underneath mainRow (see its own comment below).
    height: Math.max(30, mainRow.implicitHeight + 12 + (root.deleted ? deletedLabel.implicitHeight + 2 : 0))

    HoverHandler { id: hoverHandler }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? root.chromeHoverColor : "transparent"
    }

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: 10

        Text {
            id: tagText
            Layout.fillWidth: true
            visible: !root.editing
            text: root.tag
            // Shows in that window's own custom border color (r-4.md) when
            // it has one — this is a DIFFERENT window than the one this
            // list lives in, so it uses root.borderColor (this row's own
            // reactive property), not this window's own chromeAccentColor.
            color: root.borderColor !== "" ? root.borderColor : root.chromeTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: root.chromeFontPixelSize

            TapHandler {
                onDoubleTapped: root.editing = true
            }
        }

        TextField {
            id: editField
            Layout.fillWidth: true
            visible: root.editing
            text: root.tag
            color: root.chromeTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: root.chromeFontPixelSize
            background: Rectangle {
                radius: 4
                color: root.chromeFieldColor
            }

            onVisibleChanged: if (visible) { selectAll(); forceActiveFocus() }

            function commit() {
                root.editing = false
                var trimmed = text.trim()
                if (trimmed.length > 0 && trimmed !== root.tag)
                    root.renamed(root.windowId, trimmed)
            }
            onEditingFinished: commit()
            Keys.onReturnPressed: commit()
            Keys.onEscapePressed: root.editing = false
        }

        // ── ACTIVE row: SHOW toggle + soft-delete ────────────────────────

        Image {
            id: showBtn
            // Hidden (not just disabled) when this is the only window open
            // right now — closing it would leave nothing on screen and no
            // YatasView left to reopen anything from. A closed window's row
            // always keeps its button. Never shown for a DELETED row.
            visible: !root.deleted && !root.editing && (!root.open || root.openWindowCount > 1)
            source: iconProvider.coloredSvgUri("visibility",
                (showHover.hovered ? root.chromeAccentColor : (root.open ? root.chromeTextColor : root.chromeMutedTextColor)).toString())
            fillMode: Image.PreserveAspectFit
            smooth: true
            height: root.iconBoxHeight
            width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
            Layout.preferredWidth: width
            Layout.preferredHeight: height
            Layout.alignment: Qt.AlignVCenter
            opacity: root.open ? 1.0 : 0.4
            layer.enabled: showHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: showHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.showToggled(root.windowId, !root.open) }
        }

        // Custom border/tag-name color picker (r-4.md) — same "ACTIVE row
        // only" visibility as showBtn/deleteBtn above.
        Image {
            id: colorBtn
            visible: !root.deleted && !root.editing
            source: iconProvider.coloredSvgUri("paintbucket",
                (colorHover.hovered ? root.chromeAccentColor : root.chromeTextColor).toString())
            fillMode: Image.PreserveAspectFit
            smooth: true
            height: root.iconBoxHeight
            width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
            Layout.preferredWidth: width
            Layout.preferredHeight: height
            Layout.alignment: Qt.AlignVCenter
            layer.enabled: colorHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: colorHover; cursorShape: Qt.PointingHandCursor }
            TapHandler {
                onTapped: {
                    var current = windowManager.getBorderColor(root.windowId)
                    colorDialog.selectedColor = current !== "" ? current : "white"
                    colorDialog.open()
                }
            }

            // QtQuick.Dialogs' ColorDialog only reports a final choice via
            // selectedColor/accepted — confirm-to-apply, not live-preview
            // (native OS color pickers work the same way).
            ColorDialog {
                id: colorDialog
                title: qsTr("Choose border color")
                onAccepted: root.borderColorPicked(root.windowId, selectedColor)
            }
        }

        Text {
            id: deleteBtn
            // Soft-delete only — moves the row to the DELETED category,
            // data untouched (see WindowManager.deleteWindow). Never shown
            // for an already-DELETED row; that's purgeBtn's job below.
            visible: !root.deleted && !root.editing
            text: "🗑"
            color: deleteHover.hovered ? root.chromeAccentColor : root.chromeMutedTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 1.3)
            layer.enabled: deleteHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: deleteHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.deleteRequested(root.windowId, root.tag) }
        }

        // ── DELETED row: Re-create + Purge ───────────────────────────────

        Text {
            id: recreateBtn
            // Same glyph/meaning as TaskDelegate.qml's reopenBtn ("re-
            // active" for a done/cancelled task): bring this back to its
            // normal (here: ACTIVE) state. A direct action, no
            // confirmation — unlike delete/purge this one isn't destructive.
            visible: root.deleted && !root.editing
            text: "↺"
            color: recreateHover.hovered ? root.chromeAccentColor : root.chromeTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 1.3)
            layer.enabled: recreateHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: recreateHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.recreateRequested(root.windowId) }
        }

        Text {
            id: purgeBtn
            // Permanently discards the registry entry AND its on-disk
            // tasks/settings (WindowManager.purgeWindow) — genuinely
            // irreversible, unlike deleteBtn above, so PurgeWindowDialog
            // always confirms first.
            visible: root.deleted && !root.editing
            text: "🗑"
            color: purgeHover.hovered ? root.chromeAccentColor : root.chromeMutedTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 1.3)
            layer.enabled: purgeHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.05
            }
            HoverHandler { id: purgeHover; cursorShape: Qt.PointingHandCursor }
            TapHandler { onTapped: root.purgeRequested(root.windowId, root.tag) }
        }
    }

    // Same idiom TaskDelegate.qml's own DONE/CANCELED label uses — a
    // small, colored word beneath the name — explicit follow-up request,
    // "similarly to DONE or CANCELLED". A sibling anchored below mainRow
    // rather than nested inside it (tried first: wrapping tagText in a
    // Column broke TapHandler's double-tap detection the moment more than
    // one window had existed earlier in the same process — confirmed via a
    // from-scratch reproduction with/without the wrapper; root cause not
    // fully understood, but reparenting tagText out of the RowLayout at
    // all clearly isn't worth it for one label).
    Text {
        id: deletedLabel
        visible: root.deleted
        anchors.left: mainRow.left
        anchors.top: mainRow.bottom
        anchors.topMargin: 2
        text: qsTr("DELETED")
        color: root.chromeDangerColor
        font.family: root.chromeFontFamily
        font.pixelSize: Math.round(root.chromeFontPixelSize * 0.75)
        font.bold: true
        layer.enabled: true
        layer.effect: MultiEffect {
            shadowEnabled: true
            shadowColor: deletedLabel.color
            shadowBlur: 1.0
            shadowHorizontalOffset: 0
            shadowVerticalOffset: 0
            shadowOpacity: 1.0
        }
    }
}

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
Item {
    id: root
    required property string windowId
    required property string tag
    required property bool open
    required property bool deleted
    required property int openWindowCount
    signal renamed(string windowId, string newTag)
    signal deleteRequested(string windowId, string tag)
    signal showToggled(string windowId, bool show)
    signal recreateRequested(string windowId)
    signal purgeRequested(string windowId, string tag)
    // r-4.md: a custom border/tag-name color for this window, picked via
    // colorBtn below — fires once the ColorDialog is accepted (confirm-to-
    // apply; QtQuick.Dialogs' ColorDialog only reports a final selection,
    // not a continuous live one — see colorBtn's own comment).
    signal borderColorPicked(string windowId, color newColor)

    property bool editing: false
    readonly property bool hovered: hoverHandler.hovered

    width: ListView.view.width
    height: Math.max(30, mainRow.implicitHeight + 12)

    HoverHandler { id: hoverHandler }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? Theme.hoverColor : "transparent"
    }

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: 10

        Text {
            id: tagText
            Layout.fillWidth: true
            visible: !root.editing
            text: root.tag
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize

            TapHandler {
                onDoubleTapped: root.editing = true
            }
        }

        TextField {
            id: editField
            Layout.fillWidth: true
            visible: root.editing
            text: root.tag
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
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

        IconIndicator {
            id: showBtn
            // Hidden (not just disabled) when this is the only window open
            // right now — closing it would leave nothing on screen and no
            // YatasView left to reopen anything from. A closed window's row
            // always keeps its button (reopening is always safe). Never
            // shown at all for a DELETED row — SHOW/hide doesn't apply
            // there, that's what Re-create is for.
            visible: !root.deleted && !root.editing && (!root.open || root.openWindowCount > 1)
            iconName: "visibility"
            // 65% of the original 1.15 size, per explicit user request after
            // it rendered far larger than deleteBtn and not vertically
            // centered with it — height follows width via IconIndicator's
            // own aspect-ratio sizing.
            sizeScale: 1.15 * 0.65
            Layout.alignment: Qt.AlignVCenter
            // Even with matching AlignVCenter, the eye's tightly-cropped SVG
            // box and deleteBtn's emoji glyph (which renders with descender
            // padding baked into its own line-height box, pushing the
            // visible glyph higher than its box's true center) don't share
            // the same optical center — this nudges the eye to match
            // deleteBtn's visible glyph position rather than its box.
            // Started as +0.2*taskFontPixelSize (too far down per live
            // screenshot); pulled back up 15px per direct user feedback.
            Layout.topMargin: Math.round(Theme.taskFontPixelSize * 0.2) - 15
            tint: showHover.hovered ? "#00FFFF" : (root.open ? Theme.textColor : Theme.mutedTextColor)
            opacity: root.open ? 1.0 : 0.4
            layer.enabled: showHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: "#00FFFF"
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
        // only" visibility as showBtn/deleteBtn above; a deleted window
        // isn't rendered, so there's nothing to preview a color change on.
        // Tinted/glowed the same neutral way as every other icon here
        // (hover-only cyan), not by whatever color is currently picked —
        // that flourish wasn't asked for.
        IconIndicator {
            id: colorBtn
            visible: !root.deleted && !root.editing
            iconName: "paintbucket"
            sizeScale: 1.15 * 0.65
            Layout.alignment: Qt.AlignVCenter
            Layout.topMargin: Math.round(Theme.taskFontPixelSize * 0.2) - 15
            tint: colorHover.hovered ? "#00FFFF" : Theme.textColor
            layer.enabled: colorHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: "#00FFFF"
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

            // QtQuick.Dialogs' ColorDialog (the native platform dialog when
            // one is available) only reports a final choice via
            // selectedColor/accepted — unlike, say, a Slider's onMoved,
            // there's no continuous "still picking" signal to preview
            // against, so this is confirm-to-apply rather than live-preview
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
            color: deleteHover.hovered ? "#00FFFF" : Theme.mutedTextColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize * 1.3
            layer.enabled: deleteHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: "#00FFFF"
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
            // Same glyph/style as TaskDelegate.qml's reopenBtn ("re-active"
            // for a done/cancelled task) — same icon, same meaning: bring
            // this back to its normal (here: ACTIVE) state. A direct action,
            // no confirmation — same precedent as reopenBtn, and unlike
            // delete/purge this one isn't destructive at all.
            visible: root.deleted && !root.editing
            text: "↺"
            color: recreateHover.hovered ? "#00FFFF" : Theme.accentColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize * 1.3
            layer.enabled: recreateHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: "#00FFFF"
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
            color: purgeHover.hovered ? "#00FFFF" : Theme.mutedTextColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize * 1.3
            layer.enabled: purgeHover.hovered
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: "#00FFFF"
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
}

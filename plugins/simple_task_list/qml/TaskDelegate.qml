import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

Item {
    id: root
    required property int index
    required property string taskId
    required property string text
    required property string status
    required property string dayLabel
    required property string completedAt
    required property string note

    property bool forceEditing: false
    readonly property bool editing: forceEditing || text.length === 0
    readonly property bool hovered: hoverHandler.hovered

    readonly property color effectiveBorderColor: hostSettings.borderColor !== "" ? hostSettings.borderColor : "#000000"
    readonly property color rowHoverColor: (Theme.tintName === "none" && hostSettings.borderColor !== "")
        ? Qt.rgba(effectiveBorderColor.r, effectiveBorderColor.g, effectiveBorderColor.b, 0.18)
        : Theme.hoverColor
    readonly property bool flashed: root.taskId !== "" && root.ListView.view.flashTaskId === root.taskId
    onFlashedChanged: if (flashed) {
        flashFade.stop()
        flashOverlay.opacity = 1.0
        flashFade.start()
    }

    function activateFocus() {
        editField.forceActiveFocus()
    }

    readonly property bool dragSource: root.ListView.view.dragActive
                                        && root.index === root.ListView.view.dragFromIndex
    readonly property bool showGapBelow: root.ListView.view.dragHoverActive
                                          && root.ListView.view.dragHoverIndex === root.index
                                          && !(root.ListView.view.dragActive
                                               && root.ListView.view.dragFromIndex === root.index)
    readonly property int gapHeight: Math.max(30, Theme.taskFontPixelSize + 16)

    width: ListView.view.width
    height: (dragSource ? 0 : Math.max(30, mainRow.implicitHeight + 12)) + (showGapBelow ? gapHeight : 0)
    Behavior on height {
        NumberAnimation { duration: 120; easing.type: Easing.InOutQuad }
    }

    function mdToHtml(md, lc) {
        var codes = []
        var s = md.replace(/`([^`\n]+)`/g, function(_, c) {
            codes.push(c.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'))
            return '\x00' + (codes.length - 1) + '\x00'
        })
        s = s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        s = s.replace(/\*\*([^*\n]+)\*\*/g, '<b>$1</b>')
        s = s.replace(/\*([^*\n]+)\*/g, '<i>$1</i>')
        s = s.replace(/~~([^~\n]+)~~/g, '<s>$1</s>')
        s = s.replace(/\[([^\]\n]*)\]\(([^)\n]*)\)/g,
            '<a href="$2"><font color="' + lc + '">$1</font></a>')
        s = s.replace(/\n/g, '<br>')
        return s.replace(/\x00(\d+)\x00/g, function(_, i) {
            return '<code>' + codes[parseInt(i)] + '</code>'
        })
    }

    HoverHandler { id: hoverHandler }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: itemMenu.popup()
    }

    DragHandler {
        id: rowDrag
        target: null
        enabled: !root.editing && taskModel.canReorder
        acceptedButtons: Qt.LeftButton

        property real lastGlobalX: 0
        property real lastGlobalY: 0

        onActiveChanged: {
            var view = root.ListView.view
            if (active) {
                view.dragActive = true
                view.dragFromIndex = root.index
                view.dragHoverIndex = root.index
                windowManager.showDragGhost(root.text, root.status)
                return
            }
            var wm = windowManager
            if (view.dragActive) {
                if (view.dragTargetWindowId !== "" && view.dragTargetWindowId !== windowId) {
                    wm.moveTaskToWindow(windowId, root.taskId, view.dragTargetWindowId)
                } else if (view.dragTargetWindowId === windowId
                           && view.dragHoverIndex >= 0 && view.dragHoverIndex !== view.dragFromIndex) {
                    taskModel.moveTask(view.dragFromIndex, view.dragHoverIndex)
                }
            }
            wm.hideDragGhost()
            wm.clearDragHover()
            view.dragActive = false
            view.dragFromIndex = -1
            view.dragHoverIndex = -1
            view.dragTargetWindowId = ""
        }

        onCentroidChanged: {
            if (!root.ListView.view.dragActive)
                return
            var win = root.Window.window
            var posInWindow = root.mapToItem(null, centroid.position.x, centroid.position.y)
            rowDrag.lastGlobalX = win.x + posInWindow.x
            rowDrag.lastGlobalY = win.y + posInWindow.y
        }
    }

    Timer {
        id: dragUpdateTimer
        interval: 16
        repeat: true
        running: rowDrag.active
        onTriggered: {
            root.ListView.view.dragTargetWindowId =
                windowManager.windowAt(rowDrag.lastGlobalX, rowDrag.lastGlobalY)
            windowManager.moveDragGhost(rowDrag.lastGlobalX, rowDrag.lastGlobalY)
        }
    }

    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: !root.editing
        onTapped: root.forceActiveFocus()
    }

    Menu {
        id: itemMenu
        MenuItem { text: qsTr("Delete task"); onTriggered: taskModel.deleteTask(root.taskId); padding: 10 }
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? root.rowHoverColor : "transparent"
    }

    Rectangle {
        id: flashOverlay
        anchors.fill: parent
        radius: 4
        color: Theme.filterGlowColor
        opacity: 0
    }
    SequentialAnimation {
        id: flashFade
        loops: 3
        PropertyAction { target: flashOverlay; property: "opacity"; value: 1.0 }
        NumberAnimation {
            target: flashOverlay
            property: "opacity"
            to: 0.0
            duration: 1200 / 3
            easing.type: Easing.OutCubic
        }
    }

    Rectangle {
        id: dropPlaceholder
        visible: root.showGapBelow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.bottom: parent.bottom
        height: root.gapHeight
        radius: 4
        color: Qt.rgba(Theme.filterGlowColor.r, Theme.filterGlowColor.g, Theme.filterGlowColor.b, 0.15)
        border.color: Theme.filterGlowColor
        border.width: 2
    }

    opacity: root.dragSource ? 0.4 : 1.0

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.leftMargin: taskModel.groupByDay ? 24 : 4
        anchors.rightMargin: 4
        spacing: 4

        Column {
            id: orderControls
            visible: root.hovered && taskModel.canReorder
            Layout.alignment: Qt.AlignVCenter
            spacing: Math.round(Theme.taskFontPixelSize * 0.4)

            readonly property bool canMoveUp: root.index > 0
            readonly property bool canMoveDown: root.index < root.ListView.view.count - 1
            readonly property int iconSize: Math.round(Theme.taskFontPixelSize * 1.15)

            Image {
                id: upIcon
                width: orderControls.iconSize
                height: orderControls.iconSize
                fillMode: Image.PreserveAspectFit
                smooth: true
                opacity: orderControls.canMoveUp ? 1.0 : 0.35
                source: iconProvider.coloredSvgUri("move_up",
                    (upHover.hovered && orderControls.canMoveUp ? Theme.effectiveGlowColor : Theme.mutedTextColor).toString())
                layer.enabled: upHover.hovered && orderControls.canMoveUp
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.1
                }

                HoverHandler {
                    id: upHover
                    enabled: orderControls.canMoveUp
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    enabled: orderControls.canMoveUp
                    onTapped: taskModel.moveTaskUp(root.taskId)
                }
            }
            Image {
                id: downIcon
                width: orderControls.iconSize
                height: orderControls.iconSize
                fillMode: Image.PreserveAspectFit
                smooth: true
                opacity: orderControls.canMoveDown ? 1.0 : 0.35
                source: iconProvider.coloredSvgUri("move_down",
                    (downHover.hovered && orderControls.canMoveDown ? Theme.effectiveGlowColor : Theme.mutedTextColor).toString())
                layer.enabled: downHover.hovered && orderControls.canMoveDown
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.1
                }

                HoverHandler {
                    id: downHover
                    enabled: orderControls.canMoveDown
                    cursorShape: Qt.PointingHandCursor
                }
                TapHandler {
                    enabled: orderControls.canMoveDown
                    onTapped: taskModel.moveTaskDown(root.taskId)
                }
            }
        }

        Column {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            Layout.rightMargin: 50
            visible: !root.editing
            spacing: 2

            Text {
                id: taskText
                width: parent.width
                text: root.mdToHtml(root.text, Theme.effectiveLinkColor)
                textFormat: Text.StyledText
                wrapMode: root.hovered ? Text.Wrap : Text.NoWrap
                elide: root.hovered ? Text.ElideNone : Text.ElideRight
                horizontalAlignment: Text.AlignJustify
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                color: {
                    if (root.status === "done") return Theme.doneColor
                    if (root.status === "cancelled") return Theme.cancelledColor
                    return Theme.textColor
                }
                font.strikeout: root.status !== "active"

                onLinkActivated: link => Qt.openUrlExternally(link)

                HoverHandler {
                    cursorShape: taskText.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor
                }

                TapHandler {
                    onDoubleTapped: root.forceEditing = true
                }
            }

            Row {
                id: completedLabel
                width: parent.width
                visible: root.status !== "active"
                spacing: 0

                FontMetrics {
                    id: statusFontMetrics
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
                }

                Text {
                    id: completedStatus
                    textFormat: Text.PlainText
                    text: root.status === "done" ? qsTr("DONE") : qsTr("CANCELED")
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
                    width: Math.max(statusFontMetrics.advanceWidth(qsTr("DONE")), statusFontMetrics.advanceWidth(qsTr("CANCELED"))) + statusFontMetrics.advanceWidth("     ")
                    readonly property color labelColor: root.status === "done" ? Theme.completedDoneLabelColor : Theme.completedCancelledLabelColor
                    color: labelColor
                    layer.enabled: true
                    layer.effect: MultiEffect {
                        shadowEnabled: true
                        shadowColor: completedStatus.labelColor
                        shadowBlur: 1.0
                        shadowHorizontalOffset: 0
                        shadowVerticalOffset: 0
                        shadowOpacity: 1.0
                        shadowScale: 1.05
                    }
                }

                Text {
                    id: completedTimestamp
                    visible: root.completedAt !== ""
                    textFormat: Text.PlainText
                    text: {
                        if (root.completedAt === "") return ""
                        var dt = new Date(root.completedAt)
                        var dd = String(dt.getDate()).padStart(2, '0')
                        var mm = String(dt.getMonth() + 1).padStart(2, '0')
                        var HH = String(dt.getHours()).padStart(2, '0')
                        var MM = String(dt.getMinutes()).padStart(2, '0')
                        return dd + "-" + mm + "-" + dt.getFullYear() + " " + HH + ":" + MM
                    }
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
                    color: root.status === "done" ? Theme.doneColor : Theme.cancelledColor
                }

                Item {
                    width: Math.round(Theme.taskFontPixelSize * 0.8)
                    height: 1
                }


                Item {
                    width: noteIconImg.width + Theme.nonActiveActionIconGap
                    height: completedStatus.implicitHeight
                    Image {
                        id: noteIconImg
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        height: Theme.taskFontPixelSize
                        width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                        fillMode: Image.PreserveAspectFit
                        smooth: true
                        source: iconProvider.coloredSvgUri("notes",
                            (noteIconHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor).toString())
                        layer.enabled: noteIconHover.hovered
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowColor: Theme.effectiveGlowShadowColor
                            shadowBlur: 1.0
                            shadowHorizontalOffset: 0
                            shadowVerticalOffset: 0
                            shadowOpacity: 1.0
                            shadowScale: 1.05
                        }
                        HoverHandler { id: noteIconHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: root.ListView.view.noteEditorTaskId = root.taskId }
                    }
                }

                Item {
                    width: reopenGlyph.implicitWidth + Theme.nonActiveActionIconGap
                    height: completedStatus.implicitHeight

                    Text {
                        id: reopenGlyph
                        anchors.right: parent.right
                        anchors.verticalCenter: parent.verticalCenter
                        text: "↺"
                        font.family: Theme.fontFamily
                        font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.2)
                        color: reopenGlyphHover.hovered ? Theme.effectiveGlowColor : Theme.accentColor
                        layer.enabled: reopenGlyphHover.hovered
                        layer.effect: MultiEffect {
                            shadowEnabled: true
                            shadowColor: Theme.effectiveGlowShadowColor
                            shadowBlur: 1.0
                            shadowHorizontalOffset: 0
                            shadowVerticalOffset: 0
                            shadowOpacity: 1.0
                            shadowScale: 1.05
                        }
                        HoverHandler { id: reopenGlyphHover; cursorShape: Qt.PointingHandCursor }
                        TapHandler { onTapped: taskModel.setStatus(root.taskId, "active") }
                    }
                }
            }
        }

        TextField {
            id: editField
            objectName: "taskDescriptionField"
            Layout.fillWidth: true
            visible: root.editing
            text: root.text
            placeholderText: qsTr("Task name")
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }

            property bool committedViaEnter: false

            onVisibleChanged: if (visible) forceActiveFocus()
            Component.onCompleted: {
                if (visible) {
                    suppressAutoSave = true
                    Qt.callLater(function() { suppressAutoSave = false })
                    forceActiveFocus()
                }
            }
            property bool suppressAutoSave: false
            onEditingFinished: {
                if (committedViaEnter) return
                if (suppressAutoSave && root.text.length === 0) return
                root.forceEditing = false
                if (text.length > 0) {
                    taskModel.setText(root.taskId, text)
                } else if (root.text.length === 0) {
                    taskModel.setText(root.taskId, qsTr("Task name"))
                }
            }
            Keys.onReturnPressed: (event) => {
                event.accepted = true
                committedViaEnter = true
                if (text.length > 0) {
                    root.forceEditing = false
                    taskModel.setText(root.taskId, text)
                } else if (root.text.length === 0) {
                    taskModel.deleteTask(root.taskId)
                } else {
                    root.forceEditing = false
                }
            }
            Keys.onEscapePressed: {
                if (root.text.length === 0)
                    taskModel.deleteTask(root.taskId)
                else
                    root.forceEditing = false
            }
        }

        Row {
            visible: root.hovered && !root.editing
            spacing: 4
            Layout.alignment: Qt.AlignTop

            HoldToNoteButton {
                id: doneBtn
                visible: root.status === "active"
                taskId: root.taskId
                targetStatus: "done"
                glyph: "✓"
                idleColor: Theme.doneColor
                note: root.note
            }
            HoldToNoteButton {
                id: cancelBtn
                visible: root.status === "active"
                taskId: root.taskId
                targetStatus: "cancelled"
                glyph: "✕"
                idleColor: Theme.cancelledColor
                note: root.note
            }
            Text {
                id: deleteBtn
                text: "🗑"
                color: deleteBtnHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                layer.enabled: deleteBtnHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                HoverHandler { id: deleteBtnHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: deleteConfirm.open() }
            }
        }
    }

    DialogWindow {
        id: deleteConfirm
        title: qsTr("Delete task?")
        contentWidth: Math.max(260, Math.round(Theme.taskFontPixelSize * 20))
        onAccepted: taskModel.deleteTask(root.taskId)

        Label {
            text: qsTr("This action cannot be undone.")
            color: Theme.textColor
            font.pixelSize: Theme.taskFontPixelSize
        }
    }
}

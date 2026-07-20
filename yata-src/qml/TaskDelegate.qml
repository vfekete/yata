import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    required property int index
    required property string taskId
    required property string text
    required property string status
    required property string dayLabel
    required property string completedAt

    property bool forceEditing: false
    readonly property bool editing: forceEditing || text.length === 0
    readonly property bool hovered: hoverHandler.hovered

    function activateFocus() {
        editField.forceActiveFocus()
    }

    width: ListView.view.width
    height: Math.max(30, mainRow.implicitHeight + 12)

    // Text.linkColor is unreliable even with StyledText (Qt may ignore it).
    // Embed the color directly via <font color> so it is always applied.
    // lc is passed as an argument so the binding tracks Theme.linkColor as a
    // dependency and re-evaluates when the theme changes.
    function mdToHtml(md, lc) {
        var codes = []
        // Stash code spans so inner content isn't mangled by later passes.
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

    // When the user clicks on a non-editing task row, take focus from whatever
    // currently has it (e.g. an editing TextField in another delegate) so that
    // its onEditingFinished fires and saves correctly.  Non-interactive items
    // (Text, Rectangle) don't accept keyboard focus, so without this handler a
    // click on another task row would silently leave focus on the editor.
    //
    // Must target `root` (this delegate's Item), NOT root.ListView.view: the
    // ListView is a Flickable and already has activeFocus=true as an ancestor
    // of the editing TextField, so forceActiveFocus() on it is a no-op.
    // Targeting `root` (a sibling of the editing delegate in the contentItem)
    // genuinely steals focus because root.activeFocus is false.
    TapHandler {
        acceptedButtons: Qt.LeftButton
        enabled: !root.editing
        onTapped: root.forceActiveFocus()
    }

    Menu {
        id: itemMenu
        MenuItem { text: "Delete task"; onTriggered: taskModel.deleteTask(root.taskId); padding: 10 }
    }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? Theme.hoverColor : "transparent"
    }

    // Marks the current drop target while a drag is in progress.
    Rectangle {
        visible: root.ListView.view.dragActive
                 && root.ListView.view.dragHoverIndex === root.index
                 && root.index !== root.ListView.view.dragFromIndex
        anchors.top: parent.top
        width: parent.width
        height: 2
        color: Theme.accentColor
    }

    opacity: root.ListView.view.dragActive && root.ListView.view.dragFromIndex === root.index ? 0.4 : 1.0

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        // Day-grouped view gets extra left indent so rows read as nested
        // under their day header rather than flush with it.
        anchors.leftMargin: taskModel.groupByDay ? 24 : 4
        anchors.rightMargin: 4
        spacing: 4

        Text {
            id: dragHandle
            text: "⋮⋮"
            color: Theme.mutedTextColor
            font.family: Theme.fontFamily
            visible: root.hovered && taskModel.canReorder
            Layout.alignment: Qt.AlignVCenter

            MouseArea {
                anchors.fill: parent
                anchors.margins: -4
                cursorShape: Qt.SizeVerCursor
                preventStealing: true

                onPressed: {
                    var view = root.ListView.view
                    view.dragActive = true
                    view.dragFromIndex = root.index
                    view.dragHoverIndex = root.index
                }
                onPositionChanged: (mouse) => {
                    var view = root.ListView.view
                    if (!view.dragActive)
                        return
                    var posInView = mapToItem(view, mouse.x, mouse.y)
                    var idx = view.indexAt(1, posInView.y + view.contentY)
                    if (idx >= 0)
                        view.dragHoverIndex = idx
                }
                onReleased: {
                    var view = root.ListView.view
                    if (view.dragActive && view.dragHoverIndex >= 0 && view.dragHoverIndex !== view.dragFromIndex)
                        taskModel.moveTask(view.dragFromIndex, view.dragHoverIndex)
                    view.dragActive = false
                    view.dragFromIndex = -1
                    view.dragHoverIndex = -1
                }
            }
        }

        Column {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            visible: !root.editing
            spacing: 2

            Text {
                id: taskText
                width: parent.width
                text: root.mdToHtml(root.text, Theme.linkColor)
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

                Text {
                    id: completedStatus
                    textFormat: Text.PlainText
                    text: root.status === "done" ? "DONE" : "CANCELED"
                    font.family: Theme.fontFamily
                    font.pixelSize: Math.round(Theme.taskFontPixelSize * 0.75)
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
                    visible: root.completedAt !== ""
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
        }

        TextField {
            id: editField
            Layout.fillWidth: true
            visible: root.editing
            text: root.text
            placeholderText: "Task name"
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }

            // Set to true by Keys.onReturnPressed before calling setText so that
            // the spurious onEditingFinished that fires during _recompute()'s
            // beginResetModel() (which causes focus loss) does not overwrite the
            // value just committed by the Enter handler.
            property bool committedViaEnter: false

            // onVisibleChanged handles the double-click-to-edit path (visible
            // transitions false→true). Component.onCompleted handles new-task
            // creation (visible is already true at birth, so onVisibleChanged
            // never fires for those).
            onVisibleChanged: if (visible) forceActiveFocus()
            Component.onCompleted: {
                if (visible) {
                    // Suppress onEditingFinished for the first event-loop tick:
                    // the click that triggered addTask() causes Qt to steal focus
                    // back in the same tick, which would instantly fire
                    // onEditingFinished and auto-save "Task name" — hiding the
                    // field before the 100 ms focus timer can re-grab it.
                    suppressAutoSave = true
                    Qt.callLater(function() { suppressAutoSave = false })
                    forceActiveFocus()
                }
            }
            // True for one event-loop tick after a new-task delegate is born,
            // to block the spurious onEditingFinished that fires when Qt steals
            // focus back during click-event processing (see Component.onCompleted).
            property bool suppressAutoSave: false
            // Fires on focus loss (click-away). Enter key is handled below and
            // sets committedViaEnter=true so this handler skips the spurious fire
            // that beginResetModel() triggers inside setText().
            onEditingFinished: {
                if (committedViaEnter) return
                // Suppress the immediate spurious fire on new-task creation.
                if (suppressAutoSave && root.text.length === 0) return
                root.forceEditing = false
                if (text.length > 0) {
                    taskModel.setText(root.taskId, text)
                } else if (root.text.length === 0) {
                    taskModel.setText(root.taskId, "Task name")
                }
                // else: existing task, user cleared all text → cancel edit silently
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

            Text {
                id: doneBtn
                text: "✓"
                color: doneBtnHover.hovered ? "#00FFFF" : Theme.doneColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                layer.enabled: doneBtnHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: "#00FFFF"
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                HoverHandler { id: doneBtnHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: taskModel.setStatus(root.taskId, "done") }
            }
            Text {
                id: cancelBtn
                text: "✕"
                color: cancelBtnHover.hovered ? "#00FFFF" : Theme.cancelledColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                layer.enabled: cancelBtnHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: "#00FFFF"
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                HoverHandler { id: cancelBtnHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: taskModel.setStatus(root.taskId, "cancelled") }
            }
            Text {
                id: reopenBtn
                text: "↺"
                color: reopenBtnHover.hovered ? "#00FFFF" : Theme.accentColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                visible: root.status !== "active"
                layer.enabled: reopenBtnHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: "#00FFFF"
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                HoverHandler { id: reopenBtnHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: taskModel.setStatus(root.taskId, "active") }
            }
            Text {
                id: deleteBtn
                text: "🗑"
                color: deleteBtnHover.hovered ? "#00FFFF" : Theme.mutedTextColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                layer.enabled: deleteBtnHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: "#00FFFF"
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

    Dialog {
        id: deleteConfirm
        modal: true
        title: "Delete task?"
        font.pixelSize: Theme.taskFontPixelSize
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: taskModel.deleteTask(root.taskId)

        Label {
            text: "This action cannot be undone."
            font.pixelSize: Theme.taskFontPixelSize
        }
    }
}

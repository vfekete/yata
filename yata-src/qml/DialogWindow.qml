import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

// Base for every confirmation/prompt dialog in the app — a REAL top-level
// window, unlike QtQuick.Controls' Dialog/Popup (which renders inside its
// parent Window's own Overlay layer, i.e. is still part of the very same
// X11 window as whatever opened it). That distinction is not cosmetic here:
// every YATA window gets _NET_WM_STATE_BELOW set on it (see
// x11_stacking.py) so it stays beneath other apps on the desktop — an
// in-window Dialog inherited that same stacking, so a confirmation could
// pop up hidden behind whatever else is on screen. A `Window {}` declared
// nested inside another window's QML tree gets its transientParent set to
// that enclosing window automatically (Qt Quick's own default behavior),
// giving it normal, independent window-manager stacking — it is never
// itself passed to enable_always_below() (see main.py; that's only ever
// called on each YATA window's own top-level Main.qml window) — while
// still inheriting that window's QQmlContext, so Theme/taskModel/
// windowManager/... all keep resolving normally, exactly like any other
// nested QML object (see DragGhost.qml for the same nested-Window
// technique, used there for an unrelated reason).
Window {
    id: root
    flags: Qt.Dialog | Qt.FramelessWindowHint
    modality: Qt.WindowModal
    color: "transparent"
    visible: false

    property string title: ""
    property real contentWidth: Math.max(300, Math.round(Theme.taskFontPixelSize * 26))
    property string okText: "OK"
    property string cancelText: "Cancel"
    property bool showCancel: true
    default property alias content: contentColumn.data

    signal accepted()
    signal rejected()

    function open() {
        root.visible = true
        root.requestActivate()
    }
    function close() {
        root.visible = false
    }
    function accept() {
        root.close()
        root.accepted()
    }
    function reject() {
        root.close()
        root.rejected()
    }

    width: contentWidth
    height: outerColumn.implicitHeight

    // Centered over whichever YATA window opened it, at open time and
    // whenever that window subsequently moves/resizes (e.g. dragged while
    // the dialog is up) — transientParent is a Window, so its own x/y/
    // width/height are directly readable here (see the class comment above
    // for why transientParent is already set with no code on our part).
    x: transientParent ? Math.round(transientParent.x + (transientParent.width - width) / 2) : 0
    y: transientParent ? Math.round(transientParent.y + (transientParent.height - height) / 2) : 0

    onVisibleChanged: if (visible) focusScope.forceActiveFocus()

    // "none" theme's contentBackground is literally "transparent" (the main
    // window's wash is a translucent Rectangle underneath it) — a dialog
    // needs a real solid color to stay readable, same fallback Main.qml's
    // own bottom gradient overlay already uses for the same reason.
    Rectangle {
        anchors.fill: parent
        radius: 4
        color: Theme.tintName === "none"
               ? (Theme.dark ? "#111827" : "#f9fafb")
               : Theme.contentBackground
        border.color: Theme.borderColor
        border.width: 1
    }

    // A Window has no Keys attached property of its own (that's an Item
    // thing) — this FocusScope is what actually receives and reacts to
    // Escape/Enter, activated whenever the window becomes visible above.
    FocusScope {
        id: focusScope
        anchors.fill: parent
        focus: true

        Keys.onEscapePressed: root.reject()
        Keys.onReturnPressed: root.accept()

        ColumnLayout {
            id: outerColumn
            width: parent.width
            spacing: 10

            Label {
                visible: root.title.length > 0
                text: root.title
                color: Theme.textColor
                font.bold: true
                font.pixelSize: Theme.taskFontPixelSize * 1.2
                Layout.fillWidth: true
                Layout.margins: 12
                Layout.bottomMargin: 0
            }

            ColumnLayout {
                id: contentColumn
                Layout.fillWidth: true
                Layout.leftMargin: 12
                Layout.rightMargin: 12
                spacing: 10
            }

            RowLayout {
                Layout.alignment: Qt.AlignRight
                Layout.margins: 12
                Layout.topMargin: 4
                spacing: 8

                Button {
                    text: root.cancelText
                    visible: root.showCancel
                    onClicked: root.reject()
                }
                Button {
                    text: root.okText
                    onClicked: root.accept()
                }
            }
        }
    }
}

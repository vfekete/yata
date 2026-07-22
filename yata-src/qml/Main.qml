import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: root
    visible: true
    color: "transparent"
    // Opacity is applied to the content wrapper below, NOT to the Window
    // itself, so popup menus (rendered in the Window's Overlay layer above
    // the content) always appear at full opacity regardless of the user's
    // slider setting — preventing an irreversible "can't see the menu"
    // situation at very low opacity values.
    // Qt.WindowStaysOnBottomHint is intentionally not used: on GNOME/Mutter
    // (the primary target platform) it places the window below the desktop
    // background layer itself, making it invisible rather than merely
    // "beneath other windows, above icons". See README.md.
    flags: Qt.FramelessWindowHint

    Shortcut {
        sequences: [StandardKey.ZoomIn]
        onActivated: appSettings.fontScale = Math.min(appSettings.fontScale + 0.1, 2.0)
    }
    Shortcut {
        sequences: [StandardKey.ZoomOut]
        onActivated: appSettings.fontScale = Math.max(appSettings.fontScale - 0.1, 0.5)
    }
    Shortcut {
        sequence: "Ctrl+0"
        onActivated: appSettings.fontScale = appSettings.defaultFontScale
    }

    x: appSettings.x
    y: appSettings.y
    width: appSettings.width
    height: appSettings.height
    // Twice the combined width of the ADD/RELOAD/THEME toolbar buttons,
    // scaling with font zoom same as they do (toolbar.actionButtonsWidth is
    // itself font-scale-dependent) — below this, FilterBar's groups have
    // nowhere reasonable left to wrap into.
    minimumWidth: toolbar.actionButtonsWidth * 2

    onXChanged: appSettings.x = x
    onYChanged: appSettings.y = y
    onWidthChanged: appSettings.width = width
    onHeightChanged: appSettings.height = height

    // Right-click anywhere on the background for theme + quit. Placed first so
    // real controls (declared later / painted on top) get first refusal at clicks.
    MouseArea {
        anchors.fill: parent
        acceptedButtons: Qt.RightButton
        onClicked: contextMenu.popup()
    }

    ThemeMenu {
        id: contextMenu
        showQuit: true
    }

    // Ctrl+Wheel zoom interceptor. Sits above all content (z:999) so its
    // WheelHandler sees Ctrl+Wheel events before the ListView's Flickable
    // can consume them for scrolling. Normal (no-modifier) wheel events are
    // not matched by acceptedModifiers and propagate to the ListView as usual.
    Item {
        z: 999
        anchors.fill: parent

        WheelHandler {
            acceptedModifiers: Qt.ControlModifier
            onWheel: (event) => {
                event.accepted = true
                var scrollingUp = event.angleDelta.y > 0
                // Default (not inverted): scroll up → zoom in, scroll down → zoom out.
                var zoomIn = appSettings.wheelZoomInverted ? !scrollingUp : scrollingUp
                if (zoomIn)
                    appSettings.fontScale = Math.min(appSettings.fontScale + 0.1, 2.0)
                else
                    appSettings.fontScale = Math.max(appSettings.fontScale - 0.1, 0.5)
            }
        }
    }

    // Content wrapper: opacity applied here keeps popup menus (which render
    // in the Window Overlay above this Item) always at full opacity.
    Item {
        anchors.fill: parent
        opacity: Theme.windowOpacity

        // The window itself stays fully transparent (per spec); this wash is
        // what actually paints each tint's background, translucent so the
        // window still reads as "transparent" rather than opaque.
        Rectangle {
            anchors.fill: parent
            radius: 6
            color: Theme.contentBackground
        }

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 6
            spacing: 2

            Toolbar {
                id: toolbar
                Layout.fillWidth: true
            }

            FilterBar {
                Layout.fillWidth: true
            }

            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                ListView {
                    id: listView
                    anchors.fill: parent
                    clip: true
                    spacing: 0
                    model: taskModel
                    ScrollBar.vertical: ScrollBar { id: vbar; policy: ScrollBar.AsNeeded }

                    section.property: taskModel.groupByDay ? "dayLabel" : ""
                    section.criteria: ViewSection.FullString
                    section.delegate: sectionHeader

                    // Drag-to-reorder state, read by TaskDelegate instances.
                    property bool dragActive: false
                    property int dragFromIndex: -1
                    property int dragHoverIndex: -1

                    // The scrollbar is an overlay (doesn't reserve its own width),
                    // so rows must leave room for it themselves or their hover
                    // icons render underneath its thumb.
                    property real rowWidth: width - (vbar.visible ? vbar.width : 0)

                    delegate: TaskDelegate {
                        width: listView.rowWidth
                    }
                }

                // Gradient overlay painted on top of the list: fades the
                // bottom 10% from transparent into the window background,
                // hinting that more content lies below. Hidden when already
                // scrolled to the end (nothing more to show).
                // For the "none" theme contentBackground is "transparent", so
                // fall back to a dark/light system-like colour instead.
                Rectangle {
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.bottom: parent.bottom
                    height: parent.height * 0.1
                    visible: listView.contentHeight > listView.height && !listView.atYEnd
                    gradient: Gradient {
                        GradientStop { position: 0.0; color: "transparent" }
                        GradientStop {
                            position: 1.0
                            color: Theme.tintName === "none"
                                   ? (Theme.dark ? "#111827" : "#f9fafb")
                                   : Theme.contentBackground
                        }
                    }
                }
            }
        }

        // After addTask() the model emits taskAdded. We wait one short timer
        // interval (~2 frames) before focusing the new delegate, so the
        // ToolButton's own click-completion handling can't steal focus back.
        // After addTask() the model emits taskAdded. The 100 ms delay lets any
        // click-event processing finish before we re-grab focus, so it sticks.
        // The suppressAutoSave flag in editField ensures the spurious
        // onEditingFinished that fires in the first tick doesn't save "Task name"
        // and hide the field before we get here.
        Timer {
            id: newTaskFocusTimer
            property string pendingId: ""
            interval: 100
            repeat: false
            onTriggered: {
                for (var i = 0; i < Math.min(listView.count, 3); i++) {
                    var item = listView.itemAtIndex(i)
                    if (item && item.taskId === pendingId) {
                        item.activateFocus()
                        break
                    }
                }
            }
        }

        Connections {
            target: taskModel
            function onTaskAdded(taskId) {
                newTaskFocusTimer.pendingId = taskId
                newTaskFocusTimer.restart()
            }
        }

        Component {
            id: sectionHeader
            Rectangle {
                width: listView.rowWidth
                height: headerText.implicitHeight + 10
                color: "transparent"
                Text {
                    id: headerText
                    anchors.left: parent.left
                    anchors.verticalCenter: parent.verticalCenter
                    text: section
                    color: Theme.mutedTextColor
                    font.bold: true
                    // Day name reads as a heading over the task list below it.
                    font.pixelSize: Theme.taskFontPixelSize * 1.5
                    font.family: Theme.fontFamily
                }
            }
        }

        Rectangle {
            anchors.fill: parent
            color: "transparent"
            radius: 6
            border.color: Theme.borderColor
            border.width: 1
        }
    }
}

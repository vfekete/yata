import QtQuick
import QtQuick.Controls
import QtQuick.Effects
import QtQuick.Window

Window {
    id: root
    visible: true
    color: "transparent"
    flags: Qt.FramelessWindowHint

    function chromeBoxColor(hovered) {
        return hovered ? "#1f2937" : "#111827"
    }
    readonly property color chromeTextColor: "#f3f4f6"
    readonly property color chromeMutedTextColor: "#9ca3af"
    readonly property color chromeAccentColor: hostSettings.borderColor !== "" ? hostSettings.borderColor : "#64748b"
    readonly property color chromeDragHoverColor: "#00FFFF"
    readonly property string chromeFontFamily: "Noto Sans"
    readonly property int chromeFontPixelSize: 14
    readonly property color chromeFieldColor: Qt.rgba(1, 1, 1, 0.10)
    readonly property color chromeHoverColor: Qt.rgba(1, 1, 1, 0.08)
    readonly property color chromeDangerColor: "#ef4444"

    x: hostSettings.x
    y: hostSettings.y
    width: hostSettings.width
    height: hostSettings.height
    minimumWidth: (contentLoader.item ? contentLoader.item.actionButtonsWidth : 300) * 2

    onXChanged: hostSettings.x = x
    onYChanged: hostSettings.y = y
    onWidthChanged: hostSettings.width = width
    onHeightChanged: hostSettings.height = height

    function ensureMinimumWidth() {
        if (width < minimumWidth)
            width = minimumWidth
    }
    Component.onCompleted: ensureMinimumWidth()
    onMinimumWidthChanged: ensureMinimumWidth()

    property string windowTag: windowManager.tagFor(windowId)
    Connections {
        target: windowManager
        function onWindowsChanged() { root.windowTag = windowManager.tagFor(windowId) }
    }
    property bool editingTag: false

    property bool dragHoverActive: false
    Connections {
        target: windowManager
        function onTaskDragHoverChanged(targetWindowId, globalX, globalY) {
            root.dragHoverActive = targetWindowId === windowId
        }
    }

    readonly property bool editingTaskDescription: root.activeFocusItem !== null
        && root.activeFocusItem.objectName === "taskDescriptionField"

    property bool yatasActive: false

    readonly property bool contentLocked: {
        if (hostSettings.lockState === "unlocked") return false
        if (hostSettings.lockState === "locked") return true
        if (root.editingTaskDescription) return false
        var hovered = contentLoader.item ? contentLoader.item.contentHovered : false
        return !hovered && !root.dragHoverActive
    }

    property real blurAmount: (root.contentLocked && !root.yatasActive) ? 1.0 : 0.0
    Behavior on blurAmount {
        NumberAnimation { duration: 150 }
    }

    readonly property int lockCloseIconGap: Math.round(root.chromeFontPixelSize * 0.4)

    readonly property bool canCloseThisWindow: windowManager.openWindowCount > 1

    function nextLockState() {
        if (hostSettings.lockState === "unlocked") return "auto-locked"
        if (hostSettings.lockState === "auto-locked") return "locked"
        return "unlocked"
    }

    Shortcut {
        sequences: [StandardKey.ZoomIn]
        onActivated: hostSettings.zoomLevel = Math.min(hostSettings.zoomLevel + 0.1, hostSettings.maxZoomLevel)
    }
    Shortcut {
        sequences: [StandardKey.ZoomOut]
        onActivated: hostSettings.zoomLevel = Math.max(hostSettings.zoomLevel - 0.1, hostSettings.minZoomLevel)
    }
    Shortcut {
        sequence: "Ctrl+0"
        onActivated: hostSettings.zoomLevel = hostSettings.defaultZoomLevel
    }

    Item {
        anchors.fill: parent
        opacity: contentLoader.item ? contentLoader.item.windowOpacity : 1.0

        Item {
            id: frostedContent
            anchors.fill: parent
            anchors.topMargin: tagLabelBg.height / 2
            clip: true

            layer.enabled: true
            layer.effect: MultiEffect {
                blurEnabled: true
                blur: root.blurAmount
                blurMax: 48
                autoPaddingEnabled: true
            }

            Rectangle {
                anchors.fill: parent
                radius: 6
                color: Theme.contentBackground
            }

            Loader {
                id: contentLoader
                anchors.fill: parent
                anchors.margins: 15
                anchors.topMargin: 15 + tagLabelBg.height / 2 + 4
                source: pluginContentUrl
                visible: !root.yatasActive
            }
        }

        Rectangle {
            anchors.fill: frostedContent
            radius: 6
            color: hostSettings.borderColor !== "" ? hostSettings.borderColor : root.chromeDragHoverColor
            opacity: root.blurAmount * 0.35
        }

        Item {
            id: contentOverlay
            x: contentLoader.x
            y: contentLoader.y
            width: contentLoader.width
            height: contentLoader.height

            MouseArea {
                id: contentBlocker
                anchors.fill: parent
                enabled: root.contentLocked
                hoverEnabled: hostSettings.lockState === "locked"
                acceptedButtons: Qt.AllButtons
                onWheel: (event) => { event.accepted = true }
            }
        }

        YatasView {
            id: yatasView
            x: contentLoader.x
            y: contentLoader.y
            width: contentLoader.width
            height: contentLoader.height
            visible: root.yatasActive
            chromeTextColor: root.chromeTextColor
            chromeMutedTextColor: root.chromeMutedTextColor
            chromeAccentColor: root.chromeAccentColor
            chromeFontFamily: root.chromeFontFamily
            chromeFontPixelSize: Math.round(root.chromeFontPixelSize * hostSettings.zoomLevel)
            chromeBoxColor: root.chromeBoxColor
            chromeFieldColor: root.chromeFieldColor
            chromeHoverColor: root.chromeHoverColor
            chromeDangerColor: root.chromeDangerColor
        }

        Rectangle {
            id: windowBorder
            anchors.fill: parent
            anchors.topMargin: tagLabelBg.height / 2
            color: "transparent"
            radius: 6
            border.color: root.dragHoverActive ? root.chromeDragHoverColor : root.chromeAccentColor
            border.width: root.dragHoverActive ? 2 : 4

            layer.enabled: !root.dragHoverActive
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: windowBorder.border.color
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.0
            }
        }

        Rectangle {
            id: tagLabelBg
            x: 14
            y: 0
            visible: !root.editingTag
            radius: 3
            color: root.chromeBoxColor(false)
            width: Math.min(tagLabelText.implicitWidth, root.width - x - 14) + 12
            height: tagLabelText.implicitHeight + 4

            Text {
                id: tagLabelText
                anchors.centerIn: parent
                width: parent.width - 12
                elide: Text.ElideRight
                horizontalAlignment: Text.AlignHCenter
                text: root.windowTag
                color: hostSettings.borderColor !== "" ? hostSettings.borderColor : root.chromeTextColor
                font.bold: true
                font.family: root.chromeFontFamily
                font.pixelSize: Math.round(root.chromeFontPixelSize * 0.8)

                layer.enabled: true
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: tagLabelText.color
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
            }

            TapHandler {
                onDoubleTapped: root.editingTag = true
            }

            DragHandler {
                target: null
                onActiveChanged: if (active) root.startSystemMove()
            }
        }

        TextField {
            id: tagEditField
            x: tagLabelBg.x
            y: 0
            width: root.width / 2 - x
            visible: root.editingTag
            text: root.windowTag
            color: root.chromeTextColor
            font.bold: true
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 0.8)
            background: Rectangle {
                radius: 4
                color: root.chromeBoxColor(false)
            }

            onVisibleChanged: if (visible) { selectAll(); forceActiveFocus() }

            function commit() {
                root.editingTag = false
                var trimmed = text.trim()
                if (trimmed.length > 0 && trimmed !== root.windowTag)
                    windowManager.renameWindow(windowId, trimmed)
            }
            onEditingFinished: commit()
            Keys.onReturnPressed: commit()
            Keys.onEscapePressed: root.editingTag = false
        }

        Rectangle {
            id: closeIconBg
            y: 0
            height: tagLabelBg.height
            radius: 3
            opacity: root.canCloseThisWindow ? 1.0 : 0.35
            color: root.chromeBoxColor(closeMouseArea.containsMouse)
            width: closeGlyph.implicitWidth + 16
            x: root.width - 14 - width

            layer.enabled: closeMouseArea.containsMouse
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: closeGlyph.color
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.08
            }

            Text {
                id: closeGlyph
                anchors.centerIn: parent
                text: "✕"
                font.bold: true
                font.pixelSize: Math.round(closeIconBg.height * 0.85)
                color: root.chromeAccentColor
            }

            MouseArea {
                id: closeMouseArea
                anchors.fill: parent
                anchors.margins: -4
                enabled: root.canCloseThisWindow
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: windowManager.closeWindow(windowId)
                ToolTip.visible: containsMouse
                ToolTip.text: qsTr("Close window")
            }
        }

        Rectangle {
            id: lockIconBg
            y: 0
            height: tagLabelBg.height
            radius: 3
            color: root.chromeBoxColor(lockMouseArea.containsMouse)
            width: lockIcon.width + 12
            x: closeIconBg.x - root.lockCloseIconGap - width

            layer.enabled: lockMouseArea.containsMouse
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: lockIcon.iconColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.08
            }

            Image {
                id: lockIcon
                readonly property string iconName: hostSettings.lockState === "locked" ? "lock_locked"
                    : hostSettings.lockState === "auto-locked" ? "lock_autolocked" : "lock_unlocked"
                readonly property color iconColor: root.chromeAccentColor

                anchors.centerIn: parent
                height: parent.height - 4
                width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                fillMode: Image.PreserveAspectFit
                smooth: true
                source: iconProvider.coloredSvgUri(iconName, iconColor.toString())
            }

            MouseArea {
                id: lockMouseArea
                anchors.fill: parent
                anchors.margins: -4
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: hostSettings.lockState = root.nextLockState()
                ToolTip.visible: containsMouse
                ToolTip.text: lockIcon.iconName === "lock_locked" ? qsTr("Locked — click to unlock")
                    : lockIcon.iconName === "lock_autolocked" ? qsTr("Auto-locked — click to lock")
                    : qsTr("Unlocked — click to auto-lock")
            }
        }

        Rectangle {
            id: yatasIconBg
            y: 0
            height: tagLabelBg.height
            radius: 3
            color: root.yatasActive ? root.chromeAccentColor : root.chromeBoxColor(yatasMouseArea.containsMouse)
            width: yatasGlyph.implicitWidth + 16
            x: lockIconBg.x - root.lockCloseIconGap - width

            layer.enabled: yatasMouseArea.containsMouse || root.yatasActive
            layer.effect: MultiEffect {
                shadowEnabled: true
                shadowColor: root.chromeAccentColor
                shadowBlur: 1.0
                shadowHorizontalOffset: 0
                shadowVerticalOffset: 0
                shadowOpacity: 1.0
                shadowScale: 1.08
            }

            Text {
                id: yatasGlyph
                anchors.centerIn: parent
                text: "Y"
                font.bold: true
                font.family: root.chromeFontFamily
                font.pixelSize: Math.round(yatasIconBg.height * 0.6)
                color: root.yatasActive ? root.chromeBoxColor(false) : root.chromeAccentColor
            }

            MouseArea {
                id: yatasMouseArea
                anchors.fill: parent
                anchors.margins: -4
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onClicked: root.yatasActive = !root.yatasActive
                ToolTip.visible: containsMouse
                ToolTip.text: qsTr("Manage windows")
            }
        }

        MouseArea {
            anchors.fill: parent
            acceptedButtons: Qt.NoButton
            onWheel: (wheel) => {
                if (!(wheel.modifiers & Qt.ControlModifier)) {
                    wheel.accepted = false
                    return
                }
                wheel.accepted = true
                var scrollingUp = wheel.angleDelta.y > 0
                var zoomIn = hostSettings.wheelZoomInverted ? !scrollingUp : scrollingUp
                if (zoomIn)
                    hostSettings.zoomLevel = Math.min(hostSettings.zoomLevel + 0.1, hostSettings.maxZoomLevel)
                else
                    hostSettings.zoomLevel = Math.max(hostSettings.zoomLevel - 0.1, hostSettings.minZoomLevel)
            }
        }
    }
}

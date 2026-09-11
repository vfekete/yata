import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects

Item {
    id: root
    required property string itemId
    required property string name
    required property bool nonWorking
    required property bool running
    required property string durationLabel
    required property bool hasAbandonedSession

    signal renamed(string itemId, string newName)
    signal startRequested(string itemId)
    signal stopRequested(string itemId)
    signal deleteRequested(string itemId, string name)
    signal nonWorkingToggled(string itemId, bool nonWorking)
    signal sessionsRequested(string itemId)

    property bool forceEditing: false
    readonly property bool editing: root.forceEditing || root.name.length === 0
    readonly property bool hovered: hoverHandler.hovered

    property string displayedDuration: root.durationLabel
    function _refreshDisplayedDuration() {
        root.displayedDuration = root.running
            ? timesheetModel.liveDurationLabel(root.itemId) : root.durationLabel
    }
    onRunningChanged: root._refreshDisplayedDuration()
    onDurationLabelChanged: root._refreshDisplayedDuration()
    Component.onCompleted: root._refreshDisplayedDuration()

    Timer {
        interval: 1000
        repeat: true
        running: root.running
        onTriggered: root._refreshDisplayedDuration()
    }

    width: ListView.view.width
    height: Math.max(40, mainRow.implicitHeight + 14)

    HoverHandler { id: hoverHandler }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? Theme.hoverColor : "transparent"
    }

    FontMetrics {
        id: durationMetrics
        font.family: Theme.fontFamily
        font.pixelSize: Theme.taskFontPixelSize
    }

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        anchors.topMargin: 6
        anchors.leftMargin: 6
        anchors.rightMargin: 6
        spacing: Math.round(Theme.taskFontPixelSize * 1.2)

        Rectangle {
            id: stateIndicator
            readonly property int diameter: Math.round(Theme.taskFontPixelSize * 0.5)
            Layout.preferredWidth: diameter
            Layout.preferredHeight: diameter
            Layout.alignment: Qt.AlignTop
            Layout.topMargin: Math.round((Theme.taskFontPixelSize - diameter) / 2)
            radius: diameter / 2
            color: root.running ? Theme.ongoingColor
                : root.hasAbandonedSession ? Theme.abandonedColor : "transparent"
        }

        Text {
            Layout.preferredWidth: durationMetrics.advanceWidth("9999:59:59")
            Layout.alignment: Qt.AlignTop
            horizontalAlignment: Text.AlignRight
            text: root.nonWorking ? "" : root.displayedDuration
            color: Theme.mutedTextColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
        }

        Text {
            id: nameText
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            visible: !root.editing
            text: root.name
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            font.italic: root.nonWorking
            wrapMode: root.hovered ? Text.Wrap : Text.NoWrap
            elide: root.hovered ? Text.ElideNone : Text.ElideRight

            TapHandler {
                onDoubleTapped: root.forceEditing = true
            }
        }

        TextField {
            id: nameField
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignTop
            visible: root.editing
            text: root.name
            placeholderText: qsTr("New work item")
            color: Theme.textColor
            font.family: Theme.fontFamily
            font.pixelSize: Theme.taskFontPixelSize
            background: Rectangle {
                radius: 4
                color: Theme.fieldColor
            }

            property bool committedViaEnter: false
            property bool suppressAutoSave: false

            onVisibleChanged: if (visible) forceActiveFocus()
            Component.onCompleted: {
                if (visible) {
                    suppressAutoSave = true
                    Qt.callLater(function() { suppressAutoSave = false })
                    forceActiveFocus()
                }
            }
            onEditingFinished: {
                if (committedViaEnter) return
                if (suppressAutoSave && root.name.length === 0) return
                root.forceEditing = false
                if (text.length > 0) {
                    root.renamed(root.itemId, text)
                } else if (root.name.length === 0) {
                    root.renamed(root.itemId, qsTr("New work item"))
                }
            }
            Keys.onReturnPressed: (event) => {
                event.accepted = true
                committedViaEnter = true
                if (text.length > 0) {
                    root.forceEditing = false
                    root.renamed(root.itemId, text)
                } else if (root.name.length === 0) {
                    root.deleteRequested(root.itemId, "")
                } else {
                    root.forceEditing = false
                }
            }
            Keys.onEscapePressed: {
                if (root.name.length === 0)
                    root.deleteRequested(root.itemId, "")
                else
                    root.forceEditing = false
            }
        }

        Row {
            visible: root.hovered && !root.editing
            Layout.alignment: Qt.AlignTop
            spacing: 10

            Image {
                id: nonWorkingIcon
                height: Math.round(Theme.taskFontPixelSize * 1.2)
                width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
                smooth: true
                source: iconProvider.coloredSvgUri("sleep_mode",
                    (nonWorkingHover.hovered ? Theme.effectiveGlowColor
                        : root.nonWorking ? Theme.borderColor : Theme.mutedTextColor).toString())
                layer.enabled: nonWorkingHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                ToolTip.visible: nonWorkingHover.hovered
                ToolTip.text: qsTr("Non-working (excluded from totals)")
                HoverHandler { id: nonWorkingHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.nonWorkingToggled(root.itemId, !root.nonWorking) }
            }

            Image {
                id: sessionsIcon
                height: Math.round(Theme.taskFontPixelSize * 1.15)
                width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
                smooth: true
                source: iconProvider.coloredSvgUri("timelist",
                    (sessionsHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor).toString())
                layer.enabled: sessionsHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                ToolTip.visible: sessionsHover.hovered
                ToolTip.text: qsTr("Edit sessions")
                HoverHandler { id: sessionsHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.sessionsRequested(root.itemId) }
            }

            Image {
                id: startStopIcon
                height: Math.round(Theme.taskFontPixelSize * 1.3)
                width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                anchors.verticalCenter: parent.verticalCenter
                fillMode: Image.PreserveAspectFit
                smooth: true
                source: iconProvider.coloredSvgUri(root.running ? "stop" : "start",
                    (startStopHover.hovered ? Theme.effectiveGlowColor : Theme.textColor).toString())
                layer.enabled: startStopHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                HoverHandler { id: startStopHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: root.running ? root.stopRequested(root.itemId) : root.startRequested(root.itemId)
                }
            }

            Text {
                id: deleteBtn
                text: "🗑"
                color: deleteHover.hovered ? Theme.effectiveGlowColor : Theme.mutedTextColor
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize * 2
                layer.enabled: deleteHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: Theme.effectiveGlowShadowColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }
                HoverHandler { id: deleteHover; cursorShape: Qt.PointingHandCursor }
                TapHandler { onTapped: root.deleteRequested(root.itemId, root.name) }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
import QtQuick.Window

Item {
    id: root

    required property color chromeTextColor
    required property color chromeMutedTextColor
    required property color chromeAccentColor
    required property string chromeFontFamily
    required property int chromeFontPixelSize
    required property var chromeBoxColor
    required property color chromeFieldColor
    required property color chromeHoverColor
    required property color chromeDangerColor

    readonly property bool contentHovered: hoverHandler.hovered
    HoverHandler { id: hoverHandler }

    readonly property string searchText: searchField.text

    property var allWindows: []
    function refresh() { root.allWindows = windowManager.listWindows() }

    onVisibleChanged: if (visible) refresh()
    Connections {
        target: windowManager
        function onWindowsChanged() { if (root.visible) root.refresh() }
    }

    readonly property var availablePlugins: windowManager.listPlugins()

    property string selectedPluginId: ""
    readonly property string _thisWindowPluginId: {
        var mine = root.allWindows.find(function(w) { return w.id === windowId })
        return mine ? mine.plugin : (root.availablePlugins.length > 0 ? root.availablePlugins[0].id : "")
    }
    onAllWindowsChanged: if (root.selectedPluginId === "") root.selectedPluginId = root._thisWindowPluginId

    readonly property int openWindowCount: root.allWindows.filter(function(w) { return w.open }).length

    readonly property var filteredWindows: {
        var needle = root.searchText.trim().toLowerCase()
        if (needle.length === 0)
            return root.allWindows
        return root.allWindows.filter(function(w) {
            return String(w.tag).toLowerCase().indexOf(needle) !== -1
        })
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                id: addBtn
                radius: 4
                color: addHover.hovered ? root.chromeHoverColor : "transparent"
                implicitWidth: addText.implicitWidth + 16
                implicitHeight: addText.implicitHeight + 8

                layer.enabled: addHover.hovered
                layer.effect: MultiEffect {
                    shadowEnabled: true
                    shadowColor: root.chromeAccentColor
                    shadowBlur: 1.0
                    shadowHorizontalOffset: 0
                    shadowVerticalOffset: 0
                    shadowOpacity: 1.0
                    shadowScale: 1.05
                }

                Text {
                    id: addText
                    anchors.centerIn: parent
                    text: qsTr("Add")
                    font.bold: true
                    font.family: root.chromeFontFamily
                    font.pixelSize: root.chromeFontPixelSize
                    font.capitalization: Font.AllUppercase
                    color: root.chromeTextColor
                }

                HoverHandler { id: addHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: windowManager.createWindow({
                        plugin: root.selectedPluginId,
                        themeMode: appSettings.themeMode,
                        themeTint: appSettings.themeTint,
                        opacityPercent: appSettings.opacityPercent,
                        zoomLevel: hostSettings.zoomLevel,
                        wheelZoomInverted: hostSettings.wheelZoomInverted,
                        x: root.Window.window.x,
                        y: root.Window.window.y,
                        width: root.Window.window.width,
                        height: root.Window.window.height
                    })
                }
            }

            ComboBox {
                id: pluginCombo
                visible: root.availablePlugins.length > 1
                model: root.availablePlugins
                textRole: "displayName"
                valueRole: "id"
                Layout.preferredWidth: Math.max(120, implicitWidth)
                font.family: root.chromeFontFamily
                font.pixelSize: root.chromeFontPixelSize

                currentIndex: {
                    for (var i = 0; i < root.availablePlugins.length; i++)
                        if (root.availablePlugins[i].id === root.selectedPluginId) return i
                    return -1
                }
                onActivated: root.selectedPluginId = currentValue
            }

            TextField {
                id: searchField
                Layout.fillWidth: true
                Layout.leftMargin: addBtn.width / 2
                placeholderText: qsTr("Search windows")
                placeholderTextColor: root.chromeMutedTextColor
                leftPadding: searchIcon.width + 12
                color: root.chromeTextColor
                font.family: root.chromeFontFamily
                font.pixelSize: root.chromeFontPixelSize
                background: Rectangle {
                    radius: 4
                    color: root.chromeFieldColor
                }

                Image {
                    id: searchIcon
                    source: iconProvider.coloredSvgUri("search", root.chromeMutedTextColor.toString())
                    fillMode: Image.PreserveAspectFit
                    smooth: true
                    height: Math.round(root.chromeFontPixelSize * 1.15)
                    width: implicitHeight > 0 ? Math.round(height * implicitWidth / implicitHeight) : height
                    anchors.left: parent.left
                    anchors.leftMargin: 6
                    anchors.verticalCenter: parent.verticalCenter
                }
            }
        }

        ListView {
            id: windowsList
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            spacing: 0
            model: root.filteredWindows
            ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

            delegate: YatasRow {
                required property var modelData
                width: windowsList.width
                windowId: modelData.id
                tag: modelData.tag
                open: modelData.open
                deleted: modelData.deleted
                borderColor: modelData.borderColor
                openWindowCount: root.openWindowCount
                chromeTextColor: root.chromeTextColor
                chromeMutedTextColor: root.chromeMutedTextColor
                chromeAccentColor: root.chromeAccentColor
                chromeFontFamily: root.chromeFontFamily
                chromeFontPixelSize: root.chromeFontPixelSize
                chromeBoxColor: root.chromeBoxColor
                chromeFieldColor: root.chromeFieldColor
                chromeHoverColor: root.chromeHoverColor
                chromeDangerColor: root.chromeDangerColor
                onRenamed: (id, newTag) => windowManager.renameWindow(id, newTag)
                onDeleteRequested: (id, tag) => deleteDialog.openFor(id, tag)
                onShowToggled: (id, show) => show ? windowManager.openWindow(id) : windowManager.closeWindow(id)
                onRecreateRequested: (id) => windowManager.recreateWindow(id)
                onPurgeRequested: (id, tag) => purgeDialog.openFor(id, tag)
                onBorderColorPicked: (id, color) => windowManager.setBorderColor(id, color)
            }
        }

        Text {
            Layout.alignment: Qt.AlignHCenter
            visible: root.filteredWindows.length === 0
            text: root.allWindows.length === 0 ? qsTr("No windows") : qsTr("No windows match your search")
            color: root.chromeMutedTextColor
            font.family: root.chromeFontFamily
            font.pixelSize: root.chromeFontPixelSize
        }
    }

    DeleteWindowDialog {
        id: deleteDialog
        chromeTextColor: root.chromeTextColor
        chromeMutedTextColor: root.chromeMutedTextColor
        chromeAccentColor: root.chromeAccentColor
        chromeFontFamily: root.chromeFontFamily
        chromeFontPixelSize: root.chromeFontPixelSize
        chromeBoxColor: root.chromeBoxColor
        onConfirmed: (id) => windowManager.deleteWindow(id)
    }

    PurgeWindowDialog {
        id: purgeDialog
        chromeTextColor: root.chromeTextColor
        chromeMutedTextColor: root.chromeMutedTextColor
        chromeAccentColor: root.chromeAccentColor
        chromeFontFamily: root.chromeFontFamily
        chromeFontPixelSize: root.chromeFontPixelSize
        chromeBoxColor: root.chromeBoxColor
        onConfirmed: (id) => windowManager.purgeWindow(id)
    }
}

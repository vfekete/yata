import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

// The window-management view (r-3.md's original "YATAS" feature, r-9.md's
// plugin architecture initially carried it into plugins/simple_task_list/
// alongside everything else — moved back out to host chrome afterward,
// since managing windows is inherently the master application's job, not
// any one plugin's, and must stay available no matter which plugin a
// window happens to be running. Shown instead of Main.qml's contentLoader
// when Main.qml's own "Y" chrome icon is active. Styled entirely off the
// fixed chrome palette passed down from Main.qml — not any plugin's Theme
// — for the same "chrome must look the same regardless of plugin" reason
// Main.qml's border/lock/close/title already do.
//
// Every known YATA window (id + tag), across the whole registry — not just
// ones currently open (r-3.md: you can rename/delete a window that isn't
// running right now).
Item {
    id: root

    required property color chromeTextColor
    required property color chromeMutedTextColor
    required property color chromeAccentColor
    required property string chromeFontFamily
    required property int chromeFontPixelSize
    required property var chromeBoxColor

    // Read back by Main.qml the same way it reads contentLoader.item's
    // contentHovered — auto-locked's hover-to-unlock check needs to know
    // when the mouse is over WHATEVER is actually showing right now, this
    // view included.
    readonly property bool contentHovered: hoverHandler.hovered
    HoverHandler { id: hoverHandler }

    property bool showActive: true
    property bool showDeleted: false
    property string sortMode: ""
    readonly property string searchText: searchField.text

    property var allWindows: []
    function refresh() { root.allWindows = windowManager.listWindows() }

    onVisibleChanged: if (visible) refresh()
    Connections {
        target: windowManager
        function onWindowsChanged() { if (root.visible) root.refresh() }
    }

    // Passed down to every row so it can hide its own SHOW toggle when
    // it's the last open window — closing it would leave nothing on
    // screen and no YatasView left to reopen anything from.
    readonly property int openWindowCount: root.allWindows.filter(function(w) { return w.open }).length

    readonly property var filteredWindows: {
        var needle = root.searchText.trim().toLowerCase()
        var items = root.allWindows.filter(function(w) {
            if (w.deleted ? !root.showDeleted : !root.showActive)
                return false
            if (needle.length > 0 && String(w.tag).toLowerCase().indexOf(needle) === -1)
                return false
            return true
        })
        // Stable sort — brings the selected category to the top while
        // leaving each category's own relative order (registry order)
        // unchanged otherwise.
        if (root.sortMode === "active" || root.sortMode === "deleted") {
            var wantDeleted = root.sortMode === "deleted"
            items = items.slice().sort(function(a, b) {
                return (a.deleted === wantDeleted ? 0 : 1) - (b.deleted === wantDeleted ? 0 : 1)
            })
        }
        return items
    }

    // Small reusable toggle pill for the Active/Deleted visibility+sort
    // rows below — same look as the plugin's own FilterButton.qml (glow on
    // hover/active) but chrome-styled, not Theme-styled.
    component ChromeToggle: Item {
        id: toggle
        property string label: ""
        property bool active: false
        signal toggled(bool newChecked)

        implicitWidth: toggleText.implicitWidth + 8
        implicitHeight: toggleText.implicitHeight + 2

        HoverHandler { id: toggleHover; cursorShape: Qt.PointingHandCursor }
        TapHandler { onTapped: toggle.toggled(!toggle.active) }

        Text {
            id: toggleText
            anchors.centerIn: parent
            text: toggle.label
            font.family: root.chromeFontFamily
            font.pixelSize: Math.round(root.chromeFontPixelSize * 0.75)
            font.capitalization: Font.AllUppercase
            color: toggleHover.hovered ? root.chromeAccentColor
                   : (toggle.active ? root.chromeAccentColor : root.chromeMutedTextColor)
        }
    }

    ColumnLayout {
        anchors.fill: parent
        spacing: 8

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            // "add a new window" lives here now, not the plugin's toolbar
            // ADD button — window creation is window management. Clones
            // the CREATING window's own theme/zoom onto the new one
            // (explicit r-3.md requirement: "new window has same theme as
            // the actual window") — appSettings here is still this
            // window's own plugin content settings; reachable from any
            // depth in this window's tree since it's a plain context
            // property, not something only the plugin's own QML can see.
            Rectangle {
                id: addBtn
                radius: 4
                color: root.chromeBoxColor(addHover.hovered)
                implicitWidth: addText.implicitWidth + 16
                implicitHeight: addText.implicitHeight + 8

                Text {
                    id: addText
                    anchors.centerIn: parent
                    text: qsTr("+ New Window")
                    color: root.chromeTextColor
                    font.family: root.chromeFontFamily
                    font.pixelSize: root.chromeFontPixelSize
                }

                HoverHandler { id: addHover; cursorShape: Qt.PointingHandCursor }
                TapHandler {
                    onTapped: windowManager.createWindow({
                        themeMode: appSettings.themeMode,
                        themeTint: appSettings.themeTint,
                        opacityPercent: appSettings.opacityPercent,
                        fontScale: appSettings.fontScale,
                        wheelZoomInverted: appSettings.wheelZoomInverted,
                        x: root.Window.window.x,
                        y: root.Window.window.y,
                        width: root.Window.window.width,
                        height: root.Window.window.height
                    })
                }
            }

            TextField {
                id: searchField
                Layout.fillWidth: true
                placeholderText: qsTr("Search windows")
                color: root.chromeTextColor
                font.family: root.chromeFontFamily
                font.pixelSize: root.chromeFontPixelSize
                background: Rectangle {
                    radius: 4
                    color: root.chromeBoxColor(false)
                }
            }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 18

            RowLayout {
                spacing: 8
                ChromeToggle {
                    label: qsTr("Active")
                    active: root.showActive
                    onToggled: (checked) => root.showActive = checked
                }
                ChromeToggle {
                    label: qsTr("Deleted")
                    active: root.showDeleted
                    onToggled: (checked) => root.showDeleted = checked
                }
            }

            RowLayout {
                spacing: 8
                ChromeToggle {
                    label: qsTr("Sort active first")
                    active: root.sortMode === "active"
                    onToggled: (checked) => root.sortMode = checked ? "active" : ""
                }
                ChromeToggle {
                    label: qsTr("Sort deleted first")
                    active: root.sortMode === "deleted"
                    onToggled: (checked) => root.sortMode = checked ? "deleted" : ""
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
            text: root.allWindows.length === 0 ? qsTr("No windows") : qsTr("No windows match your search or filters")
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

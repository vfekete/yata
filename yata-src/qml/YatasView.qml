import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Effects
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
    required property color chromeFieldColor
    required property color chromeHoverColor
    required property color chromeDangerColor

    // Read back by Main.qml the same way it reads contentLoader.item's
    // contentHovered — auto-locked's hover-to-unlock check needs to know
    // when the mouse is over WHATEVER is actually showing right now, this
    // view included.
    readonly property bool contentHovered: hoverHandler.hovered
    HoverHandler { id: hoverHandler }

    // Deliberately no background Rectangle of its own here (there used to
    // be one, solid near-black) — this view sits directly on top of
    // frostedContent's own themed wash (Theme.contentBackground), the same
    // panel the plugin's own content normally shows through, so leaving
    // this transparent makes it look exactly like that panel: explicit
    // "total resemblance" request. Safe to do now that Main.qml freezes
    // blurAmount at 0 whenever this view is showing (see its own comment
    // there) — there is no blur/tint left to bleed through anymore, which
    // is what the old solid background used to guard against.
    readonly property string searchText: searchField.text

    property var allWindows: []
    function refresh() { root.allWindows = windowManager.listWindows() }

    onVisibleChanged: if (visible) refresh()
    Connections {
        target: windowManager
        function onWindowsChanged() { if (root.visible) root.refresh() }
    }

    // Every statically-registered plugin (r-10.md: added once a second
    // one, "timesheet", existed to actually choose between) — backs the
    // Add button's own plugin picker below. Fetched once; the set of
    // available plugins is fixed for the lifetime of one running process
    // (statically linked, see plugins_registry.py), no need to react to
    // windowsChanged for this.
    readonly property var availablePlugins: windowManager.listPlugins()

    // Defaults to whichever plugin THIS window itself runs — most "add
    // another window" clicks want the same kind — re-derived from
    // allWindows (which already carries each entry's own "plugin" field,
    // see WindowRegistry.list()) rather than duplicating that lookup via
    // a separate host call. Re-picking a different value in the combo box
    // below overrides this until YatasView is closed and reopened.
    property string selectedPluginId: ""
    readonly property string _thisWindowPluginId: {
        var mine = root.allWindows.find(function(w) { return w.id === windowId })
        return mine ? mine.plugin : (root.availablePlugins.length > 0 ? root.availablePlugins[0].id : "")
    }
    onAllWindowsChanged: if (root.selectedPluginId === "") root.selectedPluginId = root._thisWindowPluginId

    // Passed down to every row so it can hide its own SHOW toggle when
    // it's the last open window — closing it would leave nothing on
    // screen and no YatasView left to reopen anything from.
    readonly property int openWindowCount: root.allWindows.filter(function(w) { return w.open }).length

    // Just the list of windows, search-filtered — no separate visibility/
    // sort controls (explicit request: "no reason for ACTIVE/DELETE/SORT
    // actions, only list of windows"). Both active and deleted windows
    // always show together, in registry order; each row's own button set
    // (delete vs. recreate/purge, see YatasRow.qml) already makes clear
    // which category a row is in.
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

            // "add a new window" lives here now, not the plugin's toolbar
            // ADD button — window creation is window management. Clones
            // the CREATING window's own theme/zoom onto the new one
            // (explicit r-3.md requirement: "new window has same theme as
            // the actual window") — appSettings here is still this
            // window's own plugin content settings; reachable from any
            // depth in this window's tree since it's a plain context
            // property, not something only the plugin's own QML can see.
            // Same "Add"/bold/all-caps look as the plugin's own toolbar
            // ADD button, for visual consistency across the boundary —
            // including its background: transparent at rest, a subtle
            // translucent overlay on hover (chromeHoverColor, not the
            // solid chromeBoxColor lock/close/tag-rename use) — that's
            // the plugin toolbar's own convention for buttons sitting
            // inside a content panel, and the "before" look this needs to
            // match now that it's host-owned.
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
                        // Zoom is host-owned now (yata-src/settings.py) —
                        // cloned from hostSettings, not the plugin's own
                        // appSettings, same as borderColor already is.
                        zoomLevel: hostSettings.zoomLevel,
                        wheelZoomInverted: hostSettings.wheelZoomInverted,
                        x: root.Window.window.x,
                        y: root.Window.window.y,
                        width: root.Window.window.width,
                        height: root.Window.window.height
                    })
                }
            }

            // Which plugin the next ADD creates — r-10.md: previously
            // always simple_task_list regardless of what this window
            // itself was running. Only shown once there's an actual
            // choice to make.
            ComboBox {
                id: pluginCombo
                visible: root.availablePlugins.length > 1
                model: root.availablePlugins
                textRole: "displayName"
                valueRole: "id"
                Layout.preferredWidth: Math.max(120, implicitWidth)
                font.family: root.chromeFontFamily
                font.pixelSize: root.chromeFontPixelSize

                // A plain search over root.availablePlugins/selectedPluginId
                // directly, NOT indexOfValue(root.selectedPluginId) (tried
                // first): QML's binding dependency tracker doesn't see
                // through a method call into what THAT method reads
                // internally (pluginCombo's own model/valueRole), so a
                // currentIndex binding built on indexOfValue() never
                // re-evaluated once those settled into place — confirmed
                // live, currentIndex stayed -1 no matter what
                // selectedPluginId held. Reading availablePlugins/
                // selectedPluginId directly in this expression makes both
                // real, tracked dependencies instead.
                //
                // ComboBox's own internal click-handling sets currentIndex
                // imperatively once the user actually picks something,
                // which breaks this binding going forward — harmless here,
                // since onActivated below is what keeps selectedPluginId in
                // sync after that point, not the other way around.
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
                // Shifted right by half the ADD button's own width —
                // explicit follow-up request — rather than sitting flush
                // against it.
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

                // Same static "lupe" convention the plugin's own Toolbar
                // search field uses, just chrome-styled/iconProvider-
                // sourced directly rather than via the plugin's
                // IconIndicator.qml (which sizes itself off the plugin's
                // own, zoomable Theme.taskFontPixelSize — not appropriate
                // for host chrome).
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

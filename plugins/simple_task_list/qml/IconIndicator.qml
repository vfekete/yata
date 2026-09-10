import QtQuick
import QtQuick.Layouts

// Small non-interactive icon: prefixes a group of toggle buttons in
// FilterBar (e.g. a calendar icon before the Day/Month buttons), and also
// used standalone (not inside a Layout) as the search field's lupe icon in
// Toolbar.qml.
//
// Recolored by substituting a %FILLCOLOR% placeholder baked into the root
// <svg fill="..."> of each source file (see resources/assets/*.svg), via
// iconProvider.coloredSvgUri() (yata-src/icons.py, a context property set in
// main.py) rather than a GPU shader effect — MultiEffect's colorization did
// not reliably recolor these on a live run (rendered as flat unrecolored
// black), even though MultiEffect's shadow/glow effect elsewhere in this
// codebase does work, so this sidesteps that entirely. QML's own
// XMLHttpRequest was tried first and rejected: it refuses to read qrc:
// resources unless the process-wide QML_XHR_ALLOW_FILE_READ=1 escape hatch
// is set, which is a broader opt-out than wanted just for this.
//
// Box height is fixed (scales with the task font), but box WIDTH follows
// each icon's own aspect ratio (read back from the loaded image's
// implicitWidth/implicitHeight) rather than forcing every icon into the same
// square. A forced square left narrow icons (e.g. the arrow-up-down order
// icon) with dead horizontal padding inside their box, which made the gap
// to the following button look wider than for a squarer icon (calendar,
// visibility) even at identical spacing — sizing the box to the icon's
// actual proportions removes that dead space instead of needing a manual
// per-icon spacing fudge.
//
// Sizing uses BOTH plain width/height AND Layout.preferredWidth/Height:
// a RowLayout child's own width/height bindings get silently overwritten by
// the layout's own positioning pass (Layout.preferredWidth/Height is the
// real hook there), but outside a Layout (the Toolbar search-icon case)
// nothing overwrites plain width/height, so both are needed depending on
// where this is used. boxWidth/boxHeight are independent properties (not
// aliases of width/height) specifically so neither binding is self-
// referential/circular.
Image {
    id: root
    property string iconName: ""
    property color tint: Theme.mutedTextColor
    // Multiplies the base 1.15-of-task-font size — lets one call site (e.g.
    // FilterBar's group icons) run smaller without affecting other uses of
    // this same component (e.g. Toolbar's search icon).
    property real sizeScale: 1.0
    readonly property int boxHeight: Math.round(Theme.taskFontPixelSize * 1.15 * sizeScale)
    readonly property int boxWidth: implicitHeight > 0
        ? Math.round(boxHeight * implicitWidth / implicitHeight)
        : boxHeight

    Layout.alignment: Qt.AlignVCenter
    width: boxWidth
    height: boxHeight
    Layout.preferredWidth: boxWidth
    Layout.preferredHeight: boxHeight
    fillMode: Image.PreserveAspectFit
    smooth: true

    source: iconName ? iconProvider.coloredSvgUri(iconName, tint.toString()) : ""
}

import QtQuick
import QtQuick.Layouts

Image {
    id: root
    property string iconName: ""
    property color tint: Theme.mutedTextColor
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

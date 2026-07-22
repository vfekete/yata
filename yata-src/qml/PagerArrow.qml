import QtQuick

// Prev/next arrow used by MonthView/YearView's pagination header.
Text {
    id: root
    property string symbol: "‹"
    signal clicked()

    text: symbol
    font.bold: true
    font.family: Theme.fontFamily
    font.pixelSize: Math.round(Theme.taskFontPixelSize * 1.5)
    color: hh.hovered ? Theme.accentColor : Theme.mutedTextColor
    padding: 8

    HoverHandler { id: hh; cursorShape: Qt.PointingHandCursor }
    TapHandler { onTapped: root.clicked() }
}

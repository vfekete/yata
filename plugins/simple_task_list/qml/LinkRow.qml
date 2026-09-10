import QtQuick
import QtQuick.Layouts

// One row in LinksView: every link the task mentions (shown by label, not
// raw URL — clickable, opens in the default browser), its status tag
// beneath (mirrors TaskDelegate.qml's task-name-then-status-label stacking,
// not side-by-side), and a "to task" button at the end. Mirrors
// TaskDelegate.qml's row structure otherwise (hover highlight, height
// tracking content) for visual consistency with the main task list.
Item {
    id: root
    required property string taskId
    required property string status
    required property string completedAt
    required property var links  // [{label, url}, ...]
    signal toTaskClicked(string taskId)

    readonly property bool hovered: hoverHandler.hovered

    width: ListView.view.width
    height: Math.max(30, mainRow.implicitHeight + 12)

    HoverHandler { id: hoverHandler }

    Rectangle {
        anchors.fill: parent
        radius: 4
        color: root.hovered ? Theme.hoverColor : "transparent"
    }

    RowLayout {
        id: mainRow
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.verticalCenter: parent.verticalCenter
        anchors.leftMargin: 4
        anchors.rightMargin: 4
        spacing: 10

        Column {
            Layout.fillWidth: true
            Layout.alignment: Qt.AlignVCenter
            spacing: 2

            Text {
                id: linksText
                width: parent.width
                textFormat: Text.StyledText
                wrapMode: Text.Wrap
                font.family: Theme.fontFamily
                font.pixelSize: Theme.taskFontPixelSize
                color: Theme.textColor
                text: {
                    var parts = []
                    for (var i = 0; i < root.links.length; i++) {
                        var link = root.links[i]
                        var label = String(link.label).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                        var url = String(link.url).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
                        parts.push('<a href="' + url + '"><font color="' + Theme.effectiveLinkColor + '">' + label + '</font></a>')
                    }
                    return parts.join(', ')
                }
                onLinkActivated: (link) => Qt.openUrlExternally(link)

                HoverHandler {
                    cursorShape: linksText.hoveredLink ? Qt.PointingHandCursor : Qt.ArrowCursor
                }
            }

            StatusTag {
                width: parent.width
                status: root.status
                completedAt: root.completedAt
            }
        }

        LinkToTaskButton {
            // 8px further from the row's right edge than a plain trailing
            // item would sit — i.e. moved 8px left, per explicit request.
            Layout.rightMargin: 8
            onClicked: root.toTaskClicked(root.taskId)
        }
    }
}

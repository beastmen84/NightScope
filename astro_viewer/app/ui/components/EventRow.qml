import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var eventData
    property color accentColor: theme.amber
    property color visibilityAccentColor: theme.teal
    property bool hovered: false

    signal clicked()

    AppTheme {
        id: theme
    }

    Layout.fillWidth: true
    implicitHeight: 124
    radius: 8
    color: root.hovered ? theme.withAlpha(root.accentColor, 0.12) : theme.surface
    border.color: root.hovered ? theme.withAlpha(root.accentColor, 0.55) : theme.border
    border.width: 1

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onEntered: root.hovered = true
        onExited: root.hovered = false
        onClicked: root.clicked()
    }

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 14

        Rectangle {
            Layout.preferredWidth: 104
            Layout.preferredHeight: 72
            radius: 8
            color: theme.withAlpha(root.accentColor, 0.14)
            border.color: theme.withAlpha(root.accentColor, 0.45)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 3

                Text {
                    Layout.fillWidth: true
                    text: root.eventData.dateLabel
                    color: root.accentColor
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 2
                }

                Text {
                    Layout.fillWidth: true
                    text: root.eventData.compactTimingValue || root.eventData.timingValue
                color: theme.textSecondary
                    font.pixelSize: 11
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6

            Text {
                Layout.fillWidth: true
                text: root.eventData.title
                color: theme.textPrimary
                font.pixelSize: 15
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                StatusPill {
                    text: root.eventData.type
                    accentColor: root.accentColor
                }

                StatusPill {
                    text: root.eventData.visibilityLabel
                    accentColor: root.visibilityAccentColor
                }

                Item { Layout.fillWidth: true }
            }

            Text {
                Layout.fillWidth: true
                text: root.eventData.observingWindow.length > 0
                      ? root.eventData.observingWindow
                      : root.eventData.visibilityDetail
                color: theme.textMuted
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }
        }
    }
}

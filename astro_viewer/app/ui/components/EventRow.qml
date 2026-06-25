import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var eventData
    property color accentColor: "#f6c768"
    property bool hovered: false

    signal clicked()

    Layout.fillWidth: true
    implicitHeight: 112
    radius: 8
    color: root.hovered ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.12) : "#171a20"
    border.color: root.hovered ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.55) : "#303641"
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
            Layout.preferredWidth: 88
            Layout.preferredHeight: 68
            radius: 8
            color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.14)
            border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.45)

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 8
                spacing: 3

                Text {
                    Layout.fillWidth: true
                    text: root.eventData.date_label
                    color: root.accentColor
                    font.pixelSize: 12
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                Text {
                    Layout.fillWidth: true
                    text: root.eventData.best_time
                    color: "#aeb7c4"
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
                color: "#f4f7fb"
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

                Text {
                    Layout.fillWidth: true
                    text: root.eventData.setup
                    color: "#aeb7c4"
                    font.pixelSize: 12
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }
            }

            Text {
                Layout.fillWidth: true
                text: root.eventData.note
                color: "#788391"
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }
        }

        Rectangle {
            Layout.preferredWidth: 44
            Layout.preferredHeight: 44
            radius: 8
            color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.10)
            border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.35)

            Text {
                anchors.centerIn: parent
                text: root.eventData.usefulness
                color: root.accentColor
                font.pixelSize: 15
                font.weight: Font.DemiBold
            }
        }
    }
}

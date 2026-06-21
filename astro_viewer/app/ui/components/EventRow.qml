import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var eventData
    property color accentColor: "#f6c768"

    Layout.fillWidth: true
    implicitHeight: 88
    radius: 8
    color: "#171a20"
    border.color: "#303641"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.margins: 14
        spacing: 14

        Rectangle {
            Layout.preferredWidth: 52
            Layout.preferredHeight: 52
            radius: 8
            color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.14)
            border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.45)

            Text {
                anchors.centerIn: parent
                text: root.eventData.usefulness
                color: root.accentColor
                font.pixelSize: 16
                font.weight: Font.DemiBold
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 4

            Text {
                Layout.fillWidth: true
                text: root.eventData.title
                color: "#f4f7fb"
                font.pixelSize: 15
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: root.eventData.type + "  -  " + root.eventData.date_label + "  -  " + root.eventData.best_time
                color: "#aeb7c4"
                font.pixelSize: 12
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: root.eventData.note
                color: "#788391"
                font.pixelSize: 12
                elide: Text.ElideRight
            }
        }
    }
}


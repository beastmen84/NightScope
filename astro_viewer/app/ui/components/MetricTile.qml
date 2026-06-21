import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property string label: ""
    property string value: ""
    property color accentColor: "#65d6e8"

    radius: 8
    color: "#20242b"
    border.color: "#303641"
    border.width: 1
    implicitHeight: 78
    Layout.fillWidth: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 4

        Text {
            Layout.fillWidth: true
            text: root.label
            color: "#aeb7c4"
            font.pixelSize: 11
            elide: Text.ElideRight
        }

        Text {
            Layout.fillWidth: true
            text: root.value
            color: "#f4f7fb"
            font.pixelSize: 18
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 2
            radius: 1
            color: root.accentColor
            opacity: 0.75
        }
    }
}


import QtQuick
import QtQuick.Layouts

RowLayout {
    id: root

    property int stepNumber: 1
    property string description: ""
    property color accentColor: "#65d6e8"

    Layout.fillWidth: true
    Layout.minimumWidth: 0
    spacing: 10

    Rectangle {
        Layout.preferredWidth: 24
        Layout.preferredHeight: 24
        Layout.alignment: Qt.AlignTop
        radius: 12
        color: "#20242b"
        border.color: root.accentColor
        border.width: 1

        Text {
            anchors.centerIn: parent
            text: root.stepNumber
            color: root.accentColor
            font.pixelSize: 11
            font.weight: Font.DemiBold
        }
    }

    Text {
        Layout.fillWidth: true
        Layout.minimumWidth: 0
        text: root.description
        color: "#aeb7c4"
        font.pixelSize: 13
        wrapMode: Text.WordWrap
        lineHeight: 1.15
    }
}

import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property string text: ""
    property color accentColor: "#65d6e8"

    radius: 8
    color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.14)
    border.color: Qt.rgba(accentColor.r, accentColor.g, accentColor.b, 0.45)
    border.width: 1
    implicitWidth: label.implicitWidth + 20
    implicitHeight: 30

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.accentColor
        font.pixelSize: 12
        font.weight: Font.DemiBold
        elide: Text.ElideRight
        maximumLineCount: 1
    }
}


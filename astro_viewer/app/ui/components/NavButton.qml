import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property string text: ""
    property string iconSource: ""
    property bool selected: false
    signal clicked()

    height: 40
    radius: 8
    color: selected ? "#27313b" : (mouseArea.containsMouse ? "#1f242c" : "transparent")
    border.color: selected ? "#465260" : "transparent"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 10

        Image {
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            source: root.iconSource
            sourceSize.width: 20
            sourceSize.height: 20
        }

        Text {
            Layout.fillWidth: true
            text: root.text
            color: root.selected ? "#f4f7fb" : "#aeb7c4"
            font.pixelSize: 14
            font.weight: root.selected ? Font.DemiBold : Font.Normal
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.clicked()
    }
}

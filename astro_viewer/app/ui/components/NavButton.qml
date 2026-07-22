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
    AppTheme {
        id: theme
    }

    color: selected ? theme.navSelected : (mouseArea.containsMouse ? theme.navHover : "transparent")
    border.color: selected ? theme.navSelectedBorder : "transparent"
    border.width: 1

    RowLayout {
        anchors.fill: parent
        anchors.leftMargin: 14
        anchors.rightMargin: 14
        spacing: 10

        NightVisionIcon {
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            source: root.iconSource
        }

        Text {
            Layout.fillWidth: true
            text: root.text
            color: root.selected ? theme.textPrimary : theme.textSecondary
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

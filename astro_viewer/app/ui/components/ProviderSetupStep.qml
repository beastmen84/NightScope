import QtQuick
import QtQuick.Layouts

RowLayout {
    id: root

    property int stepNumber: 1
    property string description: ""
    property color accentColor: theme.cyan

    AppTheme {
        id: theme
    }

    Layout.fillWidth: true
    Layout.minimumWidth: 0
    spacing: 10

    Rectangle {
        Layout.preferredWidth: 24
        Layout.preferredHeight: 24
        Layout.alignment: Qt.AlignTop
        radius: 12
        color: theme.surfaceRaised
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
        color: theme.textSecondary
        font.pixelSize: 13
        wrapMode: Text.WordWrap
        lineHeight: 1.15
    }
}

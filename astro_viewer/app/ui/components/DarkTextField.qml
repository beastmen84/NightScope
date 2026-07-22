import QtQuick
import QtQuick.Controls

TextField {
    id: root

    property string labelText: ""

    implicitHeight: root.labelText.length > 0 ? 58 : 40
    leftPadding: 12
    rightPadding: 12
    topPadding: root.labelText.length > 0 ? 22 : 6
    bottomPadding: 6
    color: theme.textPrimary
    placeholderTextColor: theme.textMuted
    selectedTextColor: theme.background
    selectionColor: theme.cyan
    font.pixelSize: 14

    AppTheme {
        id: theme
    }

    background: Rectangle {
        radius: 8
        color: root.enabled ? theme.field : theme.surface
        border.color: root.activeFocus ? theme.cyan : theme.border
        border.width: 1

        Text {
            visible: root.labelText.length > 0
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 12
            anchors.rightMargin: 12
            anchors.topMargin: 6
            text: root.labelText
            color: theme.textMuted
            font.pixelSize: 10
            elide: Text.ElideRight
            maximumLineCount: 1
        }
    }
}

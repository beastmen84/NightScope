import QtQuick
import QtQuick.Controls

TextField {
    id: root

    implicitHeight: 40
    leftPadding: 12
    rightPadding: 12
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
        color: root.enabled ? "#1c222b" : "#171a20"
        border.color: root.activeFocus ? theme.cyan : "#303641"
        border.width: 1
    }
}

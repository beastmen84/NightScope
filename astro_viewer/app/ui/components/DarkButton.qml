import QtQuick
import QtQuick.Controls

Button {
    id: root

    property color accentColor: theme.cyan
    property bool danger: false

    implicitHeight: 38
    leftPadding: 14
    rightPadding: 14
    topPadding: 8
    bottomPadding: 8

    AppTheme {
        id: theme
    }

    contentItem: Text {
        text: root.text
        color: !root.enabled ? theme.textMuted : root.checked ? theme.background : theme.textPrimary
        font.pixelSize: 13
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        maximumLineCount: 1
    }

    background: Rectangle {
        radius: 8
        color: {
            if (!root.enabled)
                return "#191d23"
            if (root.checked)
                return root.danger ? theme.red : root.accentColor
            if (root.down)
                return "#2a313b"
            if (root.hovered)
                return "#252b34"
            return "#20242b"
        }
        border.color: {
            if (!root.enabled)
                return "#262c35"
            if (root.checked)
                return root.danger ? theme.red : root.accentColor
            if (root.danger)
                return Qt.rgba(theme.red.r, theme.red.g, theme.red.b, 0.58)
            return "#303641"
        }
        border.width: 1
    }
}

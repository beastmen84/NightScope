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
                return theme.surfaceDisabledHover
            if (root.checked)
                return root.danger ? theme.red : root.accentColor
            if (root.down)
                return theme.surfacePressed
            if (root.hovered)
                return theme.surfaceHover
            return theme.surfaceRaised
        }
        border.color: {
            if (!root.enabled)
                return theme.surfaceDestructiveHover
            if (root.checked)
                return root.danger ? theme.red : root.accentColor
            if (root.danger)
                return theme.withAlpha(theme.red, 0.58)
            return theme.border
        }
        border.width: 1
    }
}

import QtQuick
import QtQuick.Controls

SpinBox {
    id: root

    property color accentColor: theme.cyan

    implicitHeight: 40

    AppTheme {
        id: theme
    }

    contentItem: TextInput {
        z: 2
        text: root.textFromValue(root.value, root.locale)
        font: root.font
        color: root.enabled ? theme.textPrimary : theme.textMuted
        selectionColor: theme.cyan
        selectedTextColor: theme.background
        horizontalAlignment: Qt.AlignHCenter
        verticalAlignment: Qt.AlignVCenter
        readOnly: !root.editable
        validator: root.validator
        inputMethodHints: Qt.ImhFormattedNumbersOnly
    }

    up.indicator: Rectangle {
        x: root.mirrored ? 0 : parent.width - width
        height: parent.height
        width: 34
        color: root.up.pressed ? "#2a313b" : root.up.hovered ? "#252b34" : "transparent"

        Text {
            anchors.centerIn: parent
            text: "+"
            color: root.enabled ? root.accentColor : theme.textMuted
            font.pixelSize: 16
            font.weight: Font.DemiBold
        }
    }

    down.indicator: Rectangle {
        x: root.mirrored ? parent.width - width : 0
        height: parent.height
        width: 34
        color: root.down.pressed ? "#2a313b" : root.down.hovered ? "#252b34" : "transparent"

        Text {
            anchors.centerIn: parent
            text: "-"
            color: root.enabled ? root.accentColor : theme.textMuted
            font.pixelSize: 16
            font.weight: Font.DemiBold
        }
    }

    background: Rectangle {
        radius: 8
        color: root.enabled ? "#1c222b" : "#171a20"
        border.color: root.activeFocus ? root.accentColor : "#303641"
        border.width: 1
    }
}

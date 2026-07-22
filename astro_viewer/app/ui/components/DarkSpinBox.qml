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
            color: root.up.pressed ? theme.surfacePressed
                                   : root.up.hovered ? theme.surfaceHover : "transparent"

        Text {
            anchors.centerIn: parent
            text: qsTr("+")
            color: root.enabled ? root.accentColor : theme.textMuted
            font.pixelSize: 16
            font.weight: Font.DemiBold
        }
    }

    down.indicator: Rectangle {
        x: root.mirrored ? parent.width - width : 0
        height: parent.height
        width: 34
            color: root.down.pressed ? theme.surfacePressed
                                     : root.down.hovered ? theme.surfaceHover : "transparent"

        Text {
            anchors.centerIn: parent
            text: qsTr("-")
            color: root.enabled ? root.accentColor : theme.textMuted
            font.pixelSize: 16
            font.weight: Font.DemiBold
        }
    }

    background: Rectangle {
        radius: 8
        color: root.enabled ? theme.field : theme.surface
        border.color: root.activeFocus ? root.accentColor : theme.border
        border.width: 1
    }
}

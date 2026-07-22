import QtQuick
import QtQuick.Controls

CheckBox {
    id: root

    property color accentColor: theme.cyan

    implicitHeight: 32
    spacing: 8
    leftPadding: 0
    rightPadding: 0
    topPadding: 4
    bottomPadding: 4

    AppTheme {
        id: theme
    }

    indicator: Rectangle {
        x: root.leftPadding
        y: (root.height - height) / 2
        implicitWidth: 20
        implicitHeight: 20
        radius: 4
        color: root.checked
            ? theme.withAlpha(root.accentColor, root.enabled ? 0.22 : 0.12)
            : (root.enabled ? theme.field : theme.surface)
        border.width: root.activeFocus ? 2 : 1
        border.color: root.activeFocus || root.checked ? root.accentColor : theme.border

        Canvas {
            id: checkMark
            anchors.fill: parent
            visible: root.checked

            onPaint: {
                var ctx = getContext("2d")
                ctx.reset()
                ctx.strokeStyle = root.enabled ? root.accentColor : theme.textMuted
                ctx.lineWidth = 2
                ctx.lineCap = "round"
                ctx.lineJoin = "round"
                ctx.beginPath()
                ctx.moveTo(width * 0.25, height * 0.52)
                ctx.lineTo(width * 0.43, height * 0.70)
                ctx.lineTo(width * 0.76, height * 0.33)
                ctx.stroke()
            }

            Connections {
                target: theme

                function onRedNightVisionChanged() {
                    checkMark.requestPaint()
                }
            }
        }
    }

    contentItem: Text {
        leftPadding: root.indicator.width + root.spacing
        text: root.text
        color: root.enabled ? theme.textPrimary : theme.textMuted
        font: root.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }
}

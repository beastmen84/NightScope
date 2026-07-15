import QtQuick
import QtQuick.Controls

ComboBox {
    id: root

    property color accentColor: theme.cyan
    property string labelText: ""

    implicitHeight: root.labelText.length > 0 ? 58 : 40
    leftPadding: 12
    rightPadding: 34
    topPadding: root.labelText.length > 0 ? 22 : 6
    bottomPadding: 6
    font.pixelSize: 14

    AppTheme {
        id: theme
    }

    delegate: ItemDelegate {
        width: root.width
        height: 38
        highlighted: root.highlightedIndex === index

        contentItem: Text {
            text: root.textRole.length > 0 && modelData !== undefined && modelData !== null
                  ? String(modelData[root.textRole] || "") : String(modelData || "")
            color: parent.highlighted ? theme.textPrimary : theme.textSecondary
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            color: parent.highlighted ? "#252b34" : "#171a20"
        }
    }

    indicator: Canvas {
        x: root.width - width - 12
        y: root.topPadding + (root.availableHeight - height) / 2
        width: 10
        height: 6
        contextType: "2d"

        Connections {
            target: root
            function onPressedChanged() {
                indicator.requestPaint()
            }
        }

        onPaint: {
            var ctx = getContext("2d")
            ctx.reset()
            ctx.moveTo(0, 0)
            ctx.lineTo(width, 0)
            ctx.lineTo(width / 2, height)
            ctx.closePath()
            ctx.fillStyle = root.enabled ? root.accentColor : theme.textMuted
            ctx.fill()
        }
    }

    contentItem: Text {
        leftPadding: 0
        rightPadding: root.indicator.width + root.spacing
        text: root.displayText
        color: root.enabled ? theme.textPrimary : theme.textMuted
        font: root.font
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 8
        color: root.enabled ? "#1c222b" : "#171a20"
        border.color: root.activeFocus ? root.accentColor : "#303641"
        border.width: 1

        Text {
            visible: root.labelText.length > 0
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.leftMargin: 12
            anchors.rightMargin: 34
            anchors.topMargin: 6
            text: root.labelText
            color: theme.textMuted
            font.pixelSize: 10
            elide: Text.ElideRight
            maximumLineCount: 1
        }
    }

    popup: Popup {
        y: root.height + 4
        width: root.width
        implicitHeight: Math.min(contentItem.implicitHeight + 2, 260)
        padding: 1

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: root.popup.visible ? root.delegateModel : null
            currentIndex: root.highlightedIndex
            ScrollIndicator.vertical: ScrollIndicator { }
        }

        background: Rectangle {
            radius: 8
            color: "#171a20"
            border.color: "#303641"
            border.width: 1
        }
    }
}

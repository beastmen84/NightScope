import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property color accentColor: "#65d6e8"
    property string headerBadgeText: ""
    property color headerBadgeColor: accentColor
    property string headerActionText: ""
    property bool headerActionEnabled: true
    property color headerActionAccentColor: accentColor
    property string headerActionToolTip: ""
    default property alias content: contentColumn.data

    signal headerActionClicked()

    color: "#171a20"
    border.color: "#303641"
    border.width: 1
    radius: 8
    implicitHeight: cardLayout.implicitHeight + 32

    ColumnLayout {
        id: cardLayout
        anchors.fill: parent
        anchors.margins: 16
        spacing: 14

        RowLayout {
            visible: root.title.length > 0 || root.subtitle.length > 0
            Layout.fillWidth: true
            spacing: 10

            Rectangle {
                Layout.preferredWidth: 4
                Layout.preferredHeight: 28
                radius: 2
                color: root.accentColor
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    Layout.fillWidth: true
                    text: root.title
                    color: "#f4f7fb"
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.subtitle.length > 0
                    text: root.subtitle
                    color: "#aeb7c4"
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }

            StatusPill {
                visible: root.headerBadgeText.length > 0
                text: root.headerBadgeText
                accentColor: root.headerBadgeColor
                Layout.alignment: Qt.AlignTop
            }

            DarkButton {
                visible: root.headerActionText.length > 0
                Layout.preferredWidth: 116
                Layout.alignment: Qt.AlignTop
                text: root.headerActionText
                enabled: root.headerActionEnabled
                accentColor: root.headerActionAccentColor
                ToolTip.visible: hovered && root.headerActionToolTip.length > 0
                ToolTip.text: root.headerActionToolTip
                onClicked: root.headerActionClicked()
            }
        }

        ColumnLayout {
            id: contentColumn
            Layout.fillWidth: true
            spacing: 12
        }

        Item {
            Layout.fillHeight: true
        }
    }
}

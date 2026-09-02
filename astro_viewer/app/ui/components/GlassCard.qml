// Purpose: Provide the reusable framed card with optional header, badge, and action.
// Contract: Owns layout and styling only; callers supply content and handle the emitted action.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Rectangle {
    id: root

    property string title: ""
    property string subtitle: ""
    property bool subtitleWrap: false
    property color accentColor: theme.cyan
    property bool accentMeaningful: false
    property string headerBadgeText: ""
    property color headerBadgeColor: accentColor
    property string headerActionText: ""
    property bool headerActionEnabled: true
    property int headerActionWidth: 116
    property color headerActionAccentColor: accentColor
    property string headerActionToolTip: ""
    property bool contentFillsHeight: false
    property alias headerContent: headerContentRow.data
    default property alias content: contentColumn.data

    signal headerActionClicked()

    AppTheme {
        id: theme
    }

    color: theme.surface
    border.color: theme.border
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
                color: root.accentMeaningful ? root.accentColor : theme.teal
                opacity: root.accentMeaningful ? 1.0 : 0.7
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 2

                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: root.title
            color: theme.textPrimary
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    visible: root.subtitle.length > 0
                    text: root.subtitle
            color: theme.textSecondary
                    font.pixelSize: 12
                    wrapMode: root.subtitleWrap ? Text.WordWrap : Text.NoWrap
                    elide: Text.ElideRight
                    maximumLineCount: root.subtitleWrap ? 2 : 1
                }
            }

            RowLayout {
                id: headerContentRow
                visible: children.length > 0
                Layout.alignment: Qt.AlignTop | Qt.AlignRight
                spacing: 8
            }

            StatusPill {
                visible: root.headerBadgeText.length > 0
                text: root.headerBadgeText
                accentColor: root.headerBadgeColor
                Layout.alignment: Qt.AlignTop
            }

            DarkButton {
                visible: root.headerActionText.length > 0
                Layout.preferredWidth: root.headerActionWidth
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
            Layout.fillHeight: root.contentFillsHeight
            spacing: 12
        }

        Item {
            visible: !root.contentFillsHeight
            Layout.fillHeight: !root.contentFillsHeight
        }
    }
}

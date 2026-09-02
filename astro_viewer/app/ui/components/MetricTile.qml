// Purpose: Render one compact label, value, and optional semantic accent.
// Contract: Accepts presentation-ready strings and performs no unit or score conversion.

import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property string label: ""
    property string value: ""
    property color accentColor: theme.cyan
    property bool accentMeaningful: false

    AppTheme {
        id: theme
    }

    radius: 8
    color: theme.surfaceRaised
    border.color: theme.border
    border.width: 1
    implicitHeight: 78
    Layout.fillWidth: true

    ColumnLayout {
        anchors.fill: parent
        anchors.margins: 12
        spacing: 4

        Text {
            Layout.fillWidth: true
            text: root.label
            color: theme.textSecondary
            font.pixelSize: 11
            elide: Text.ElideRight
        }

        Text {
            Layout.fillWidth: true
            text: root.value
            color: theme.textPrimary
            font.pixelSize: 18
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: 2
            radius: 1
            color: root.accentMeaningful ? root.accentColor : theme.teal
            opacity: root.accentMeaningful ? 0.75 : 0.6
        }
    }
}

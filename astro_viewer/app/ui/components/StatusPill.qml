// Purpose: Render a compact semantic status label with an accent color.
// Contract: Accepts presentation-ready text and owns no status interpretation.

import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property string text: ""
    property color accentColor: theme.cyan

    AppTheme {
        id: theme
    }

    radius: 8
    color: theme.withAlpha(accentColor, 0.14)
    border.color: theme.withAlpha(accentColor, 0.45)
    border.width: 1
    implicitWidth: label.implicitWidth + 20
    implicitHeight: 30

    Text {
        id: label
        anchors.centerIn: parent
        text: root.text
        color: root.accentColor
        font.pixelSize: 12
        font.weight: Font.DemiBold
        elide: Text.ElideRight
        maximumLineCount: 1
    }
}

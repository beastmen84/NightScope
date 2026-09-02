// Purpose: Provide the shared theme-aware multiline text editor.
// Contract: Preserves the Qt TextArea API and adds only palette, padding, and focus styling.

import QtQuick
import QtQuick.Controls

TextArea {
    id: root

    implicitHeight: 96
    leftPadding: 12
    rightPadding: 12
    topPadding: 10
    bottomPadding: 10
    color: theme.textPrimary
    placeholderTextColor: theme.textMuted
    selectedTextColor: theme.background
    selectionColor: theme.cyan
    wrapMode: TextArea.Wrap
    font.pixelSize: 14

    AppTheme {
        id: theme
    }

    background: Rectangle {
        radius: 8
        color: root.enabled ? theme.field : theme.surface
        border.color: root.activeFocus ? theme.cyan : theme.border
        border.width: 1
    }
}

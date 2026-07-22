import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root

    property string title: ""
    property string acceptText: qsTr("Conferma")
    property string cancelText: qsTr("Annulla")
    property bool showAccept: true
    property bool acceptDanger: false
    property bool acceptEnabled: true
    property bool closeOnAccept: true
    property int preferredWidth: 720
    property int dialogPadding: 28
    default property alias content: body.data

    signal accepted()
    signal rejected()

    modal: true
    focus: true
    width: Math.min(preferredWidth, parent ? parent.width - 72 : preferredWidth)
    height: Math.min(dialogLayout.implicitHeight, parent ? parent.height - 72 : dialogLayout.implicitHeight)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0
    clip: true

    AppTheme {
        id: theme
    }

    background: Rectangle {
        radius: 8
            color: theme.surface
            border.color: theme.border
        border.width: 1
    }

    contentItem: ColumnLayout {
        id: dialogLayout
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: root.dialogPadding
            Layout.rightMargin: root.dialogPadding
            Layout.topMargin: root.dialogPadding

            Text {
                Layout.fillWidth: true
                text: root.title
                color: theme.textPrimary
                font.pixelSize: 20
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }
        }

        ColumnLayout {
            id: body
            Layout.fillWidth: true
            Layout.leftMargin: root.dialogPadding
            Layout.rightMargin: root.dialogPadding
            spacing: 12
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: root.dialogPadding
            Layout.rightMargin: root.dialogPadding
            Layout.bottomMargin: root.dialogPadding
            spacing: 10

            Item { Layout.fillWidth: true }

            DarkButton {
                text: root.cancelText
                onClicked: {
                    root.rejected()
                    root.close()
                }
            }

            DarkButton {
                visible: root.showAccept
                enabled: root.acceptEnabled
                text: root.acceptText
                accentColor: theme.cyan
                danger: root.acceptDanger
                onClicked: {
                    root.accepted()
                    if (root.closeOnAccept)
                        root.close()
                }
            }
        }
    }
}

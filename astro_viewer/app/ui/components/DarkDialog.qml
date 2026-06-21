import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Popup {
    id: root

    property string title: ""
    property string acceptText: "Conferma"
    property string cancelText: "Annulla"
    property bool showAccept: true
    default property alias content: body.data

    signal accepted()
    signal rejected()

    modal: true
    focus: true
    width: Math.min(720, parent ? parent.width - 72 : 720)
    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside
    x: parent ? Math.round((parent.width - width) / 2) : 0
    y: parent ? Math.round((parent.height - height) / 2) : 0

    AppTheme {
        id: theme
    }

    background: Rectangle {
        radius: 8
        color: "#171a20"
        border.color: "#303641"
        border.width: 1
    }

    contentItem: ColumnLayout {
        spacing: 16

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 18
            Layout.rightMargin: 18
            Layout.topMargin: 18

            Text {
                Layout.fillWidth: true
                text: root.title
                color: theme.textPrimary
                font.pixelSize: 20
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }

            Button {
                text: "Chiudi"
                onClicked: {
                    root.rejected()
                    root.close()
                }
            }
        }

        ColumnLayout {
            id: body
            Layout.fillWidth: true
            Layout.leftMargin: 18
            Layout.rightMargin: 18
            spacing: 12
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 18
            Layout.rightMargin: 18
            Layout.bottomMargin: 18
            spacing: 10

            Item { Layout.fillWidth: true }

            Button {
                text: root.cancelText
                onClicked: {
                    root.rejected()
                    root.close()
                }
            }

            Button {
                visible: root.showAccept
                text: root.acceptText
                onClicked: {
                    root.accepted()
                    root.close()
                }
            }
        }
    }
}

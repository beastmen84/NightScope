import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    readonly property string earthdataRegistrationUrl: "https://urs.earthdata.nasa.gov/users/new"

    AppTheme {
        id: theme
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: scroll.availableWidth
            spacing: 18

            Item { Layout.fillWidth: true; Layout.preferredHeight: 18 }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 18

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Text {
                        Layout.fillWidth: true
                        text: "Provider dati"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Configura gli accessi opzionali ai servizi esterni."
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1040 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 206
                    title: "Earthdata NASA"
                    subtitle: controller.earthdataConnectionVerified ? "Connessione LAADS verificata" : (controller.earthdataCredentialsConfigured ? "Credenziali salvate nel vault di sistema" : "Accesso opzionale ai dati VIIRS")
                    accentColor: controller.earthdataConnectionVerified ? theme.green : (controller.earthdataAuthorizationRequired ? theme.violet : theme.amber)
                    headerActionText: "Create account"
                    headerActionWidth: 148
                    headerActionEnabled: !controller.earthdataConnectionTestRunning && !controller.earthdataConnectionVerified && !controller.earthdataAuthorizationRequired
                    headerActionAccentColor: theme.cyan
                    headerActionToolTip: controller.earthdataConnectionVerified || controller.earthdataAuthorizationRequired ? "Account already configured" : "Create a NASA Earthdata account"
                    onHeaderActionClicked: Qt.openUrlExternally(root.earthdataRegistrationUrl)

                    Connections {
                        target: controller

                        function onEarthdataCredentialsChanged() {
                            if (!earthdataUsername.activeFocus)
                                earthdataUsername.text = controller.earthdataUsername
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        StatusPill {
                            text: controller.earthdataConnectionTestRunning ? "Verifica" : (controller.earthdataConnectionVerified ? "Verificato" : (controller.earthdataAuthorizationRequired ? "Autorizza" : (controller.earthdataCredentialsConfigured ? "Da testare" : "Fallback")))
                            accentColor: controller.earthdataConnectionTestRunning ? theme.cyan : (controller.earthdataConnectionVerified ? theme.green : (controller.earthdataAuthorizationRequired ? theme.violet : theme.amber))
                        }

                        Text {
                            Layout.fillWidth: true
                            text: controller.earthdataCredentialMessage
                            color: controller.earthdataSecureStorageAvailable ? theme.textSecondary : theme.coral
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 920 ? 2 : 1
                        columnSpacing: 12
                        rowSpacing: 10

                        DarkTextField {
                            id: earthdataUsername
                            Layout.fillWidth: true
                            placeholderText: "Utente Earthdata"
                            enabled: controller.earthdataSecureStorageAvailable
                            Component.onCompleted: text = controller.earthdataUsername
                        }

                        DarkTextField {
                            id: earthdataPassword
                            Layout.fillWidth: true
                            placeholderText: controller.earthdataCredentialsConfigured ? "Nuova password" : "Password Earthdata"
                            echoMode: TextInput.Password
                            enabled: controller.earthdataSecureStorageAvailable
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        DarkButton {
                            Layout.preferredWidth: 112
                            text: "Salva"
                            enabled: !controller.earthdataConnectionTestRunning && controller.earthdataSecureStorageAvailable && earthdataUsername.text.trim().length > 0 && earthdataPassword.text.trim().length > 0
                            accentColor: theme.green
                            onClicked: {
                                controller.saveEarthdataCredentials(earthdataUsername.text, earthdataPassword.text)
                                earthdataPassword.text = ""
                            }
                        }

                        DarkButton {
                            Layout.preferredWidth: 148
                            text: controller.earthdataConnectionTestRunning ? "Verifica..." : "Test connessione"
                            enabled: controller.earthdataCredentialsConfigured && !controller.earthdataConnectionTestRunning && !controller.earthdataConnectionVerified
                            accentColor: theme.cyan
                            onClicked: controller.testEarthdataConnection()
                        }

                        DarkButton {
                            Layout.preferredWidth: 128
                            text: "Autorizza app"
                            enabled: controller.earthdataAuthorizationRequired && !controller.earthdataConnectionTestRunning && !controller.earthdataConnectionVerified
                            accentColor: theme.violet
                            onClicked: Qt.openUrlExternally(controller.earthdataAuthorizationUrl)
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        DarkButton {
                            Layout.preferredWidth: 96
                            text: "Rimuovi"
                            enabled: controller.earthdataCredentialsConfigured && !controller.earthdataConnectionTestRunning
                            danger: true
                            onClicked: {
                                controller.removeEarthdataCredentials()
                                earthdataUsername.text = ""
                                earthdataPassword.text = ""
                            }
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

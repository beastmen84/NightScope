import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    readonly property string earthdataRegistrationUrl: "https://urs.earthdata.nasa.gov/users/new"
    readonly property string openAQRegistrationUrl: "https://explore.openaq.org/register"

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
                        text: qsTr("Provider dati")
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Configura gli accessi opzionali ai servizi esterni.")
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
                columns: scroll.availableWidth >= 1320 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    id: earthdataCard

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 500
                    title: qsTr("NASA Earthdata")
                    subtitle: controller.earthdataConnectionVerified ? qsTr("Connessione LAADS verificata") : (controller.earthdataCredentialsConfigured ? qsTr("Credenziali salvate nel vault di sistema") : qsTr("Accesso opzionale ai dati VIIRS e AOD"))
                    subtitleWrap: true
                    accentColor: controller.earthdataConnectionVerified ? theme.green : (controller.earthdataAuthorizationRequired ? theme.violet : theme.amber)
                    headerActionText: qsTr("Crea account")
                    headerActionWidth: 148
                    headerActionEnabled: !controller.earthdataConnectionTestRunning && !controller.earthdataConnectionVerified && !controller.earthdataAuthorizationRequired
                    headerActionAccentColor: theme.cyan
                    headerActionToolTip: controller.earthdataConnectionVerified || controller.earthdataAuthorizationRequired ? qsTr("Account già configurato") : qsTr("Crea un account NASA Earthdata")
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
                            text: controller.earthdataConnectionTestRunning ? qsTr("Verifica") : (controller.earthdataConnectionVerified ? qsTr("Verificato") : (controller.earthdataAuthorizationRequired ? qsTr("Autorizza") : (controller.earthdataCredentialsConfigured ? qsTr("Da testare") : qsTr("Fallback"))))
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
                        columns: earthdataCard.width >= 720 ? 2 : 1
                        columnSpacing: 12
                        rowSpacing: 10

                        DarkTextField {
                            id: earthdataUsername
                            Layout.fillWidth: true
                            placeholderText: qsTr("Utente Earthdata")
                            enabled: controller.earthdataSecureStorageAvailable
                            Component.onCompleted: text = controller.earthdataUsername
                        }

                        DarkTextField {
                            id: earthdataPassword
                            Layout.fillWidth: true
                            placeholderText: controller.earthdataCredentialsConfigured ? qsTr("Nuova password") : qsTr("Password Earthdata")
                            echoMode: TextInput.Password
                            enabled: controller.earthdataSecureStorageAvailable
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        DarkButton {
                            Layout.preferredWidth: 112
                            text: qsTr("Salva")
                            enabled: !controller.earthdataConnectionTestRunning && controller.earthdataSecureStorageAvailable && earthdataUsername.text.trim().length > 0 && earthdataPassword.text.trim().length > 0
                            accentColor: theme.green
                            onClicked: {
                                controller.saveEarthdataCredentials(earthdataUsername.text, earthdataPassword.text)
                                earthdataPassword.text = ""
                            }
                        }

                        DarkButton {
                            Layout.preferredWidth: 148
                            text: controller.earthdataConnectionTestRunning ? qsTr("Verifica...") : qsTr("Test connessione")
                            enabled: controller.earthdataCredentialsConfigured && !controller.earthdataConnectionTestRunning && !controller.earthdataConnectionVerified
                            accentColor: theme.cyan
                            onClicked: controller.testEarthdataConnection()
                        }

                        DarkButton {
                            Layout.preferredWidth: 160
                            text: qsTr("Autorizza app")
                            enabled: controller.earthdataAuthorizationRequired && !controller.earthdataConnectionTestRunning && !controller.earthdataConnectionVerified
                            accentColor: theme.violet
                            onClicked: Qt.openUrlExternally(controller.earthdataAuthorizationUrl)
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        DarkButton {
                            Layout.preferredWidth: 96
                            text: qsTr("Rimuovi")
                            enabled: controller.earthdataCredentialsConfigured && !controller.earthdataConnectionTestRunning
                            danger: true
                            onClicked: {
                                controller.removeEarthdataCredentials()
                                earthdataUsername.text = ""
                                earthdataPassword.text = ""
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: theme.border
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Guida alla configurazione")
                        color: theme.textPrimary
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                    }

                    ProviderSetupStep {
                        stepNumber: 1
                        accentColor: earthdataCard.accentColor
                        description: qsTr("Crea l'account Earthdata, conferma l'e-mail di attivazione e accedi.")
                    }

                    ProviderSetupStep {
                        stepNumber: 2
                        accentColor: earthdataCard.accentColor
                        description: qsTr("Apri Modifica profilo e compila tutti i campi, anche quelli indicati come facoltativi: organizzazione, affiliazione, tipo di utente e area di studio. Inserisci informazioni veritiere e pertinenti al tuo caso.")
                    }

                    ProviderSetupStep {
                        stepNumber: 3
                        accentColor: earthdataCard.accentColor
                        description: qsTr("In NightScope inserisci nome utente e password. Seleziona quindi Salva e Test connessione.")
                    }

                    ProviderSetupStep {
                        stepNumber: 4
                        accentColor: earthdataCard.accentColor
                        description: qsTr("Se richiesto, seleziona Autorizza app, spunta tutte le autorizzazioni richieste da LAADS OPeNDAP e conferma con Authorize. Torna quindi in NightScope e ripeti il test.")
                    }
                }

                GlassCard {
                    id: openaqCard

                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 500
                    title: qsTr("OpenAQ")
                    subtitle: controller.openaqConnectionVerified ? qsTr("Connessione API verificata") : (controller.openaqCredentialsConfigured ? qsTr("API key salvata nel vault di sistema") : qsTr("Accesso opzionale ai dati qualità aria"))
                    subtitleWrap: true
                    accentColor: controller.openaqConnectionVerified ? theme.green : (controller.openaqCredentialsConfigured ? theme.amber : theme.violet)
                    headerActionText: qsTr("Crea account")
                    headerActionWidth: 148
                    headerActionEnabled: !controller.openaqConnectionTestRunning && !controller.openaqConnectionVerified
                    headerActionAccentColor: theme.cyan
                    headerActionToolTip: controller.openaqConnectionVerified ? qsTr("Account già configurato") : qsTr("Crea un account OpenAQ")
                    onHeaderActionClicked: Qt.openUrlExternally(root.openAQRegistrationUrl)

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        StatusPill {
                            text: controller.openaqConnectionTestRunning ? qsTr("Verifica") : (controller.openaqConnectionVerified ? qsTr("Verificato") : (controller.openaqCredentialsConfigured ? qsTr("Da testare") : qsTr("Non configurato")))
                            accentColor: controller.openaqConnectionTestRunning ? theme.cyan : (controller.openaqConnectionVerified ? theme.green : (controller.openaqCredentialsConfigured ? theme.amber : theme.violet))
                        }

                        Text {
                            Layout.fillWidth: true
                            text: controller.openaqCredentialMessage
                            color: controller.openaqSecureStorageAvailable ? theme.textSecondary : theme.coral
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }
                    }

                    DarkTextField {
                        id: openaqApiKey
                        Layout.fillWidth: true
                        placeholderText: controller.openaqCredentialsConfigured ? qsTr("Nuova API key OpenAQ") : qsTr("API key OpenAQ")
                        echoMode: TextInput.Password
                        enabled: controller.openaqSecureStorageAvailable
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        DarkButton {
                            Layout.preferredWidth: 112
                            text: qsTr("Salva")
                            enabled: !controller.openaqConnectionTestRunning && controller.openaqSecureStorageAvailable && openaqApiKey.text.trim().length > 0
                            accentColor: theme.green
                            onClicked: {
                                controller.saveOpenAQApiKey(openaqApiKey.text)
                                openaqApiKey.text = ""
                            }
                        }

                        DarkButton {
                            Layout.preferredWidth: 148
                            text: controller.openaqConnectionTestRunning ? qsTr("Verifica...") : qsTr("Test connessione")
                            enabled: controller.openaqCredentialsConfigured && !controller.openaqConnectionTestRunning
                            accentColor: theme.cyan
                            onClicked: controller.testOpenAQConnection()
                        }

                        Item {
                            Layout.fillWidth: true
                        }

                        DarkButton {
                            Layout.preferredWidth: 96
                            text: qsTr("Rimuovi")
                            enabled: controller.openaqCredentialsConfigured && !controller.openaqConnectionTestRunning
                            danger: true
                            onClicked: {
                                controller.removeOpenAQCredentials()
                                openaqApiKey.text = ""
                            }
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 1
                        color: theme.border
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Guida alla configurazione")
                        color: theme.textPrimary
                        font.pixelSize: 14
                        font.weight: Font.DemiBold
                    }

                    ProviderSetupStep {
                        stepNumber: 1
                        accentColor: openaqCard.accentColor
                        description: qsTr("Crea un account OpenAQ e accedi.")
                    }

                    ProviderSetupStep {
                        stepNumber: 2
                        accentColor: openaqCard.accentColor
                        description: qsTr("Apri la pagina dell'account dal menu del profilo e scorri fino alla sezione API Keys.")
                    }

                    ProviderSetupStep {
                        stepNumber: 3
                        accentColor: openaqCard.accentColor
                        description: qsTr("Crea o copia la chiave API. Trattala come una password e non condividerla.")
                    }

                    ProviderSetupStep {
                        stepNumber: 4
                        accentColor: openaqCard.accentColor
                        description: qsTr("In NightScope incolla la chiave, seleziona Salva e poi Test connessione. La configurazione è completa quando lo stato diventa Verificato.")
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

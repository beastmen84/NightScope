// Purpose: Present credential setup and account-free IMO/COBS cache status.
// Contract: Credentials cross only controller APIs; secure storage and provider tests stay in services.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Dialogs
import "../components"

Item {
    id: root

    property var controller
    readonly property string earthdataRegistrationUrl: "https://urs.earthdata.nasa.gov/users/new"
    readonly property string openAQRegistrationUrl: "https://explore.openaq.org/register"
    readonly property var imo: controller.imoCalendar.info
    readonly property var cobs: controller.cobsObservations.info

    FileDialog {
        id: imoImportDialog
        title: qsTr("Importa il calendario IMO dell'anno corrente")
        nameFilters: [qsTr("Calendari PDF (*.pdf)")]
        onAccepted: controller.imoCalendar.importFile(selectedFile)
    }

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
                        text: qsTr("Fonti esterne, calendari scaricati e accessi opzionali.")
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }
            }

            GridLayout {
                id: providersGrid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: scroll.availableWidth >= 1320 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    id: imoCard
                    objectName: "imoProviderCard"
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.preferredWidth: (providersGrid.width - providersGrid.columnSpacing * (providersGrid.columns - 1)) / providersGrid.columns
                    title: qsTr("IMO · International Meteor Organization")
                    subtitle: qsTr("Calendario annuale degli sciami meteorici · Nessun account richiesto")
                    subtitleWrap: true
                    accentColor: root.imo.busy ? theme.cyan : root.imo.current ? theme.green : theme.amber
                    accentMeaningful: true
                    headerActionText: qsTr("Sito ufficiale")
                    headerActionWidth: 148
                    onHeaderActionClicked: Qt.openUrlExternally(root.imo.sourceUrl)

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        StatusPill {
                            text: root.imo.state === "loading" ? qsTr("Caricamento")
                                  : root.imo.state === "ready" ? qsTr("Aggiornato")
                                  : root.imo.state === "stale" ? qsTr("Anno precedente")
                                  : root.imo.state === "invalid_import" ? qsTr("Importazione non riuscita")
                                  : root.imo.state === "pending" ? qsTr("In attesa") : qsTr("Non disponibile")
                            accentColor: imoCard.accentColor
                        }
                        Text {
                            Layout.fillWidth: true
                            text: root.imo.year ? qsTr("Calendario IMO %1 · %2 sciami principali").arg(root.imo.year).arg(root.imo.count)
                                                : qsTr("Calendario %1 non ancora scaricato").arg(root.imo.requestedYear)
                            color: theme.textPrimary
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: root.imo.year > 0
                        text: root.imo.filename + " · " + qsTr("Salvato il %1").arg(root.imo.downloadedAt ? new Date(root.imo.downloadedAt).toLocaleString(Qt.locale(), Locale.ShortFormat) : "")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Download automatico una sola volta per anno, dopo l'avvio. Al cambio d'anno il calendario precedente viene eliminato solo quando il nuovo è stato scaricato e verificato. Le date IMO restano previsioni, non garanzie di osservabilità.")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: root.imo.state === "unavailable" || root.imo.state === "stale" || root.imo.state === "invalid_import"
                        text: root.imo.state === "invalid_import"
                              ? qsTr("PDF non valido o di un altro anno. Il calendario già presente è stato conservato.")
                              : qsTr("Il calendario dell'anno corrente non è disponibile. Nuovo tentativo automatico entro 24 ore; nel frattempo restano le ricorrenze indicative. Puoi importare il PDF originale IMO se lo hai già scaricato.")
                        color: theme.amber
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        DarkButton {
                            text: qsTr("Riprova")
                            enabled: !root.imo.busy && !root.imo.current
                            onClicked: controller.imoCalendar.retry()
                        }
                        DarkButton {
                            text: qsTr("Importa PDF")
                            enabled: !root.imo.busy
                            onClicked: imoImportDialog.open()
                        }
                    }
                }

                GlassCard {
                    id: cobsCard
                    objectName: "cobsProviderCard"
                    Layout.fillWidth: true
                    Layout.preferredWidth: imoCard.Layout.preferredWidth
                    Layout.fillHeight: true
                    title: qsTr("COBS · Comet Observation Database")
                    subtitle: qsTr("Osservazioni della luminosità cometaria · Nessun account richiesto")
                    subtitleWrap: true
                    accentColor: root.cobs.busy ? theme.cyan : root.cobs.state === "ready" ? theme.green : theme.amber
                    accentMeaningful: true
                    headerActionText: qsTr("Sito ufficiale")
                    headerActionWidth: 148
                    onHeaderActionClicked: Qt.openUrlExternally(root.cobs.sourceUrl)

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12
                        StatusPill {
                            text: root.cobs.state === "loading" ? qsTr("Caricamento")
                                  : root.cobs.state === "ready" ? qsTr("Aggiornato")
                                  : root.cobs.state === "stale" ? qsTr("Dati di riserva")
                                  : root.cobs.state === "pending" ? qsTr("In attesa") : qsTr("Non disponibile")
                            accentColor: cobsCard.accentColor
                        }
                        Text {
                            Layout.fillWidth: true
                            text: qsTr("%1 osservazioni · %2 comete negli ultimi 14 giorni").arg(root.cobs.count).arg(root.cobs.comets)
                            color: theme.textPrimary
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                        }
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: !!root.cobs.downloadedAt
                        text: qsTr("Salvato il %1").arg(root.cobs.downloadedAt ? new Date(root.cobs.downloadedAt).toLocaleString(Qt.locale(), Locale.ShortFormat) : "")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        visible: !!root.cobs.latestAt
                        text: qsTr("Ultima osservazione: %1").arg(root.cobs.latestAt ? new Date(root.cobs.latestAt).toLocaleString(Qt.locale(), Locale.ShortFormat) : "")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Aggiornamento automatico ogni 24 ore in background. Serie recenti e coerenti correggono la luminosità a breve termine e quindi selezione, notti utili e strumento consigliato. Dati insufficienti o discordanti mantengono il modello JPL.")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Le stime visuali e quelle CCD equivalenti restano separate. La correzione scade entro 72 ore dall'ultima osservazione usata; non prevede outburst né garantisce la visibilità.")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Dati: COBS e osservatori contributori · CC BY-NC-SA 4.0. Uso non commerciale; elaborazioni NightScope soggette alla stessa licenza. La licenza del codice resta MPL 2.0.")
                        color: theme.textSecondary
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                    DarkButton {
                        text: qsTr("Licenza dei dati")
                        onClicked: Qt.openUrlExternally(root.cobs.licenseUrl)
                    }
                }

                GlassCard {
                    id: earthdataCard
                    objectName: "earthdataProviderCard"

                    Layout.fillWidth: true
                    Layout.preferredWidth: imoCard.Layout.preferredWidth
                    Layout.fillHeight: true
                    Layout.minimumHeight: 500
                    title: qsTr("NASA Earthdata")
                    subtitle: controller.earthdataConnectionVerified ? qsTr("Connessione LAADS verificata") : (controller.earthdataCredentialsConfigured ? qsTr("Credenziali salvate nel vault di sistema") : qsTr("Accesso opzionale ai dati VIIRS e AOD"))
                    subtitleWrap: true
                    accentColor: controller.earthdataConnectionTestRunning
                                 ? theme.cyan
                                 : controller.earthdataConnectionVerified
                                   ? theme.green
                                   : (controller.earthdataAuthorizationRequired
                                      || controller.earthdataCredentialsConfigured)
                                     ? theme.amber
                                     : theme.teal
                    accentMeaningful: true
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
                            accentColor: earthdataCard.accentColor
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
                        columns: earthdataCard.width >= 620 ? 2 : 1
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
                    objectName: "openaqProviderCard"

                    Layout.fillWidth: true
                    Layout.preferredWidth: imoCard.Layout.preferredWidth
                    Layout.fillHeight: true
                    Layout.minimumHeight: 500
                    title: qsTr("OpenAQ")
                    subtitle: controller.openaqConnectionVerified ? qsTr("Connessione API verificata") : (controller.openaqCredentialsConfigured ? qsTr("API key salvata nel vault di sistema") : qsTr("Accesso opzionale ai dati qualità aria"))
                    subtitleWrap: true
                    accentColor: controller.openaqConnectionTestRunning
                                 ? theme.cyan
                                 : controller.openaqConnectionVerified
                                   ? theme.green
                                   : controller.openaqCredentialsConfigured
                                     ? theme.amber
                                     : theme.teal
                    accentMeaningful: true
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
                            accentColor: openaqCard.accentColor
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

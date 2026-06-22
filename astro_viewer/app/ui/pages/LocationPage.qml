import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller

    function compactCountry() {
        if (!controller.hasValidLocation)
            return "Nessuna posizione configurata"
        if (controller.location.country === undefined || controller.location.country === "")
            return controller.location.timezone
        return controller.location.country + "  -  " + controller.location.timezone
    }

    function currentLocationTitle() {
        if (!controller.hasValidLocation)
            return "Nessuna posizione"
        return controller.location.city + " (" + controller.location.latitude.toFixed(4) + " / " + controller.location.longitude.toFixed(4) + ")"
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
            spacing: 16

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
                        text: "Configurazione location"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.locationMessage
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }

                StatusPill {
                    text: controller.location.city
                    accentColor: theme.teal
                }
            }

            GridLayout {
                id: overviewGrid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1040 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 148
                    title: "Posizione attuale"
                    subtitle: controller.hasValidLocation ? controller.activeLocationSource : "Nessuna posizione configurata"
                    accentColor: theme.green

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        StatusPill {
                            text: controller.hasValidLocation ? "Attiva" : "Da configurare"
                            accentColor: controller.hasValidLocation ? theme.green : theme.amber
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: root.currentLocationTitle()
                                color: theme.textPrimary
                                font.pixelSize: 20
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.compactCountry()
                                color: theme.textSecondary
                                font.pixelSize: 13
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: !controller.hasValidLocation
                                text: "Configura una posizione per ottenere meteo e cielo locale."
                                color: theme.textMuted
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 148
                    title: "Rilevamento posizione all'avvio"
                    subtitle: "Origini usate quando NightScope parte."
                    accentColor: theme.teal

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 920 ? 3 : 1
                        columnSpacing: 14
                        rowSpacing: 6

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: "Avvio"
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            CheckBox {
                                Layout.fillWidth: true
                                text: "Rileva automaticamente"
                                checked: controller.autoDetectLocationOnStartup
                                onToggled: controller.setAutoDetectLocationOnStartup(checked)
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: "Origini"
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            CheckBox {
                                Layout.fillWidth: true
                                text: "Posizione Windows"
                                enabled: controller.autoDetectLocationOnStartup && (controller.allowApproximateOnlineLocation || !controller.useWindowsLocationOnStartup)
                                checked: controller.autoDetectLocationOnStartup && controller.useWindowsLocationOnStartup
                                opacity: enabled || checked ? 1 : 0.55
                                onToggled: controller.setUseWindowsLocationOnStartup(checked)
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: "Fallback"
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            CheckBox {
                                Layout.fillWidth: true
                                text: "Online approssimato"
                                enabled: controller.autoDetectLocationOnStartup && (controller.useWindowsLocationOnStartup || !controller.allowApproximateOnlineLocation)
                                checked: controller.autoDetectLocationOnStartup && controller.allowApproximateOnlineLocation
                                opacity: enabled || checked ? 1 : 0.55
                                onToggled: controller.setAllowApproximateOnlineLocation(checked)
                            }
                        }
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
                    visible: controller.recentLocations.length > 0
                    title: "Posizioni recenti"
                    subtitle: "Ultime posizioni salvate o caricate"
                    accentColor: theme.violet

                    Repeater {
                        model: controller.recentLocations

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 42
                            radius: 8
                            color: recentMouse.containsMouse ? "#20242b" : "#15181e"
                            border.color: recentMouse.containsMouse ? "#303641" : "transparent"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 8
                                spacing: 10

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.location.city + ", " + modelData.location.country
                                        color: theme.textPrimary
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.location.timezone
                                        color: theme.textMuted
                                        font.pixelSize: 11
                                        elide: Text.ElideRight
                                    }
                                }

                                Button {
                                    Layout.preferredWidth: 64
                                    text: "Usa"
                                    onClicked: controller.selectRecentLocation(index)
                                }
                            }

                            MouseArea {
                                id: recentMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                acceptedButtons: Qt.NoButton
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 206
                    title: "Earthdata NASA"
                    subtitle: controller.earthdataCredentialsConfigured ? "Credenziali salvate nel vault di sistema" : "Accesso opzionale ai dati VIIRS"
                    accentColor: controller.earthdataCredentialsConfigured ? theme.green : theme.amber

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
                            text: controller.earthdataConnectionTestRunning ? "Verifica" : (controller.earthdataCredentialsConfigured ? "Configurato" : "Fallback")
                            accentColor: controller.earthdataConnectionTestRunning ? theme.cyan : (controller.earthdataCredentialsConfigured ? theme.green : theme.amber)
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
                            placeholderText: "Username Earthdata"
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
                            enabled: controller.earthdataCredentialsConfigured && !controller.earthdataConnectionTestRunning
                            accentColor: theme.cyan
                            onClicked: controller.testEarthdataConnection()
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

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1040 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    title: "Posizione Windows"
                    subtitle: "Precisa con fallback Windows approssimato"
                    accentColor: theme.cyan

                    Text {
                        Layout.fillWidth: true
                        text: "Usa i servizi di localizzazione di Windows con consenso di sistema. Se il provider preciso non risponde, NightScope tenta il fallback Windows approssimato."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Usa posizione Windows"
                        onClicked: controller.useWindowsLocation()
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: controller.canUseApproximateOnlineLocation
                        radius: 8
                        color: "#20242b"
                        border.color: theme.amber
                        border.width: 1
                        implicitHeight: fallbackLayout.implicitHeight + 20

                        ColumnLayout {
                            id: fallbackLayout
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Text {
                                Layout.fillWidth: true
                                text: "Windows location is unavailable. Try approximate online location?"
                                color: theme.textPrimary
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }

                            Button {
                                Layout.fillWidth: true
                                text: "Usa posizione approssimata online"
                                onClicked: controller.useApproximateOnlineLocation()
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Posizione approssimata online"
                    subtitle: "Geolocalizzazione IP"
                    accentColor: theme.violet

                    Text {
                        Layout.fillWidth: true
                        text: "Stima citta, paese, coordinate e timezone tramite connessione internet. Precisione limitata; non viene usata senza consenso."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Usa posizione approssimata online"
                        onClicked: controller.useApproximateOnlineLocation()
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: controller.locationDetails.approximate === true
                        text: "Origine: " + controller.locationDetails.source + "  -  accuratezza: " + controller.locationDetails.accuracy
                        color: theme.textMuted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
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
                    Layout.alignment: Qt.AlignTop
                    Layout.minimumHeight: root.width > 1040 ? 248 : 0
                    title: "Ricerca citta"
                    subtitle: "Catalogo GeoNames offline"
                    accentColor: theme.amber

                    TextField {
                        id: citySearch
                        Layout.fillWidth: true
                        placeholderText: "Cerca citta"
                        onTextChanged: controller.searchCities(text)
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 168
                        radius: 8
                        color: "#15181e"
                        border.color: "#303641"
                        border.width: 1
                        clip: true

                        Text {
                            anchors.fill: parent
                            anchors.margins: 12
                            visible: !controller.hasCitySearchQuery
                            text: "Digita una citta per mostrare risultati offline."
                            color: theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            verticalAlignment: Text.AlignVCenter
                        }

                        Text {
                            anchors.fill: parent
                            anchors.margins: 12
                            visible: controller.hasCitySearchQuery && controller.cityResults.length === 0
                            text: "Nessuna citta trovata."
                            color: theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            verticalAlignment: Text.AlignVCenter
                        }

                        ListView {
                            anchors.fill: parent
                            anchors.margins: 6
                            visible: controller.hasCitySearchQuery && controller.cityResults.length > 0
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds
                            spacing: 4
                            model: controller.cityResults

                            delegate: Rectangle {
                                width: ListView.view.width
                                height: 38
                                radius: 8
                                color: cityMouse.containsMouse ? "#20242b" : "transparent"
                                border.color: cityMouse.containsMouse ? "#303641" : "transparent"
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.city + ", " + modelData.country
                                        color: theme.textPrimary
                                        font.pixelSize: 13
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        text: modelData.latitude.toFixed(2) + ", " + modelData.longitude.toFixed(2)
                                        color: theme.textMuted
                                        font.pixelSize: 11
                                    }
                                }

                                MouseArea {
                                    id: cityMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: controller.selectCity(modelData.id)
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    Layout.minimumHeight: root.width > 1040 ? 248 : 0
                    title: "Coordinate manuali"
                    subtitle: "Inserimento diretto"
                    accentColor: theme.teal

                    TextField {
                        id: manualLabel
                        Layout.fillWidth: true
                        placeholderText: "Nome luogo"
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 760 ? 2 : 1
                        columnSpacing: 10
                        rowSpacing: 8

                        TextField {
                            id: manualLatitude
                            Layout.fillWidth: true
                            placeholderText: "Latitudine"
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }

                        TextField {
                            id: manualLongitude
                            Layout.fillWidth: true
                            placeholderText: "Longitudine"
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Imposta coordinate"
                        onClicked: controller.setManualLocation(manualLatitude.text, manualLongitude.text, manualLabel.text)
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

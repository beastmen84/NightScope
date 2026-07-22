import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller

    function compactCountry() {
        if (!controller.hasValidLocation)
            return qsTr("Nessuna località configurata")
        if (controller.location.country === undefined || controller.location.country === "")
            return controller.location.timezone
        return controller.location.country + "  -  " + controller.location.timezone
    }

    function currentLocationTitle() {
        if (!controller.hasValidLocation)
            return qsTr("Nessuna posizione")
        return qsTr("%1 (%2)")
            .arg(controller.location.city)
            .arg(controller.location.coordinatesLabel)
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
                        text: qsTr("Configurazione località")
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
                    title: qsTr("Posizione attuale")
                    subtitle: controller.hasValidLocation ? controller.activeLocationSource : qsTr("Nessuna località configurata")
                    accentColor: theme.green

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        StatusPill {
                            text: controller.hasValidLocation ? qsTr("Attiva") : qsTr("Da configurare")
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
                                text: qsTr("Configura una località per ottenere meteo e cielo locale.")
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
                    title: qsTr("Rilevamento posizione all'avvio")
                    subtitle: qsTr("Origini usate quando NightScope parte.")
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
                                text: qsTr("Avvio")
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            CheckBox {
                                Layout.fillWidth: true
                                text: qsTr("Rileva automaticamente")
                                checked: controller.autoDetectLocationOnStartup
                                onToggled: controller.setAutoDetectLocationOnStartup(checked)
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("Origini")
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            CheckBox {
                                Layout.fillWidth: true
                                text: qsTr("Posizione di sistema")
                                enabled: platformCapabilities.systemLocationSupported && controller.autoDetectLocationOnStartup && (controller.allowApproximateOnlineLocation || !controller.useSystemLocationOnStartup)
                                checked: controller.autoDetectLocationOnStartup && controller.useSystemLocationOnStartup
                                opacity: enabled || checked ? 1 : 0.55
                                onToggled: controller.setUseSystemLocationOnStartup(checked)
                            }
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("Fallback")
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            CheckBox {
                                Layout.fillWidth: true
                                text: qsTr("Fallback online")
                                enabled: controller.autoDetectLocationOnStartup && (controller.useSystemLocationOnStartup || !controller.allowApproximateOnlineLocation)
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
                    Layout.rowSpan: root.width > 1040 ? 2 : 1
                    Layout.alignment: Qt.AlignTop
                    Layout.minimumHeight: root.width > 1040 ? 428 : 248
                    clip: true
                    title: qsTr("Ricerca località")
                    subtitle: qsTr("GeoNames e osservatori MPC offline")
                    accentColor: theme.amber
                    contentFillsHeight: true

                    TextField {
                        id: locationSearch
                        Layout.fillWidth: true
                        placeholderText: qsTr("Cerca città, osservatorio o codice MPC")
                        onTextChanged: controller.searchLocations(text)
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        radius: 8
                        color: "#15181e"
                        border.color: "#303641"
                        border.width: 1
                        clip: true

                        Text {
                            anchors.fill: parent
                            anchors.margins: 12
                            visible: !controller.hasLocationSearchQuery
                            text: qsTr("Digita una città, un osservatorio o un codice MPC.")
                            color: theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            verticalAlignment: Text.AlignVCenter
                        }

                        Text {
                            anchors.fill: parent
                            anchors.margins: 12
                            visible: controller.hasLocationSearchQuery && controller.locationResults.length === 0
                            text: qsTr("Nessuna località trovata.")
                            color: theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            verticalAlignment: Text.AlignVCenter
                        }

                        ListView {
                            anchors.fill: parent
                            anchors.margins: 6
                            visible: controller.hasLocationSearchQuery && controller.locationResults.length > 0
                            clip: true
                            boundsBehavior: Flickable.StopAtBounds
                            spacing: 4
                            model: controller.locationResults

                            delegate: Rectangle {
                                width: ListView.view.width
                                height: 52
                                radius: 8
                                color: cityMouse.containsMouse ? "#20242b" : "transparent"
                                border.color: cityMouse.containsMouse ? "#303641" : "transparent"
                                border.width: 1

                                RowLayout {
                                    anchors.fill: parent
                                    anchors.leftMargin: 10
                                    anchors.rightMargin: 10

                                    ColumnLayout {
                                        Layout.fillWidth: true
                                        spacing: 1

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.displayName
                                            color: theme.textPrimary
                                            font.pixelSize: 13
                                            elide: Text.ElideRight
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.kindLabel + " · " + modelData.context
                                            color: theme.textMuted
                                            font.pixelSize: 11
                                            elide: Text.ElideRight
                                        }
                                    }

                                    Text {
                                        text: modelData.coordinatesLabel
                                        color: theme.textMuted
                                        font.pixelSize: 11
                                    }
                                }

                                MouseArea {
                                    id: cityMouse
                                    anchors.fill: parent
                                    hoverEnabled: true
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: controller.selectLocation(modelData.kind, modelData.selection_id)
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    Layout.minimumHeight: 206
                    title: qsTr("Posizione di sistema")
                    subtitle: platformCapabilities.systemLocationProvider === "geoclue2"
                              ? qsTr("Servizio GeoClue 2")
                              : qsTr("Precisa con fallback Windows approssimato")
                    accentColor: theme.cyan

                    Text {
                        Layout.fillWidth: true
                        text: platformCapabilities.systemLocationProvider === "geoclue2"
                              ? qsTr("Usa GeoClue per richiedere la posizione al sistema. Disponibilità e precisione dipendono dai servizi di localizzazione configurati nella distribuzione.")
                              : qsTr("Usa i servizi di localizzazione di Windows con consenso di sistema. Se il provider preciso non risponde, NightScope tenta il fallback Windows approssimato.")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    DarkButton {
                        Layout.alignment: Qt.AlignLeft
                        text: qsTr("Usa posizione di sistema")
                        enabled: platformCapabilities.systemLocationSupported
                        accentColor: theme.cyan
                        onClicked: controller.useSystemLocation()
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
                                text: qsTr("La posizione di sistema non è disponibile. Provare la posizione approssimata online?")
                                color: theme.textPrimary
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }

                            DarkButton {
                                Layout.alignment: Qt.AlignLeft
                                text: qsTr("Usa posizione approssimata online")
                                accentColor: theme.amber
                                onClicked: controller.useApproximateOnlineLocation()
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    Layout.minimumHeight: 206
                    title: qsTr("Località IP (ipapi/ipwho)")
                    subtitle: qsTr("Geolocalizzazione IP")
                    accentColor: theme.violet

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Stima città, paese, coordinate e fuso orario tramite connessione internet. Precisione limitata; non viene usata senza consenso.")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    DarkButton {
                        Layout.alignment: Qt.AlignLeft
                        text: qsTr("Usa posizione approssimata online")
                        accentColor: theme.violet
                        onClicked: controller.useApproximateOnlineLocation()
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: controller.locationDetails.approximate === true
                        text: qsTr("Origine: %1  -  accuratezza: %2")
                            .arg(controller.locationDetails.source)
                            .arg(controller.locationDetails.accuracy)
                        color: theme.textMuted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 206
                    title: qsTr("Posizioni recenti")
                    subtitle: qsTr("Ultime posizioni salvate o caricate")
                    accentColor: theme.violet

                    Text {
                        Layout.fillWidth: true
                        visible: controller.recentLocations.length === 0
                        text: qsTr("Nessuna posizione recente.")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

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

                                DarkButton {
                                    Layout.preferredWidth: 64
                                    text: qsTr("Usa")
                                    accentColor: theme.violet
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
                    Layout.alignment: Qt.AlignTop
                    Layout.minimumHeight: 206
                    title: qsTr("Coordinate manuali")
                    subtitle: qsTr("Inserimento diretto")
                    accentColor: theme.teal

                    TextField {
                        id: manualLabel
                        Layout.fillWidth: true
                        placeholderText: qsTr("Nome luogo (facoltativo)")
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 760 ? 2 : 1
                        columnSpacing: 10
                        rowSpacing: 8

                        TextField {
                            id: manualLatitude
                            Layout.fillWidth: true
                            placeholderText: qsTr("Latitudine *")
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }

                        TextField {
                            id: manualLongitude
                            Layout.fillWidth: true
                            placeholderText: qsTr("Longitudine *")
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                    }

                    DarkButton {
                        Layout.alignment: Qt.AlignLeft
                        text: qsTr("Imposta coordinate")
                        enabled: manualLatitude.text.trim().length > 0
                                 && manualLongitude.text.trim().length > 0
                        accentColor: theme.teal
                        onClicked: controller.setManualLocation(manualLatitude.text, manualLongitude.text, manualLabel.text)
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

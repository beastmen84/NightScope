import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller

    function diagnosticValue(value, fallbackText) {
        if (value === undefined || value === null || value === "")
            return fallbackText
        return value
    }

    function diagnosticJson(value) {
        if (value === undefined || value === null)
            return ""
        return JSON.stringify(value, null, 2)
    }

    function compactCountry() {
        if (!controller.hasValidLocation)
            return "Nessuna posizione configurata"
        if (controller.location.country === undefined || controller.location.country === "")
            return controller.location.timezone
        return controller.location.country + "  -  " + controller.location.timezone
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
                    Layout.columnSpan: overviewGrid.columns === 2 && controller.recentLocations.length === 0 ? 2 : 1
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
                                text: controller.hasValidLocation ? controller.location.city : "Nessuna posizione"
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
                                text: controller.hasValidLocation ? (controller.location.latitude.toFixed(4) + ", " + controller.location.longitude.toFixed(4)) : "Configura una posizione per ottenere meteo e cielo locale."
                                color: theme.textMuted
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
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
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Rilevamento posizione all'avvio"
                subtitle: "Scegli se rilevare automaticamente la posizione e quali origini sono consentite."
                accentColor: theme.teal

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1040 ? 3 : 1
                    columnSpacing: 18
                    rowSpacing: 8

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

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
                        spacing: 6

                        Text {
                            Layout.fillWidth: true
                            text: "Origini consentite"
                            color: theme.textPrimary
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        CheckBox {
                            Layout.fillWidth: true
                            text: "Posizione Windows"
                            checked: controller.useWindowsLocationOnStartup
                            onToggled: controller.setUseWindowsLocationOnStartup(checked)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

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
                            checked: controller.allowApproximateOnlineLocation
                            onToggled: controller.setAllowApproximateOnlineLocation(checked)
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

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 760 ? 2 : 1
                        columnSpacing: 10
                        rowSpacing: 8

                        Button {
                            Layout.fillWidth: true
                            text: "Usa posizione Windows"
                            onClicked: controller.useWindowsLocation()
                        }

                        Button {
                            Layout.fillWidth: true
                            text: "Diagnostica Windows"
                            onClicked: controller.runWindowsLocationDiagnostics()
                        }
                    }

                    Rectangle {
                        Layout.fillWidth: true
                        visible: controller.windowsLocationDiagnostics.providerStatus !== "not run"
                        radius: 8
                        color: "#1c222b"
                        border.color: theme.cyan
                        border.width: 1
                        implicitHeight: diagnosticsLayout.implicitHeight + 20

                        ColumnLayout {
                            id: diagnosticsLayout
                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 8

                            Text {
                                Layout.fillWidth: true
                                text: "Windows Location Diagnostics"
                                color: theme.textPrimary
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Access Status: " + root.diagnosticValue(controller.windowsLocationDiagnostics.accessStatus, "n/d")
                                color: theme.textSecondary
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "RequestAccessAsync result: " + root.diagnosticValue(controller.windowsLocationDiagnostics.requestAccessResult, "n/d")
                                color: theme.textSecondary
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Coordinates received: " + (controller.windowsLocationDiagnostics.coordinatesReceived ? "yes" : "no")
                                color: theme.textSecondary
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Provider status: " + root.diagnosticValue(controller.windowsLocationDiagnostics.providerStatus, "n/d")
                                color: theme.textSecondary
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Coordinates: " + root.diagnosticJson(controller.windowsLocationDiagnostics.coordinates)
                                color: theme.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                maximumLineCount: 4
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Error details: " + root.diagnosticJson(controller.windowsLocationDiagnostics.errorDetails)
                                color: theme.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                maximumLineCount: 8
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Thread/apartment: " + root.diagnosticJson(controller.windowsLocationDiagnostics.thread)
                                color: theme.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                maximumLineCount: 5
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "WinRT: " + root.diagnosticJson(controller.windowsLocationDiagnostics.winrt)
                                color: theme.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                maximumLineCount: 8
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Steps: " + root.diagnosticJson(controller.windowsLocationDiagnostics.steps)
                                color: theme.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                                maximumLineCount: 10
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Raw provider response: " + root.diagnosticValue(controller.windowsLocationDiagnostics.rawProviderResponse, "n/d")
                                color: theme.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WrapAnywhere
                                maximumLineCount: 10
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: controller.windowsLocationDiagnostics.rawProviderError !== undefined && controller.windowsLocationDiagnostics.rawProviderError.length > 0
                                text: "Raw provider error: " + controller.windowsLocationDiagnostics.rawProviderError
                                color: theme.textMuted
                                font.pixelSize: 11
                                wrapMode: Text.WrapAnywhere
                                maximumLineCount: 6
                            }
                        }
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

                    Repeater {
                        model: controller.hasCitySearchQuery ? controller.cityResults.slice(0, 6) : []

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 40
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

                    Text {
                        Layout.fillWidth: true
                        visible: !controller.hasCitySearchQuery
                        text: "Digita una citta per mostrare risultati offline."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: controller.hasCitySearchQuery && controller.cityResults.length === 0
                        text: "Nessuna citta trovata."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
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

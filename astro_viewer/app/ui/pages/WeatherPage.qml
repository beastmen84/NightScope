pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var displayWeatherHours: controller.weatherNext24Hours || []
    property string selectedWeatherHourTimestamp: ""
    readonly property bool hasSkyQuality: controller.hasValidLocation && controller.hasSkyQuality
    signal openLocation()

    function selectedWeatherHourIndex() {
        if (root.displayWeatherHours.length === 0)
            return -1
        for (var index = 0; index < root.displayWeatherHours.length; index++) {
            if (root.displayWeatherHours[index].timestamp === root.selectedWeatherHourTimestamp)
                return index
        }
        return 0
    }

    function selectedWeatherHour() {
        if (root.displayWeatherHours.length === 0)
            return null
        return root.displayWeatherHours[root.selectedWeatherHourIndex()]
    }

    function selectedHourText(key, fallbackText) {
        var hour = root.selectedWeatherHour()
        if (!hour || hour[key] === undefined || hour[key] === null)
            return fallbackText
        return hour[key]
    }

    function skyQualityConfidenceText() {
        if (!root.hasSkyQuality)
            return qsTr("n/d")
        var quality = controller.skyQuality || {}
        return quality.confidenceLabel || quality.confidence || qsTr("n/d")
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
                        text: qsTr("Meteo osservativo")
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.hasValidLocation
                              ? qsTr("Meteo per: %1 - %2")
                                    .arg(controller.activeLocationLabel)
                                    .arg(controller.activeLocationSource)
                              : qsTr("Nessuna località configurata")
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }

                DarkButton {
                    Layout.preferredWidth: controller.hasValidLocation ? 118 : 154
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    text: !controller.hasValidLocation
                          ? qsTr("Configura località")
                          : controller.weatherRefreshRunning ? qsTr("Aggiorno...") : qsTr("Aggiorna")
                    enabled: !controller.startupLocationDetectionRunning
                             && (!controller.hasValidLocation || !controller.weatherRefreshRunning)
                    accentColor: theme.cyan
                    onClicked: {
                        if (controller.hasValidLocation)
                            controller.refreshWeatherNow()
                        else
                            root.openLocation()
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                visible: controller.isLoading || controller.weatherRefreshRunning || controller.weatherStatus.length > 0
                radius: 8
                    color: theme.field
                border.color: controller.weatherRefreshRunning || controller.isLoading ? theme.cyan : theme.coral
                border.width: 1
                implicitHeight: weatherStateText.implicitHeight + 22

                Text {
                    id: weatherStateText
                    anchors.fill: parent
                    anchors.margins: 11
                    text: controller.weatherRefreshRunning ? qsTr("Aggiornamento meteo in corso...") : controller.isLoading ? qsTr("Caricamento meteo...") : controller.weatherStatus
                    color: theme.textPrimary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 2
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 3

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Sintesi notte osservativa")
                    color: theme.textPrimary
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                }

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Medie meteo nella finestra notturna; precipitazioni come probabilità massima, Bortle locale quando disponibile.")
                    color: theme.textMuted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1050 ? 4 : 3
                columnSpacing: 12
                rowSpacing: 12

                MetricTile { label: qsTr("Nuvolosità media"); value: controller.hasValidLocation ? controller.weatherSummary.cloudCoverLabel : qsTr("n/d") }
                MetricTile { label: qsTr("Precipitazioni max"); value: controller.hasValidLocation ? controller.weatherSummary.precipitationProbabilityLabel : qsTr("n/d") }
                MetricTile { label: qsTr("Vento medio"); value: controller.hasValidLocation ? controller.weatherSummary.windLabel : qsTr("n/d") }
                MetricTile { label: qsTr("Umidità media"); value: controller.hasValidLocation ? controller.weatherSummary.humidityLabel : qsTr("n/d") }
                MetricTile { label: qsTr("Temperatura media"); value: controller.hasValidLocation ? controller.weatherSummary.temperatureLabel : qsTr("n/d") }
                MetricTile { label: qsTr("Seeing notturno"); value: controller.hasValidLocation ? controller.seeingTransparency.seeing : qsTr("n/d") }
                MetricTile { label: qsTr("Trasparenza notturna"); value: controller.hasValidLocation ? controller.seeingTransparency.atmosphericTransparency : qsTr("n/d") }
                MetricTile { label: qsTr("Bortle locale"); value: root.hasSkyQuality ? controller.skyQuality.bortleLabel : qsTr("n/d") }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Qualità cielo locale")
                subtitle: root.hasSkyQuality
                          ? controller.skyQuality.source
                          : controller.hasValidLocation
                            ? qsTr("Dati di inquinamento luminoso non disponibili")
                            : qsTr("n/d")
                accentColor: theme.violet

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 980 ? 4 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile {
                        visible: root.hasSkyQuality && controller.skyQuality.hasViirsRadiance
                        label: qsTr("Osservazioni VIIRS")
                        value: controller.skyQuality.viirsObservationCountLabel
                    }
                    MetricTile {
                        label: root.hasSkyQuality && controller.skyQuality.hasViirsRadiance
                               ? qsTr("Radianza VIIRS") : "SQM"
                        value: !root.hasSkyQuality
                               ? qsTr("n/d")
                               : controller.skyQuality.hasViirsRadiance
                                 ? controller.skyQuality.viirsRadianceLabel
                                 : controller.skyQuality.skyBrightnessLabel
                    }
                    MetricTile {
                        label: root.hasSkyQuality && controller.skyQuality.hasViirsRadiance
                               ? qsTr("SQM stimato") : qsTr("Limite visuale")
                        value: !root.hasSkyQuality
                               ? qsTr("n/d")
                               : controller.skyQuality.hasViirsRadiance
                                 ? controller.skyQuality.skyBrightnessLabel
                                 : controller.skyQuality.limitingMagnitudeLabel
                    }
                    MetricTile { label: qsTr("Confidenza"); value: root.skyQualityConfidenceText() }
                }

                Text {
                    Layout.fillWidth: true
                    text: controller.hasValidLocation
                          ? qsTr("Seeing: %1 (%2)")
                                .arg(controller.seeingTransparency.source)
                                .arg(controller.seeingTransparency.confidence)
                          : qsTr("Seeing: n/d")
                    color: theme.textMuted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    visible: controller.viirsSkyQualityRunning || controller.lightPollutionStatus.length > 0
                    text: controller.viirsSkyQualityRunning ? qsTr("Recupero dati VIIRS NASA...") : controller.lightPollutionStatus
                    color: controller.viirsSkyQualityRunning ? theme.cyan : theme.textMuted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                visible: controller.atmosphericTransparency.visible
                title: qsTr("Aerosol atmosferico")
                subtitle: qsTr("NASA MAIAC AOD")
                accentColor: controller.atmosphericTransparency.running ? theme.cyan : controller.atmosphericTransparency.hasData ? theme.green : theme.amber

                GridLayout {
                    Layout.fillWidth: true
                    visible: controller.atmosphericTransparency.hasData
                    columns: root.width > 980 ? 4 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile { label: qsTr("AOD 550 nm"); value: controller.atmosphericTransparency.aod550 }
                    MetricTile { label: qsTr("Effetto aerosol"); value: controller.atmosphericTransparency.transparency }
                    MetricTile { label: qsTr("Freschezza"); value: controller.atmosphericTransparency.freshness }
                    MetricTile { label: qsTr("Fonte"); value: controller.atmosphericTransparency.productLabel }
                }

                Text {
                    Layout.fillWidth: true
                    visible: controller.atmosphericTransparency.sourceDetail.length > 0
                    text: controller.atmosphericTransparency.sourceDetail
                    color: controller.atmosphericTransparency.freshnessWarning ? theme.amber : theme.textMuted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    visible: controller.atmosphericTransparency.running || !controller.atmosphericTransparency.hasData
                    text: controller.atmosphericTransparency.running ? qsTr("Recupero dati NASA AOD...") : controller.atmosphericTransparency.message
                    color: controller.atmosphericTransparency.running ? theme.cyan : theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                visible: controller.localAtmosphere.visible
                title: qsTr("Particolato locale")
                subtitle: qsTr("OpenAQ PM2.5/PM10")
                accentColor: controller.localAtmosphere.freshnessWarning ? theme.amber : theme.teal

                GridLayout {
                    Layout.fillWidth: true
                    visible: controller.localAtmosphere.hasData
                    columns: root.width > 980 ? 4 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile { label: qsTr("PM2.5"); value: controller.localAtmosphere.pm25 }
                    MetricTile { label: qsTr("PM10"); value: controller.localAtmosphere.pm10 }
                    MetricTile { label: qsTr("Aria locale"); value: controller.localAtmosphere.clarity }
                    MetricTile { label: qsTr("Fonte"); value: controller.localAtmosphere.source }
                    MetricTile { label: qsTr("Freschezza"); value: controller.localAtmosphere.freshness }
                }

                Text {
                    Layout.fillWidth: true
                    visible: controller.localAtmosphere.sourceDetail.length > 0
                    text: controller.localAtmosphere.sourceDetail
                    color: controller.localAtmosphere.freshnessWarning ? theme.amber : theme.textMuted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    visible: !controller.localAtmosphere.hasData
                    text: controller.localAtmosphere.message
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Copertura nuvolosa oraria")
                subtitle: qsTr("Previsione mobile delle prossime 24 ore")
                accentColor: controller.hasValidLocation
                             ? theme.scoreColor(controller.weatherSummary.scoreValue)
                             : theme.textMuted
                headerContent: [
                    RowLayout {
                        spacing: 7

                        Rectangle {
                            Layout.preferredWidth: 11
                            Layout.preferredHeight: 11
                            radius: 3
                            color: theme.teal
                        }

                        Text {
                            text: qsTr("Notte osservativa")
                            color: theme.textSecondary
                            font.pixelSize: 11
                        }
                    }
                ]

                WeatherBars {
                    visible: root.displayWeatherHours.length > 0
                    hourly: root.displayWeatherHours
                    barColor: theme.textMuted
                    nightBarColor: theme.teal
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.displayWeatherHours.length === 0
                    text: !controller.hasValidLocation
                          ? qsTr("Dati non disponibili senza località.")
                          : controller.isLoading || controller.weatherRefreshRunning
                            ? qsTr("Caricamento meteo...")
                            : controller.weatherStatus.length > 0
                              ? controller.weatherStatus
                              : qsTr("Dati meteo non disponibili al momento.")
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Dettaglio orario")
                subtitle: qsTr("Previsione mobile delle prossime 24 ore")
                accentColor: theme.teal

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 86
                    visible: root.displayWeatherHours.length > 0
                    radius: 8
                    color: theme.surfaceLow
                    border.color: theme.border
                    border.width: 1
                    clip: true

                    ListView {
                        id: weatherHourList

                        anchors.fill: parent
                        anchors.margins: 8
                        orientation: ListView.Horizontal
                        spacing: 8
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        model: root.displayWeatherHours

                        delegate: Rectangle {
                            id: weatherHourDelegate

                            required property int index
                            required property var modelData

                            width: 94
                            height: ListView.view.height
                            radius: 8
                            property bool selectedHour: weatherHourDelegate.index === root.selectedWeatherHourIndex()
                            property bool nightHour: Boolean(weatherHourDelegate.modelData.isObservingNight)
                            color: selectedHour
                                   ? theme.withAlpha(theme.cyan, 0.18)
                                   : nightHour
                                     ? theme.withAlpha(theme.teal, 0.08)
                                     : theme.field
                            border.color: selectedHour
                                          ? theme.cyan
                                          : nightHour
                                            ? theme.withAlpha(theme.teal, 0.55)
                                            : theme.border
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 3

                                Text {
                                    Layout.fillWidth: true
                                    text: weatherHourDelegate.modelData.time
                                    color: weatherHourDelegate.selectedHour
                                           ? theme.cyan
                                           : weatherHourDelegate.nightHour ? theme.teal : theme.textPrimary
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: qsTr("%1 pioggia").arg(weatherHourDelegate.modelData.precipitationProbabilityLabel)
                                    color: theme.textSecondary
                                    font.pixelSize: 11
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: weatherHourDelegate.modelData.temperatureLabel
                                    color: theme.textMuted
                                    font.pixelSize: 11
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.selectedWeatherHourTimestamp = weatherHourDelegate.modelData.timestamp
                            }
                        }

                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    visible: root.displayWeatherHours.length > 0
                    columns: root.width > 980 ? 3 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile { label: qsTr("Orario"); value: root.selectedHourText("time", "-") }
                    MetricTile { label: qsTr("Nuvolosità"); value: root.selectedHourText("cloudCoverLabel", "-") }
                    MetricTile { label: qsTr("Pioggia"); value: root.selectedHourText("precipitationProbabilityLabel", "-") }
                    MetricTile { label: qsTr("Vento"); value: root.selectedHourText("windLabel", "-") }
                    MetricTile { label: qsTr("Umidità"); value: root.selectedHourText("humidityLabel", "-") }
                    MetricTile { label: qsTr("Temperatura"); value: root.selectedHourText("temperatureLabel", "-") }
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.displayWeatherHours.length === 0
                    text: !controller.hasValidLocation
                          ? qsTr("Dati non disponibili senza località.")
                          : controller.isLoading || controller.weatherRefreshRunning
                            ? qsTr("Caricamento meteo...")
                            : controller.weatherStatus.length > 0
                              ? controller.weatherStatus
                              : qsTr("Dati meteo non disponibili al momento.")
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

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

    function selectedHourText(key, suffix, fallbackText) {
        var hour = root.selectedWeatherHour()
        if (!hour || hour[key] === undefined || hour[key] === null)
            return fallbackText
        return hour[key] + suffix
    }

    function skyQualityConfidenceText() {
        var quality = controller.skyQuality || {}
        return quality.confidenceLabel || quality.confidence || "n/d"
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
                        text: "Meteo osservativo"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.hasValidLocation ? "Meteo per: " + controller.activeLocationLabel + " - " + controller.activeLocationSource : "Configura una posizione per visualizzare il meteo."
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }

                DarkButton {
                    Layout.preferredWidth: 118
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    text: controller.weatherRefreshRunning ? "Aggiorno..." : "Aggiorna"
                    enabled: controller.hasValidLocation && !controller.weatherRefreshRunning && !controller.startupLocationDetectionRunning
                    accentColor: theme.cyan
                    onClicked: controller.refreshWeatherNow()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                visible: controller.isLoading || controller.weatherRefreshRunning || controller.weatherStatus.length > 0
                radius: 8
                color: "#1c222b"
                border.color: controller.weatherRefreshRunning || controller.isLoading ? theme.cyan : theme.coral
                border.width: 1
                implicitHeight: weatherStateText.implicitHeight + 22

                Text {
                    id: weatherStateText
                    anchors.fill: parent
                    anchors.margins: 11
                    text: controller.weatherRefreshRunning ? "Aggiornamento meteo in corso..." : controller.isLoading ? "Caricamento meteo..." : controller.weatherStatus
                    color: theme.textPrimary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 2
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1050 ? 4 : 3
                columnSpacing: 12
                rowSpacing: 12

                MetricTile { label: "Nuvolosità"; value: controller.weatherSummary.cloudCover + "%"; accentColor: theme.cyan }
                MetricTile { label: "Precipitazioni"; value: controller.weatherSummary.precipitationProbability + "%"; accentColor: theme.coral }
                MetricTile { label: "Vento"; value: controller.weatherSummary.windKmh + " km/h"; accentColor: theme.teal }
                MetricTile { label: "Umidità"; value: controller.weatherSummary.humidity + "%"; accentColor: theme.violet }
                MetricTile { label: "Temperatura"; value: controller.weatherSummary.temperatureC + " °C"; accentColor: theme.amber }
                MetricTile { label: "Seeing"; value: controller.seeingTransparency.seeing; accentColor: theme.green }
                MetricTile { label: "Trasparenza meteo"; value: controller.seeingTransparency.transparency; accentColor: theme.cyan }
                MetricTile { label: "Bortle"; value: controller.skyQuality.bortleClass + " - " + controller.skyQuality.description; accentColor: theme.violet }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Qualità cielo locale"
                subtitle: controller.skyQuality.source
                accentColor: theme.violet

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 980 ? 4 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile {
                        visible: controller.skyQuality.hasViirsRadiance
                        label: "Osservazioni VIIRS"
                        value: controller.skyQuality.viirsObservationCount + " obs"
                        accentColor: theme.violet
                    }
                    MetricTile {
                        label: controller.skyQuality.hasViirsRadiance ? "Radianza VIIRS" : "SQM"
                        value: controller.skyQuality.hasViirsRadiance ? controller.skyQuality.viirsRadiance + " nW/cm2 sr" : controller.skyQuality.skyBrightness + " mag/arcsec2"
                        accentColor: theme.cyan
                    }
                    MetricTile {
                        label: controller.skyQuality.hasViirsRadiance ? "SQM stimato" : "Limite visuale"
                        value: controller.skyQuality.hasViirsRadiance ? controller.skyQuality.skyBrightness + " mag/arcsec2" : controller.skyQuality.limitingMagnitude + " mag"
                        accentColor: theme.teal
                    }
                    MetricTile { label: "Confidenza"; value: root.skyQualityConfidenceText(); accentColor: theme.amber }
                }

                Text {
                    Layout.fillWidth: true
                    text: "Seeing: " + controller.seeingTransparency.source + " (" + controller.seeingTransparency.confidence + ")"
                    color: theme.textMuted
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }

                Text {
                    Layout.fillWidth: true
                    visible: controller.viirsSkyQualityRunning || controller.lightPollutionStatus.length > 0
                    text: controller.viirsSkyQualityRunning ? "Recupero dati VIIRS NASA..." : controller.lightPollutionStatus
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
                title: "Aerosol atmosferico"
                subtitle: "NASA MAIAC AOD"
                accentColor: controller.atmosphericTransparency.running ? theme.cyan : controller.atmosphericTransparency.hasData ? theme.green : theme.amber

                GridLayout {
                    Layout.fillWidth: true
                    visible: controller.atmosphericTransparency.hasData
                    columns: root.width > 980 ? 4 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile { label: "AOD 550 nm"; value: controller.atmosphericTransparency.aod550; accentColor: theme.cyan }
                    MetricTile { label: "Effetto aerosol"; value: controller.atmosphericTransparency.transparency; accentColor: theme.green }
                    MetricTile { label: "Freschezza"; value: controller.atmosphericTransparency.freshness; accentColor: theme.amber }
                    MetricTile { label: "Fonte"; value: controller.atmosphericTransparency.productLabel; accentColor: theme.violet }
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
                    text: controller.atmosphericTransparency.running ? "Recupero dati NASA AOD..." : controller.atmosphericTransparency.message
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
                title: "Particolato locale"
                subtitle: "OpenAQ PM2.5/PM10"
                accentColor: controller.localAtmosphere.freshnessWarning ? theme.amber : theme.teal

                GridLayout {
                    Layout.fillWidth: true
                    visible: controller.localAtmosphere.hasData
                    columns: root.width > 980 ? 4 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile { label: "PM2.5"; value: controller.localAtmosphere.pm25; accentColor: theme.teal }
                    MetricTile { label: "PM10"; value: controller.localAtmosphere.pm10; accentColor: theme.cyan }
                    MetricTile { label: "Aria locale"; value: controller.localAtmosphere.clarity; accentColor: theme.amber }
                    MetricTile { label: "Fonte"; value: controller.localAtmosphere.source; accentColor: theme.violet }
                    MetricTile { label: "Freschezza"; value: controller.localAtmosphere.freshness; accentColor: theme.amber }
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
                title: "Copertura nuvolosa oraria"
                subtitle: "Previsione mobile delle prossime 24 ore"
                accentColor: theme.scoreColor(controller.weatherSummary.score)

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 7

                    Item { Layout.fillWidth: true }

                    Rectangle {
                        Layout.preferredWidth: 11
                        Layout.preferredHeight: 11
                        radius: 3
                        color: theme.teal
                    }

                    Text {
                        text: "Notte osservativa"
                        color: theme.textSecondary
                        font.pixelSize: 11
                    }
                }

                WeatherBars {
                    visible: root.displayWeatherHours.length > 0
                    hourly: root.displayWeatherHours
                    barColor: theme.textMuted
                    nightBarColor: theme.teal
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.displayWeatherHours.length === 0
                    text: controller.isLoading || controller.weatherRefreshRunning ? "Caricamento meteo..." : controller.weatherStatus.length > 0 ? controller.weatherStatus : "Dati meteo non disponibili al momento."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Dettaglio orario"
                subtitle: "Previsione mobile delle prossime 24 ore"
                accentColor: theme.teal

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 86
                    visible: root.displayWeatherHours.length > 0
                    radius: 8
                    color: "#15181e"
                    border.color: "#303641"
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
                                   ? Qt.rgba(theme.cyan.r, theme.cyan.g, theme.cyan.b, 0.18)
                                   : nightHour
                                     ? Qt.rgba(theme.teal.r, theme.teal.g, theme.teal.b, 0.08)
                                   : "#1c222b"
                            border.color: selectedHour
                                          ? theme.cyan
                                          : nightHour
                                            ? Qt.rgba(theme.teal.r, theme.teal.g, theme.teal.b, 0.55)
                                          : "#303641"
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
                                    text: weatherHourDelegate.modelData.precipitationProbability + "% pioggia"
                                    color: theme.textSecondary
                                    font.pixelSize: 11
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: weatherHourDelegate.modelData.temperatureC + " °C"
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

                    MetricTile { label: "Orario"; value: root.selectedHourText("time", "", "-"); accentColor: theme.cyan }
                    MetricTile { label: "Nuvolosità"; value: root.selectedHourText("cloudCover", "%", "-"); accentColor: theme.cyan }
                    MetricTile { label: "Pioggia"; value: root.selectedHourText("precipitationProbability", "%", "-"); accentColor: theme.coral }
                    MetricTile { label: "Vento"; value: root.selectedHourText("windKmh", " km/h", "-"); accentColor: theme.teal }
                    MetricTile { label: "Umidità"; value: root.selectedHourText("humidity", "%", "-"); accentColor: theme.violet }
                    MetricTile { label: "Temperatura"; value: root.selectedHourText("temperatureC", " °C", "-"); accentColor: theme.amber }
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.displayWeatherHours.length === 0
                    text: controller.isLoading || controller.weatherRefreshRunning ? "Caricamento meteo..." : controller.weatherStatus.length > 0 ? controller.weatherStatus : "Dati meteo non disponibili al momento."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

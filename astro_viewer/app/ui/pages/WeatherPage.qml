import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property int selectedWeatherHourIndex: 0

    function selectedWeatherHour() {
        if (controller.weatherHourly.length === 0)
            return null
        var index = Math.max(0, Math.min(root.selectedWeatherHourIndex, controller.weatherHourly.length - 1))
        return controller.weatherHourly[index]
    }

    function selectedHourText(key, suffix, fallbackText) {
        var hour = root.selectedWeatherHour()
        if (!hour || hour[key] === undefined || hour[key] === null)
            return fallbackText
        return hour[key] + suffix
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

                StatusPill {
                    text: controller.weatherSummary.score
                    accentColor: theme.scoreColor(controller.weatherSummary.score)
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                visible: controller.isLoading || controller.weatherStatus.length > 0
                radius: 8
                color: "#1c222b"
                border.color: controller.weatherStatus.length > 0 ? theme.coral : theme.cyan
                border.width: 1
                implicitHeight: weatherStateText.implicitHeight + 22

                Text {
                    id: weatherStateText
                    anchors.fill: parent
                    anchors.margins: 11
                    text: controller.isLoading ? "Loading weather..." : controller.weatherStatus
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

                MetricTile { label: "Nuvolosita"; value: controller.weatherSummary.cloudCover + "%"; accentColor: theme.cyan }
                MetricTile { label: "Precipitazioni"; value: controller.weatherSummary.precipitationProbability + "%"; accentColor: theme.coral }
                MetricTile { label: "Vento"; value: controller.weatherSummary.windKmh + " km/h"; accentColor: theme.teal }
                MetricTile { label: "Umidita"; value: controller.weatherSummary.humidity + "%"; accentColor: theme.violet }
                MetricTile { label: "Temperatura"; value: controller.weatherSummary.temperatureC + " C"; accentColor: theme.amber }
                MetricTile { label: "Seeing"; value: controller.seeingTransparency.seeing; accentColor: theme.green }
                MetricTile { label: "Transparency"; value: controller.seeingTransparency.transparency; accentColor: theme.cyan }
                MetricTile { label: "Bortle"; value: controller.skyQuality.bortleClass + " - " + controller.skyQuality.description; accentColor: theme.violet }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Qualita cielo locale"
                subtitle: controller.skyQuality.source
                accentColor: theme.violet

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 980 ? 4 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile { label: "Bortle"; value: controller.skyQuality.bortleClass.toString(); accentColor: theme.violet }
                    MetricTile { label: "SQM"; value: controller.skyQuality.skyBrightness + " mag/arcsec2"; accentColor: theme.cyan }
                    MetricTile { label: "Limite visuale"; value: controller.skyQuality.limitingMagnitude + " mag"; accentColor: theme.teal }
                    MetricTile { label: "Confidenza"; value: controller.skyQuality.confidence; accentColor: theme.amber }
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
                title: "Copertura nuvolosa oraria"
                subtitle: "Percentuale prevista durante la finestra notturna"
                accentColor: theme.scoreColor(controller.weatherSummary.score)

                WeatherBars {
                    visible: controller.weatherHourly.length > 0
                    hourly: controller.weatherHourly
                    barColor: theme.scoreColor(controller.weatherSummary.score)
                }

                Text {
                    Layout.fillWidth: true
                    visible: controller.weatherHourly.length === 0
                    text: controller.isLoading ? "Loading weather..." : "Weather service temporarily unavailable."
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
                subtitle: "Seleziona un orario per leggere i dettagli"
                accentColor: theme.teal

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 86
                    visible: controller.weatherHourly.length > 0
                    radius: 8
                    color: "#15181e"
                    border.color: "#303641"
                    border.width: 1
                    clip: true

                    ListView {
                        anchors.fill: parent
                        anchors.margins: 8
                        orientation: ListView.Horizontal
                        spacing: 8
                        clip: true
                        boundsBehavior: Flickable.StopAtBounds
                        model: controller.weatherHourly

                        delegate: Rectangle {
                            width: 94
                            height: ListView.view.height
                            radius: 8
                            color: index === Math.max(0, Math.min(root.selectedWeatherHourIndex, controller.weatherHourly.length - 1))
                                   ? Qt.rgba(theme.teal.r, theme.teal.g, theme.teal.b, 0.18)
                                   : "#1c222b"
                            border.color: index === Math.max(0, Math.min(root.selectedWeatherHourIndex, controller.weatherHourly.length - 1))
                                          ? theme.teal
                                          : "#303641"
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 8
                                spacing: 3

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.time
                                    color: theme.textPrimary
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.precipitationProbability + "% pioggia"
                                    color: theme.textSecondary
                                    font.pixelSize: 11
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.temperatureC + " C"
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
                                onClicked: root.selectedWeatherHourIndex = index
                            }
                        }
                    }
                }

                GridLayout {
                    Layout.fillWidth: true
                    visible: controller.weatherHourly.length > 0
                    columns: root.width > 980 ? 3 : 2
                    columnSpacing: 12
                    rowSpacing: 12

                    MetricTile { label: "Orario"; value: root.selectedHourText("time", "", "-"); accentColor: theme.teal }
                    MetricTile { label: "Nuvolosita"; value: root.selectedHourText("cloudCover", "%", "-"); accentColor: theme.cyan }
                    MetricTile { label: "Pioggia"; value: root.selectedHourText("precipitationProbability", "%", "-"); accentColor: theme.coral }
                    MetricTile { label: "Vento"; value: root.selectedHourText("windKmh", " km/h", "-"); accentColor: theme.teal }
                    MetricTile { label: "Umidita"; value: root.selectedHourText("humidity", "%", "-"); accentColor: theme.violet }
                    MetricTile { label: "Temperatura"; value: root.selectedHourText("temperatureC", " C", "-"); accentColor: theme.amber }
                }

                Text {
                    Layout.fillWidth: true
                    visible: controller.weatherHourly.length === 0
                    text: controller.isLoading ? "Loading weather..." : "No weather forecast available."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

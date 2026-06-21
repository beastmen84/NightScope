import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller

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
                        text: controller.weatherSummary.alert
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
                title: "Copertura nuvolosa oraria"
                subtitle: "Percentuale prevista durante la finestra notturna"
                accentColor: theme.scoreColor(controller.weatherSummary.score)

                WeatherBars {
                    hourly: controller.weatherHourly
                    barColor: theme.scoreColor(controller.weatherSummary.score)
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Dettaglio orario"
                subtitle: "Cloud cover, pioggia, vento, umidita e temperatura"
                accentColor: theme.teal

                Repeater {
                    model: controller.weatherHourly

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        StatusPill {
                            text: modelData.time
                            accentColor: theme.cyan
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "Nuvole " + modelData.cloudCover + "%  -  Pioggia " + modelData.precipitationProbability + "%  -  Vento " + modelData.windKmh + " km/h"
                            color: theme.textPrimary
                            font.pixelSize: 14
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.preferredWidth: 160
                            text: modelData.humidity + "%  -  " + modelData.temperatureC + " C"
                            color: theme.textSecondary
                            horizontalAlignment: Text.AlignRight
                            font.pixelSize: 13
                            elide: Text.ElideRight
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

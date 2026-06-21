import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    signal openObject(string objectId)

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

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 18
            }

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
                        text: "Stasera dal tuo cielo"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.location.city + "  -  " + controller.location.timezone
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
                id: grid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1120 ? 3 : 2
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: grid.columns > 1 ? 2 : 1
                    title: "Stasera dal tuo cielo"
                    subtitle: "Target ordinati per utilita osservativa"
                    accentColor: theme.cyan

                    Repeater {
                        model: controller.tonightHighlights

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatusPill {
                                text: modelData.bestTime
                                accentColor: theme.cyan
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: theme.textPrimary
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.setup
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Qualita osservativa stanotte"
                    subtitle: controller.observingQuality.explanation
                    accentColor: theme.scoreColor(controller.observingQuality.score)

                    Text {
                        Layout.fillWidth: true
                        text: controller.observingQuality.scoreValue + "/100"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    StatusPill {
                        text: controller.observingQuality.score
                        accentColor: theme.scoreColor(controller.observingQuality.score)
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.observingQuality.alert
                        color: theme.textSecondary
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        maximumLineCount: 3
                        elide: Text.ElideRight
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Sky Quality"
                    subtitle: controller.skyQuality.description
                    accentColor: theme.violet

                    Text {
                        Layout.fillWidth: true
                        text: "Bortle " + controller.skyQuality.bortleClass
                        color: theme.textPrimary
                        font.pixelSize: 30
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Limite " + controller.skyQuality.limitingMagnitude + " mag  -  " + controller.skyQuality.skyBrightness + " mag/arcsec2"
                        color: theme.textSecondary
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Planetary Score"
                    subtitle: controller.advancedScores.explanation
                    accentColor: theme.teal

                    Text {
                        Layout.fillWidth: true
                        text: controller.advancedScores.planetaryScore + "/100"
                        color: theme.textPrimary
                        font.pixelSize: 32
                        font.weight: Font.DemiBold
                    }

                    StatusPill {
                        text: controller.advancedScores.planetaryLabel
                        accentColor: theme.scoreColor(controller.advancedScores.planetaryLabel)
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Deep Sky Score"
                    subtitle: "Trasparenza, Luna e inquinamento luminoso"
                    accentColor: theme.cyan

                    Text {
                        Layout.fillWidth: true
                        text: controller.advancedScores.deepSkyScore + "/100"
                        color: theme.textPrimary
                        font.pixelSize: 32
                        font.weight: Font.DemiBold
                    }

                    StatusPill {
                        text: controller.advancedScores.deepSkyLabel
                        accentColor: theme.scoreColor(controller.advancedScores.deepSkyLabel)
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Miglior oggetto della notte"
                    subtitle: controller.bestObjectOfNight.scoreExplanation
                    accentColor: theme.amber

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        Image {
                            Layout.preferredWidth: 82
                            Layout.preferredHeight: 82
                            source: controller.assetBaseUrl + "/" + controller.bestObjectOfNight.image
                            fillMode: Image.PreserveAspectFit
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                Layout.fillWidth: true
                                text: controller.bestObjectOfNight.name
                                color: theme.textPrimary
                                font.pixelSize: 20
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Score " + controller.bestObjectOfNight.score + "/100  -  " + controller.bestObjectOfNight.scoreLabel
                                color: theme.amber
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Osservazione consigliata: " + controller.bestObjectOfNight.observing_window
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Setup: " + controller.bestObjectOfNight.recommended_setup
                                color: theme.textMuted
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: grid.columns > 1 ? 2 : 1
                    title: "Night Planner"
                    subtitle: "Sequenza osservativa ottimizzata"
                    accentColor: theme.green

                    Repeater {
                        model: controller.nightPlan

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            StatusPill {
                                text: modelData.timeLabel
                                accentColor: theme.green
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name + "  -  " + modelData.difficulty + "  -  " + modelData.setup
                                color: theme.textPrimary
                                font.pixelSize: 13
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.preferredWidth: 64
                                text: modelData.score + "/100"
                                color: theme.textSecondary
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Sky Map"
                    subtitle: "Vista cardinale minimale"
                    accentColor: theme.cyan

                    Repeater {
                        model: controller.skyMap

                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 4

                            Text {
                                Layout.fillWidth: true
                                text: modelData.direction
                                color: theme.cyan
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.targets.length > 0 ? modelData.targets.map(function(item) { return item.name }).join(", ") : "Nessun target prioritario"
                                color: theme.textSecondary
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Luna"
                    subtitle: controller.moonSummary.phase + "  -  " + controller.moonSummary.illumination
                    accentColor: theme.amber

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        Image {
                            Layout.preferredWidth: 92
                            Layout.preferredHeight: 92
                            source: controller.assetBaseUrl + "/" + controller.moonSummary.image
                            fillMode: Image.PreserveAspectFit
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 8

                            Text {
                                Layout.fillWidth: true
                                text: "Sorge " + controller.moonSummary.rise_time + "  -  tramonta " + controller.moonSummary.set_time
                                color: theme.textPrimary
                                font.pixelSize: 14
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: controller.moonSummary.best_note
                                color: theme.textSecondary
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Pianeti visibili"
                    subtitle: "Visibilita serale e notturna"
                    accentColor: theme.teal

                    Repeater {
                        model: controller.visiblePlanets

                        delegate: ObjectRow {
                            itemData: modelData
                            assetBaseUrl: controller.assetBaseUrl
                            onOpenRequested: function(objectId) {
                                root.openObject(objectId)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: grid.columns > 1 ? 2 : 1
                    title: "Oggetti Deep Sky consigliati"
                    subtitle: "Priorita per la notte corrente"
                    accentColor: theme.violet

                    Repeater {
                        model: controller.recommendedDeepSky

                        delegate: ObjectRow {
                            itemData: modelData
                            assetBaseUrl: controller.assetBaseUrl
                            onOpenRequested: function(objectId) {
                                root.openObject(objectId)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Meteo osservativo"
                    subtitle: controller.weatherSummary.alert
                    accentColor: theme.scoreColor(controller.weatherSummary.score)

                    WeatherBars {
                        hourly: controller.weatherHourly
                        barColor: theme.scoreColor(controller.weatherSummary.score)
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: grid.columns > 1 ? 2 : 1
                    title: "Prossimi eventi astronomici"
                    subtitle: "Ordinati per utilita osservativa"
                    accentColor: theme.amber

                    Repeater {
                        model: controller.events.slice(0, 3)

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            StatusPill {
                                text: modelData.date_label
                                accentColor: theme.amber
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.title
                                    color: theme.textPrimary
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.note
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: grid.columns > 1 ? 2 : 1
                    title: "Notifiche intelligenti"
                    subtitle: "Promemoria generati dal planner"
                    accentColor: theme.coral

                    Repeater {
                        model: controller.notifications

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            StatusPill {
                                text: modelData.triggerTime
                                accentColor: theme.coral
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.title + "  -  " + modelData.message
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 28
            }
        }
    }
}

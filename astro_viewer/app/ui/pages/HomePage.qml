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
            spacing: 16

            Item { Layout.fillWidth: true; Layout.preferredHeight: 14 }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 18

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 5

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
                        text: controller.activeLocationLabel + "  -  " + controller.activeLocationSource
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }

                StatusPill {
                    text: controller.observingQuality.score
                    accentColor: theme.scoreColor(controller.observingQuality.score)
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                visible: controller.isLoading || controller.serviceStatus.length > 0
                radius: 8
                color: "#1c222b"
                border.color: controller.serviceStatus.length > 0 ? theme.coral : theme.cyan
                border.width: 1
                implicitHeight: statusText.implicitHeight + 22

                Text {
                    id: statusText
                    anchors.fill: parent
                    anchors.margins: 11
                    text: controller.isLoading ? "Aggiornamento dei dati del cielo..." : controller.serviceStatus
                    color: theme.textPrimary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 2
                }
            }

            GridLayout {
                id: topGrid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1420 ? 5 : root.width > 980 ? 3 : 1
                columnSpacing: 14
                rowSpacing: 14

                GlassCard {
                    Layout.fillWidth: true
                    title: "Qualita osservativa"
                    subtitle: controller.observingQuality.explanation
                    accentColor: theme.scoreColor(controller.observingQuality.score)

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Text {
                            text: controller.observingQuality.scoreValue + "/100"
                            color: theme.textPrimary
                            font.pixelSize: 34
                            font.weight: Font.DemiBold
                        }

                        StatusPill {
                            text: controller.observingQuality.score
                            accentColor: theme.scoreColor(controller.observingQuality.score)
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.weatherDigest.bestWindow !== "n/d" ? "Migliore finestra: " + controller.weatherDigest.bestWindow : controller.observingQuality.alert
                        color: theme.textSecondary
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: topGrid.columns >= 3 ? 2 : 1
                    title: "Miglior oggetto della notte"
                    subtitle: controller.bestObjectOfNight.observingStatusDetail
                    accentColor: theme.amber

                    Text {
                        Layout.fillWidth: true
                        visible: !controller.bestObjectOfNight.name
                        text: "Nessun oggetto visibile trovato per le condizioni correnti."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        visible: !!controller.bestObjectOfNight.name
                        spacing: 14

                        Image {
                            Layout.preferredWidth: 104
                            Layout.preferredHeight: 104
                            source: controller.assetBaseUrl + "/" + controller.bestObjectOfNight.image
                            fillMode: Image.PreserveAspectFit
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 5

                            Text {
                                Layout.fillWidth: true
                                text: controller.bestObjectOfNight.name
                                color: theme.textPrimary
                                font.pixelSize: 30
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            StatusPill {
                                text: controller.bestObjectOfNight.observingStatus
                                accentColor: controller.bestObjectOfNight.observingStatus === "Visible now" ? theme.green : theme.amber
                            }

                            Text {
                                Layout.fillWidth: true
                                text: controller.bestObjectOfNight.homeWindowLabel + "  -  " + controller.bestObjectOfNight.direction
                                color: theme.amber
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Setup: " + controller.bestObjectOfNight.recommended_setup
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Punteggio planetario"
                    subtitle: "Seeing " + controller.seeingTransparency.seeing + ", vento " + controller.weatherDigest.windLabel
                    accentColor: theme.teal

                    Text {
                        Layout.fillWidth: true
                        text: controller.advancedScores.planetaryScore + "/100"
                        color: theme.textPrimary
                        font.pixelSize: 31
                        font.weight: Font.DemiBold
                    }

                    StatusPill {
                        text: controller.advancedScores.planetaryLabel
                        accentColor: theme.scoreColor(controller.advancedScores.planetaryLabel)
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Punteggio cielo profondo"
                    subtitle: "Bortle " + controller.skyQuality.bortleClass + ", " + controller.skyQuality.description
                    accentColor: theme.violet

                    Text {
                        Layout.fillWidth: true
                        text: controller.advancedScores.deepSkyScore + "/100"
                        color: theme.textPrimary
                        font.pixelSize: 31
                        font.weight: Font.DemiBold
                    }

                    StatusPill {
                        text: controller.advancedScores.deepSkyLabel
                        accentColor: theme.scoreColor(controller.advancedScores.deepSkyLabel)
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                text: "Piano della notte"
                color: theme.textPrimary
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            GridLayout {
                id: centerGrid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1180 ? 3 : 1
                columnSpacing: 14
                rowSpacing: 14

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: centerGrid.columns > 1 ? 2 : 1
                    title: "Piano osservativo"
                    subtitle: "Sequenza ordinata per utilita e finestra notturna"
                    accentColor: theme.green

                    Text {
                        Layout.fillWidth: true
                        visible: controller.nightPlan.length === 0
                        text: controller.isLoading ? "Aggiornamento del piano osservativo..." : "Nessun target utile nella finestra notturna."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.nightPlan.slice(0, 4)

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
                                Layout.preferredWidth: 58
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
                    title: "Luna"
                    subtitle: controller.moonSummary.phase + "  -  " + controller.moonSummary.illumination
                    accentColor: theme.amber

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Image {
                            Layout.preferredWidth: 70
                            Layout.preferredHeight: 70
                            source: controller.assetBaseUrl + "/" + controller.moonSummary.image
                            fillMode: Image.PreserveAspectFit
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 6

                            Text {
                                Layout.fillWidth: true
                                text: "Sorge " + controller.moonSummary.rise_time + "  -  tramonta " + controller.moonSummary.set_time
                                color: theme.textPrimary
                                font.pixelSize: 13
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: controller.moonSummary.best_note
                                color: theme.textSecondary
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                maximumLineCount: 3
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: centerGrid.columns > 1 ? 3 : 1
                    title: "Pianeti visibili"
                    subtitle: "Solo target utili per la sera, la notte o prima dell'alba"
                    accentColor: theme.teal

                    Text {
                        Layout.fillWidth: true
                        visible: controller.visiblePlanets.length === 0
                        text: controller.isLoading ? "Calcolo della visibilita..." : "Nessun pianeta utile nella finestra notturna."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 1180 ? 2 : 1
                        columnSpacing: 10
                        rowSpacing: 4

                        Repeater {
                            model: controller.visiblePlanets.slice(0, 4)

                            delegate: ObjectRow {
                                itemData: modelData
                                assetBaseUrl: controller.assetBaseUrl
                                onOpenRequested: function(objectId) {
                                    root.openObject(objectId)
                                }
                            }
                        }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                text: "Dettagli osservativi"
                color: theme.textPrimary
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            GridLayout {
                id: lowerGrid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 14
                rowSpacing: 14

                GlassCard {
                    Layout.fillWidth: true
                    title: "Oggetti cielo profondo consigliati"
                    subtitle: controller.skyQualityWarning.length > 0 ? controller.skyQualityWarning : "Priorita per la notte corrente"
                    accentColor: theme.violet

                    Text {
                        Layout.fillWidth: true
                        visible: controller.recommendedDeepSky.length === 0
                        text: controller.isLoading ? "Calcolo della visibilita..." : "Nessun oggetto cielo profondo utile nelle condizioni correnti."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.recommendedDeepSky.slice(0, 4)

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
                    subtitle: controller.weatherStatus.length > 0 ? controller.weatherStatus : "Migliore finestra: " + controller.weatherDigest.bestWindow
                    accentColor: theme.scoreColor(controller.weatherSummary.score)

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 3
                        columnSpacing: 8
                        rowSpacing: 8

                        Text {
                            Layout.fillWidth: true
                            text: "Nuvolosita media\n" + controller.weatherDigest.cloudAverage + "%"
                            color: theme.textPrimary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "Vento\n" + controller.weatherDigest.windLabel
                            color: theme.textPrimary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "Pioggia max\n" + controller.weatherDigest.rainProbability + "%"
                            color: theme.textPrimary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }
                    }

                    Repeater {
                        model: controller.weatherDigest.bestHours

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatusPill {
                                text: modelData.time
                                accentColor: theme.scoreColor(controller.weatherSummary.score)
                            }

                            Text {
                                Layout.fillWidth: true
                                text: "Nuvole " + modelData.cloudCover + "%  -  Vento " + modelData.windKmh + " km/h  -  Pioggia " + modelData.rainProbability + "%"
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Mappa cielo"
                    subtitle: "Vista cardinale minimale"
                    accentColor: theme.cyan

                    Repeater {
                        model: controller.skyMap

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.preferredWidth: 52
                                text: modelData.direction
                                color: theme.cyan
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.targets.length > 0 ? modelData.targets.map(function(item) { return item.name }).join(", ") : "Nessun target prioritario"
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Prossimi eventi"
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
                                    font.pixelSize: 14
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
                    Layout.columnSpan: lowerGrid.columns > 1 ? 2 : 1
                    title: "Notifiche intelligenti"
                    subtitle: "Promemoria generati dal piano osservativo"
                    accentColor: theme.coral

                    Repeater {
                        model: controller.notifications.slice(0, 3)

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

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

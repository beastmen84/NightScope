import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var objectData: controller.selectedObject
    property bool hasObject: objectData && objectData.name !== undefined && objectData.name !== ""
    property int detailMetricHeight: 88
    signal backToHome()

    function distinctSetupOptions(options) {
        var result = []
        var seen = {}
        options = options || []
        for (var i = 0; i < options.length; i++) {
            var key = options[i].detailLabel || options[i].label || ""
            if (key.length === 0 || seen[key])
                continue
            seen[key] = true
            result.push(options[i])
        }
        return result
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

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 14
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 14

                DarkButton {
                    text: "Torna alla Home"
                    accentColor: theme.cyan
                    onClicked: root.backToHome()
                }

                Text {
                    Layout.fillWidth: true
                    text: root.hasObject ? "Dettaglio osservativo" : "Nessun oggetto selezionato"
                    color: theme.textSecondary
                    font.pixelSize: 13
                    elide: Text.ElideRight
                }
            }

            RowLayout {
                visible: root.hasObject
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 18

                ColumnLayout {
                    Layout.preferredWidth: 420
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

                    Rectangle {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 300
                        radius: 8
                        color: "#111319"
                        border.color: "#303641"
                        border.width: 1

                        Image {
                            anchors.fill: parent
                            anchors.margins: 30
                            source: root.hasObject ? controller.assetBaseUrl + "/" + objectData.image : ""
                            fillMode: Image.PreserveAspectFit
                            sourceSize.width: 520
                            sourceSize.height: 520
                        }
                    }

                    GlassCard {
                        Layout.fillWidth: true
                        title: "Finestra osservativa"
                        subtitle: objectData.time_above_horizon + " sopra l'orizzonte"
                        accentColor: theme.teal

                        Text {
                            Layout.fillWidth: true
                            text: objectData.homeWindowLabel
                            color: theme.textPrimary
                            font.pixelSize: 30
                            font.weight: Font.DemiBold
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

                    StatusPill {
                        text: objectData.observingStatus
                        accentColor: objectData.observingStatus === "Osservabile ora" ? theme.green
                                     : objectData.observingStatus === "Non osservabile" ? theme.coral
                                     : theme.amber
                    }

                    Text {
                        Layout.fillWidth: true
                        text: objectData.name
                        color: theme.textPrimary
                        font.pixelSize: 40
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: objectData.observingStatusDetail
                        color: theme.amber
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: objectData.notes
                        color: theme.textSecondary
                        font.pixelSize: 15
                        wrapMode: Text.WordWrap
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 1000 ? 3 : 2
                        columnSpacing: 12
                        rowSpacing: 12

                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Magnitudine"; value: objectData.magnitude; accentColor: theme.cyan }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Distanza"; value: objectData.distance; accentColor: theme.violet }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Altezza massima"; value: objectData.max_altitude; accentColor: theme.teal }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Direzione"; value: objectData.direction; accentColor: theme.amber }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Finestra migliore"; value: objectData.homeWindowLabel; accentColor: theme.green }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Azimut"; value: objectData.azimuth; accentColor: theme.coral }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Altezza attuale"; value: objectData.currentAltitude; accentColor: theme.cyan }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Sorge"; value: objectData.riseTime; accentColor: theme.teal }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Tramonta"; value: objectData.setTime; accentColor: theme.amber }
                    }
                }
            }

            GlassCard {
                visible: root.hasObject
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Setup consigliato"
                subtitle: "Suggerimento operativo"
                accentColor: theme.amber

                Text {
                    Layout.fillWidth: true
                    text: objectData.recommended_setup
                    color: theme.textPrimary
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: root.distinctSetupOptions(objectData.setupOptions)

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        StatusPill {
                            text: modelData.role
                            accentColor: modelData.role === "Consigliato" ? theme.amber
                                         : modelData.role === "Campo largo" ? theme.teal
                                         : theme.cyan
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.detailLabel || modelData.label
                            color: theme.textPrimary
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Text {
                            text: modelData.magnification + "  -  " + modelData.trueField + "  -  " + modelData.exitPupil
                            color: theme.textSecondary
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: "Oculare: " + objectData.bestEyepiece + "  -  Barlow: " + objectData.barlow + "  -  Difficolta: " + objectData.difficulty
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                visible: !root.hasObject
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Seleziona un oggetto dalla Home"
                subtitle: "Il dettaglio si apre dai target consigliati"
                accentColor: theme.cyan

                Text {
                    Layout.fillWidth: true
                    text: "Torna alla Home e scegli un pianeta, un oggetto deep-sky o una voce del piano osservativo."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                visible: root.hasObject
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Perche consigliato"
                subtitle: "Ragionamento sintetico per l'osservazione"
                accentColor: theme.green

                Repeater {
                    model: objectData.observingReasons || []

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        StatusPill {
                            text: "-"
                            accentColor: theme.green
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            color: theme.textPrimary
                            font.pixelSize: 14
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            GlassCard {
                visible: root.hasObject
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Storico osservazioni"
                subtitle: "Note locali salvate nel database SQLite"
                accentColor: theme.violet

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    DarkTextField {
                        id: observationRating
                        Layout.preferredWidth: 120
                        placeholderText: "Rating 0-5"
                        inputMethodHints: Qt.ImhDigitsOnly
                    }

                    DarkTextField {
                        id: observationNotes
                        Layout.fillWidth: true
                        placeholderText: "Note osservazione"
                    }

                    DarkButton {
                        text: "Salva"
                        accentColor: theme.violet
                        onClicked: controller.saveObservation(observationRating.text, observationNotes.text)
                    }
                }

                Repeater {
                    model: controller.observationHistory.slice(0, 4)

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        StatusPill {
                            text: modelData.rating + "/5"
                            accentColor: theme.violet
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData.date + "  -  " + modelData.object_name + "  -  " + modelData.notes
                            color: theme.textSecondary
                            font.pixelSize: 12
                            elide: Text.ElideRight
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

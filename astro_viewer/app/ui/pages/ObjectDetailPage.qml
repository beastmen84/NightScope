import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var objectData: controller.selectedObject

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
                spacing: 22

                Rectangle {
                    Layout.preferredWidth: 360
                    Layout.preferredHeight: 320
                    radius: 8
                    color: "#111319"
                    border.color: "#303641"
                    border.width: 1

                    Image {
                        anchors.fill: parent
                        anchors.margins: 32
                        source: controller.assetBaseUrl + "/" + objectData.image
                        fillMode: Image.PreserveAspectFit
                        sourceSize.width: 520
                        sourceSize.height: 520
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 14

                    StatusPill {
                        text: objectData.type + "  -  " + objectData.visibility_class
                        accentColor: theme.cyan
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

                        MetricTile { label: "Magnitudine"; value: objectData.magnitude; accentColor: theme.cyan }
                        MetricTile { label: "Distanza"; value: objectData.distance; accentColor: theme.violet }
                        MetricTile { label: "Altezza massima"; value: objectData.max_altitude; accentColor: theme.teal }
                        MetricTile { label: "Direzione"; value: objectData.direction; accentColor: theme.amber }
                        MetricTile { label: "Orario migliore"; value: objectData.best_time; accentColor: theme.green }
                        MetricTile { label: "Azimut"; value: objectData.azimuth; accentColor: theme.coral }
                        MetricTile { label: "Altezza attuale"; value: objectData.currentAltitude; accentColor: theme.cyan }
                        MetricTile { label: "Sorge"; value: objectData.riseTime; accentColor: theme.teal }
                        MetricTile { label: "Tramonta"; value: objectData.setTime; accentColor: theme.amber }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 980 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    title: "Finestra osservativa"
                    subtitle: objectData.time_above_horizon + " sopra l'orizzonte"
                    accentColor: theme.teal

                    Text {
                        Layout.fillWidth: true
                        text: objectData.observing_window
                        color: theme.textPrimary
                        font.pixelSize: 24
                        font.weight: Font.DemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Meglio osservabile tra le " + objectData.observing_window + "."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
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

                    Text {
                        Layout.fillWidth: true
                        text: "Oculare: " + objectData.bestEyepiece + "  -  Barlow: " + objectData.barlow + "  -  Difficolta: " + objectData.difficulty
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Storico osservazioni"
                subtitle: "Note locali salvate nel database SQLite"
                accentColor: theme.violet

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    TextField {
                        id: observationRating
                        Layout.preferredWidth: 120
                        placeholderText: "Rating 0-5"
                        inputMethodHints: Qt.ImhDigitsOnly
                    }

                    TextField {
                        id: observationNotes
                        Layout.fillWidth: true
                        placeholderText: "Note osservazione"
                    }

                    Button {
                        text: "Salva"
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

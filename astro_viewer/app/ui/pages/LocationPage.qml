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
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1040 ? 3 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    title: "Metodo 1"
                    subtitle: "Posizione Windows"
                    accentColor: theme.cyan

                    Text {
                        Layout.fillWidth: true
                        text: "Usa il consenso di Windows per stimare latitudine e longitudine."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Usa posizione Windows"
                        onClicked: controller.useWindowsLocation()
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Metodo 2"
                    subtitle: "Ricerca citta offline"
                    accentColor: theme.amber

                    TextField {
                        id: citySearch
                        Layout.fillWidth: true
                        placeholderText: "Cerca citta"
                        onTextChanged: controller.searchCities(text)
                    }

                    Repeater {
                        model: controller.cityResults.slice(0, 6)

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 42
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
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Metodo 3"
                    subtitle: "Coordinate manuali"
                    accentColor: theme.teal

                    TextField {
                        id: manualLabel
                        Layout.fillWidth: true
                        placeholderText: "Nome luogo"
                    }

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

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

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Text {
                        Layout.fillWidth: true
                        text: "Configurazione strumenti"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.currentSetup.name + "  -  Barlow " + controller.selectedBarlow + "x"
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Modalita principianti"
                subtitle: "Preset immediatamente utilizzabili"
                accentColor: theme.teal

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1080 ? 5 : 3
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: controller.beginnerPresets

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 122
                            radius: 8
                            color: "#20242b"
                            border.color: "#303641"
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: theme.textPrimary
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.target
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.suggestedObjects
                                    color: theme.textMuted
                                    font.pixelSize: 11
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1100 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    title: "Setup telescopi"
                    subtitle: "Rifrattore, Newton, Schmidt-Cassegrain e Maksutov"
                    accentColor: theme.cyan

                    Repeater {
                        model: controller.equipmentSetups

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 58
                            radius: 8
                            color: setupMouse.containsMouse ? "#20242b" : "transparent"
                            border.color: setupMouse.containsMouse ? "#303641" : "transparent"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.name
                                        color: theme.textPrimary
                                        font.pixelSize: 14
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.type + "  -  " + modelData.mount
                                        color: theme.textSecondary
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                    }
                                }

                                Text {
                                    text: modelData.apertureMm + " / " + modelData.focalLengthMm + " mm"
                                    color: theme.cyan
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }
                            }

                            MouseArea {
                                id: setupMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: controller.selectEquipmentSetup(index)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Aggiungi telescopio"
                    subtitle: "Setup personalizzato in memoria"
                    accentColor: theme.amber

                    TextField { id: telescopeName; Layout.fillWidth: true; placeholderText: "Nome" }
                    TextField { id: telescopeAperture; Layout.fillWidth: true; placeholderText: "Apertura mm"; inputMethodHints: Qt.ImhDigitsOnly }
                    TextField { id: telescopeFocal; Layout.fillWidth: true; placeholderText: "Focale mm"; inputMethodHints: Qt.ImhDigitsOnly }

                    ComboBox {
                        id: telescopeType
                        Layout.fillWidth: true
                        model: ["rifrattore", "Newton", "Schmidt-Cassegrain", "Maksutov"]
                    }

                    TextField { id: telescopeMount; Layout.fillWidth: true; placeholderText: "Montatura" }

                    Button {
                        Layout.fillWidth: true
                        text: "Aggiungi setup"
                        onClicked: controller.addTelescope(telescopeName.text, telescopeAperture.text, telescopeFocal.text, telescopeType.currentText, telescopeMount.text)
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Oculari e calcoli"
                subtitle: "Ingrandimento, campo reale e pupilla d'uscita"
                accentColor: theme.violet

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    StatusPill { text: controller.currentSetup.name; accentColor: theme.violet }

                    Button {
                        text: "1x"
                        onClicked: controller.setBarlow(1.0)
                    }

                    Button {
                        text: "Barlow 2x"
                        onClicked: controller.setBarlow(2.0)
                    }

                    Button {
                        text: "Barlow 3x"
                        onClicked: controller.setBarlow(3.0)
                    }
                }

                Repeater {
                    model: controller.telescopeCalculations

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 14

                        Text {
                            Layout.fillWidth: true
                            text: modelData.eyepiece
                            color: theme.textPrimary
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        StatusPill { text: modelData.magnification; accentColor: theme.cyan }
                        StatusPill { text: modelData.trueField; accentColor: theme.teal }
                        StatusPill { text: modelData.exitPupil; accentColor: theme.amber }
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

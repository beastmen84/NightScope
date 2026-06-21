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
            spacing: 16

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
                        text: "Calendario astronomico"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Opposizioni, congiunzioni, Luna, eclissi e sciami meteorici"
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
                title: "Prossimi 30 giorni"
                subtitle: "Highlights osservativi da controllare per primi"
                accentColor: theme.amber

                Text {
                    Layout.fillWidth: true
                    visible: controller.upcomingHighlights.length === 0
                    text: "Nessun highlight nei prossimi 30 giorni. Consulta il calendario completo sotto."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: controller.upcomingHighlights

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
                                text: modelData.best_time + "  -  " + modelData.setup
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 12

                Repeater {
                    model: controller.events

                    delegate: EventRow {
                        eventData: modelData
                        accentColor: modelData.type === "Luna" ? theme.amber
                                     : modelData.type === "Sciame meteorico" ? theme.teal
                                     : modelData.type === "Eclissi" ? theme.coral
                                     : theme.cyan
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

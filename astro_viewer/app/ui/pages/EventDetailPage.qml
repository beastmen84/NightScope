import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var eventData
    property color accentColor: "#65d6e8"
    property bool hasEvent: eventData && eventData.title !== undefined && eventData.title !== ""
    readonly property string eventWindow: root.hasEvent
                                                   ? (root.eventData.observingWindow || "").toString().trim()
                                                   : ""
    readonly property string eventTimingValue: root.hasEvent
                                                      ? (root.eventData.timingValue || "").toString().trim()
                                                      : ""
    readonly property bool hasDistinctWindow: root.eventWindow.length > 0
                                                      && root.eventWindow !== root.eventTimingValue

    signal backToCalendar()
    signal openObject(string objectId)

    AppTheme {
        id: theme
    }

    function visibilityAccent(state) {
        if (state === "visible" || state === "favorable" || state === "nearby_night")
            return theme.teal
        if (state === "check" || state === "unknown")
            return theme.amber
        return theme.coral
    }

    function eventObjects() {
        if (!root.hasEvent)
            return []
        var provided = root.eventData.targetObjects || []
        if (provided.length > 0)
            return provided
        var targetId = (root.eventData.targetObjectId || "").toString().trim()
        if (targetId.length === 0)
            return []
        var objects = root.controller.solarSystemObjects || []
        for (var index = 0; index < objects.length; index += 1) {
            if (objects[index].id === targetId)
                return [{ "id": targetId, "name": objects[index].name }]
        }
        return []
    }

    ScrollView {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: scroll.availableWidth
            spacing: 18

            Item { Layout.fillWidth: true; Layout.preferredHeight: 14 }

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 14

                DarkButton {
                    text: qsTr("Torna al Calendario")
                    accentColor: root.accentColor
                    onClicked: root.backToCalendar()
                }

                Text {
                    Layout.fillWidth: true
                    text: root.hasEvent ? qsTr("Dettaglio evento") : qsTr("Nessun evento selezionato")
                    color: theme.textSecondary
                    font.pixelSize: 13
                    elide: Text.ElideRight
                }
            }

            GlassCard {
                visible: root.hasEvent
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: root.hasEvent ? root.eventData.title : ""
                subtitle: root.hasEvent ? root.eventData.detailSubtitle : ""
                subtitleWrap: true
                headerBadgeText: root.hasEvent ? root.eventData.type : ""
                headerBadgeColor: root.accentColor
                accentColor: root.accentColor

                Flow {
                    Layout.fillWidth: true
                    Layout.preferredHeight: implicitHeight
                    spacing: 8

                    StatusPill {
                        text: root.hasEvent ? root.eventData.priorityLabel : ""
                        accentColor: root.accentColor
                    }

                    StatusPill {
                        text: root.hasEvent ? root.eventData.visibilityLabel : ""
                        accentColor: root.visibilityAccent(root.hasEvent ? root.eventData.visibilityState : "unknown")
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: root.hasEvent ? root.eventData.whyText : ""
                    color: theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }

            GridLayout {
                visible: root.hasEvent
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: scroll.availableWidth >= 1160 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 244
                    title: qsTr("Quando osservarlo")
                    subtitle: qsTr("Istante, finestra e visibilità locale")
                    accentColor: theme.amber

                    Text {
                        Layout.fillWidth: true
                        text: root.hasEvent ? root.eventData.timingLabel : qsTr("Istante evento")
                        color: theme.textMuted
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.hasEvent ? root.eventData.timingValue : qsTr("n/d")
                        color: theme.textPrimary
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.hasDistinctWindow
                        text: qsTr("Finestra osservativa: %1").arg(root.eventWindow)
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.hasEvent && root.eventWindow.length === 0
                        text: qsTr("Nessuna finestra osservativa locale")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.hasEvent && (root.eventData.separationLabel || "").length > 0
                        text: qsTr("Separazione minima: %1").arg(root.eventData.separationLabel || "")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.hasEvent ? root.eventData.visibilityDetail : ""
                        color: root.visibilityAccent(root.hasEvent ? root.eventData.visibilityState : "unknown")
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 244
                    title: root.hasEvent && root.eventData.typeCode === "solar_conjunction"
                           ? qsTr("Indicazione di sicurezza")
                           : root.hasEvent && root.eventData.typeCode === "satellite_pass"
                             ? qsTr("Osservazione")
                             : qsTr("Con il tuo profilo")
                    subtitle: root.hasEvent && root.eventData.typeCode === "solar_conjunction"
                              ? qsTr("Evento informativo, non osservativo")
                              : root.hasEvent && root.eventData.typeCode === "satellite_pass"
                                ? qsTr("Indicazioni essenziali per il passaggio")
                                : qsTr("Configurazione consigliata per l'evento")
                    accentColor: theme.cyan

                    Text {
                        Layout.fillWidth: true
                        text: root.hasEvent ? root.eventData.setupText : ""
                        color: theme.textPrimary
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.hasEvent ? root.eventData.note : ""
                        color: theme.textMuted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }

                    Flow {
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        spacing: 8

                        Repeater {
                            model: root.eventObjects()

                            delegate: DarkButton {
                                text: qsTr("Apri %1").arg(modelData.name)
                                accentColor: root.accentColor
                                onClicked: root.openObject(modelData.id)
                            }
                        }
                    }
                }

                GlassCard {
                    visible: root.hasEvent
                             && ((root.eventData.eventFacts || []).length > 0
                                 || (root.eventData.dataSource || "").length > 0)
                    Layout.fillWidth: true
                    Layout.minimumHeight: 244
                    title: root.hasEvent && root.eventData.typeCode === "satellite_pass"
                           ? qsTr("Dettagli del passaggio")
                           : qsTr("Dettagli evento")
                    subtitle: root.hasEvent ? (root.eventData.sourceLabel || "") : ""
                    accentColor: theme.violet

                    Repeater {
                        model: root.hasEvent ? (root.eventData.eventFacts || []) : []

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                Layout.fillWidth: true
                                text: modelData.label
                                color: theme.textSecondary
                                font.pixelSize: 13
                                elide: Text.ElideRight
                            }

                            Text {
                                text: modelData.value
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.hasEvent && (root.eventData.dataSource || "").length > 0
                        text: qsTr("Fonte: %1").arg(root.eventData.dataSource || "")
                        color: theme.textMuted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.hasEvent && (root.eventData.dataFreshness || "").length > 0
                        text: root.eventData.dataFreshness || ""
                        color: theme.textMuted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }
                }
            }

            GlassCard {
                visible: root.hasEvent
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Consigli osservativi")
                subtitle: qsTr("Azioni pratiche per preparare l'evento")
                accentColor: theme.teal

                Repeater {
                    model: root.hasEvent ? root.eventData.tips : []

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Rectangle {
                            Layout.preferredWidth: 7
                            Layout.preferredHeight: 7
                            radius: 4
                            color: root.accentColor
                            Layout.alignment: Qt.AlignTop
                            Layout.topMargin: 6
                        }

                        Text {
                            Layout.fillWidth: true
                            text: modelData
                            color: theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }
                    }
                }
            }

            GlassCard {
                visible: !root.hasEvent
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Nessun evento selezionato")
                subtitle: qsTr("Torna al calendario e scegli una voce dalla timeline")
                accentColor: theme.violet

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Seleziona una scheda evento per aprire il dettaglio.")
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

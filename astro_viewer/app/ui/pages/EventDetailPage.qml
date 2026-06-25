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

    signal backToCalendar()
    signal openObject(string objectId)

    AppTheme {
        id: theme
    }

    function cleanText(value) {
        return (value || "").toString().trim()
    }

    function lowerText(value) {
        return cleanText(value).toLowerCase()
    }

    function eventType() {
        return root.hasEvent ? root.cleanText(root.eventData.type) : ""
    }

    function eventTitle() {
        return root.hasEvent ? root.cleanText(root.eventData.title) : ""
    }

    function eventWindowText() {
        if (!root.hasEvent)
            return ""
        var dateLabel = root.cleanText(root.eventData.date_label)
        var timeLabel = root.cleanText(root.eventData.best_time)
        if (dateLabel.length > 0 && timeLabel.length > 0)
            return dateLabel + " - " + timeLabel
        return dateLabel.length > 0 ? dateLabel : timeLabel
    }

    function hasConfiguredEquipment() {
        var assigned = controller.profileAssignedEquipment || []
        for (var index = 0; index < assigned.length; index += 1) {
            if (assigned[index].id !== "preset:naked-eye")
                return true
        }
        return false
    }

    function profileSetupText() {
        var setup = root.hasEvent ? root.cleanText(root.eventData.setup) : ""
        var type = root.eventType()
        if (setup === "Occhio nudo")
            return "Osservabile a occhio nudo"
        if (!root.hasConfiguredEquipment() && (type === "Opposizione" || type === "Congiunzione" || setup === "Telescopio consigliato"))
            return "Configura un profilo per consigli più precisi."
        if (setup === "Nota osservativa")
            return "Configura un profilo per consigli più precisi."
        if (setup.length > 0)
            return setup
        if (type === "Sciame meteorico" || type === "Eclissi")
            return "Osservabile a occhio nudo"
        return "Configura un profilo per consigli più precisi."
    }

    function whyText() {
        var type = root.eventType()
        var title = root.lowerText(root.eventTitle())
        if (type === "Opposizione")
            return "L'opposizione è il periodo migliore dell'anno per osservare il pianeta: è più vicino alla Terra, più luminoso e visibile per gran parte della notte."
        if (type === "Luna" && title.indexOf("nuova") >= 0)
            return "La Luna nuova offre il cielo più scuro del mese ed è il momento migliore per oggetti deboli del cielo profondo."
        if (type === "Luna")
            return "Le fasi lunari aiutano a scegliere tra osservazione della Luna, pianeti e cielo profondo in base alla luminosità del cielo."
        if (type === "Sciame meteorico")
            return "Gli sciami meteorici si osservano meglio a occhio nudo, lontano da luci dirette, lasciando adattare la vista al buio."
        if (type === "Eclissi")
            return "Un'eclissi lunare è osservabile anche a occhio nudo e diventa più interessante con binocolo o telescopio a basso ingrandimento."
        if (type === "Congiunzione")
            return "Una congiunzione avvicina prospetticamente due oggetti nel cielo e offre una finestra interessante per osservazioni grandangolari o fotografie."
        return root.hasEvent ? root.cleanText(root.eventData.note) : "Seleziona un evento dal calendario."
    }

    function observingTips() {
        var type = root.eventType()
        var title = root.lowerText(root.eventTitle())
        if (type === "Opposizione")
            return [
                "Usa alti ingrandimenti solo se il seeing lo permette.",
                "Osserva quando il pianeta è più alto sull'orizzonte.",
                "Lascia acclimatare il telescopio prima dei dettagli fini."
            ]
        if (type === "Sciame meteorico")
            return [
                "Non serve il telescopio.",
                "Guarda verso una zona di cielo buia, non direttamente verso luci o schermi.",
                "Se possibile osserva dopo la mezzanotte."
            ]
        if (type === "Luna" && title.indexOf("nuova") >= 0)
            return [
                "Dai priorità a galassie, nebulose e ammassi deboli.",
                "Evita luci dirette e lascia adattare la vista al buio.",
                "Sfrutta finestre meteo con poca umidità e nubi basse."
            ]
        if (type === "Eclissi")
            return [
                "È osservabile anche a occhio nudo.",
                "Usa binocolo o basso ingrandimento per seguire il disco lunare completo.",
                "Controlla in anticipo la finestra temporale dell'evento."
            ]
        if (type === "Congiunzione")
            return [
                "Preferisci bassi ingrandimenti o binocolo.",
                "Cerca un orizzonte libero nella direzione indicata dall'evento.",
                "Inizia qualche minuto prima della finestra migliore."
            ]
        return [
            "Controlla meteo, altezza sull'orizzonte e trasparenza prima di uscire.",
            "Prepara il setup in anticipo per non perdere la finestra utile."
        ]
    }

    function eventObjectId() {
        if (!root.hasEvent || root.eventType() !== "Opposizione")
            return ""
        var targetId = root.cleanText(root.eventData.targetObjectId)
        if (targetId.length === 0)
            return ""
        var objects = controller.solarSystemObjects || []
        for (var index = 0; index < objects.length; index += 1) {
            if (objects[index].id === targetId)
                return targetId
        }
        return ""
    }

    function canOpenObjectDetail() {
        return root.eventObjectId().length > 0
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
                    text: "Torna al Calendario"
                    accentColor: root.accentColor
                    onClicked: root.backToCalendar()
                }

                Text {
                    Layout.fillWidth: true
                    text: root.hasEvent ? "Dettaglio evento" : "Nessun evento selezionato"
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
                title: root.eventTitle()
                subtitle: root.eventWindowText()
                headerBadgeText: root.eventType()
                headerBadgeColor: root.accentColor
                accentColor: root.accentColor

                Text {
                    Layout.fillWidth: true
                    text: root.whyText()
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
                    Layout.minimumHeight: 190
                    title: "Con il tuo profilo"
                    subtitle: "Setup consigliato per questo evento"
                    accentColor: theme.cyan

                    Text {
                        Layout.fillWidth: true
                        text: root.profileSetupText()
                        color: theme.textPrimary
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.cleanText(root.eventData.note)
                        color: theme.textMuted
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }

                    DarkButton {
                        visible: root.canOpenObjectDetail()
                        Layout.preferredWidth: 180
                        text: "Apri dettaglio oggetto"
                        accentColor: root.accentColor
                        onClicked: root.openObject(root.eventObjectId())
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 190
                    title: "Consigli osservativi"
                    subtitle: "Azioni pratiche per la sessione"
                    accentColor: theme.teal

                    Repeater {
                        model: root.observingTips()

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
            }

            GlassCard {
                visible: !root.hasEvent
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Nessun evento selezionato"
                subtitle: "Torna al calendario e scegli una voce dalla timeline"
                accentColor: theme.violet

                Text {
                    Layout.fillWidth: true
                    text: "Seleziona una scheda evento per aprire il dettaglio."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item {
                Layout.fillWidth: true
                Layout.preferredHeight: 28
            }
        }
    }
}

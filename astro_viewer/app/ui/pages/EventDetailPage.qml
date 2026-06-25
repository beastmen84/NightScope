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

    function appendGuidance(setup, guidance) {
        var base = root.cleanText(setup)
        var detail = root.cleanText(guidance)
        if (base.length === 0)
            return detail
        if (detail.length === 0)
            return base
        var lastChar = base.charAt(base.length - 1)
        if (lastChar !== "." && lastChar !== "!" && lastChar !== "?")
            base += "."
        return base + " " + detail
    }

    function isGenericSetup(setup) {
        return setup === "" || setup === "Nota osservativa" || setup === "Qualsiasi setup"
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
        var title = root.lowerText(root.eventTitle())
        if (type === "Sciame meteorico")
            return "Il telescopio non serve: osserva a occhio nudo. Un binocolo può essere utile solo per esplorare il cielo tra una meteora e l'altra."
        if (type === "Eclissi" && title.indexOf("solare") >= 0)
            return "Osserva il Sole solo con filtri solari certificati davanti all'obiettivo. Non usare oculari o cercatori non filtrati."
        if (type === "Eclissi")
            return "Osservabile a occhio nudo. Con binocolo o telescopio usa basso ingrandimento: l'intero disco lunare deve restare nel campo."
        if (type === "Luna" && title.indexOf("nuova") >= 0) {
            if (!root.isGenericSetup(setup))
                return setup
            return "Configura un profilo per consigli più precisi; resta comunque la notte migliore del mese per galassie, nebulose e ammassi deboli."
        }
        if (type === "Luna") {
            var lunarSetup = root.isGenericSetup(setup) ? "Osservabile a occhio nudo o con binocolo." : setup
            if (title.indexOf("primo quarto") >= 0 || title.indexOf("ultimo quarto") >= 0)
                return root.appendGuidance(lunarSetup, "Il terminatore evidenzia crateri e rilievi; l'ingrandimento consigliato mantiene dettagli e immagine luminosa.")
            if (title.indexOf("piena") >= 0)
                return root.appendGuidance(lunarSetup, "Usa filtro lunare o ingrandimenti moderati: il disco è luminoso e il cielo profondo debole rende poco.")
            return root.appendGuidance(lunarSetup, "Mantieni il disco comodo nel campo e aumenta l'ingrandimento solo quando l'immagine resta stabile.")
        }
        if (type === "Opposizione" && setup.length > 0)
            return root.appendGuidance(setup, "Aumenta l'ingrandimento solo se il seeing mantiene il pianeta nitido.")
        if (type === "Congiunzione" && setup.length > 0)
            return root.appendGuidance(setup, "Preferisci campo largo: l'obiettivo è vedere gli oggetti insieme, non spingerli al massimo ingrandimento.")
        if (setup === "Occhio nudo")
            return "Osservabile a occhio nudo"
        if (!root.hasConfiguredEquipment() && (type === "Opposizione" || type === "Congiunzione" || setup === "Telescopio consigliato"))
            return "Configura un profilo per consigli più precisi."
        if (setup === "Nota osservativa")
            return "Configura un profilo per consigli più precisi."
        if (setup.length > 0)
            return setup
        return "Configura un profilo per consigli più precisi."
    }

    function whyText() {
        var type = root.eventType()
        var title = root.lowerText(root.eventTitle())
        if (type === "Opposizione")
            return "È la notte in cui il pianeta merita davvero spazio nel piano osservativo: resta visibile a lungo, diventa più luminoso e consente di aspettare i momenti di seeing stabile."
        if (type === "Luna" && title.indexOf("nuova") >= 0)
            return "È la finestra con meno luce lunare: vale la pena riservarla a galassie, nebulose e ammassi deboli che nelle altre notti perdono contrasto."
        if (type === "Luna" && (title.indexOf("primo quarto") >= 0 || title.indexOf("ultimo quarto") >= 0))
            return "Il terminatore attraversa zone ricche di rilievi: crateri, ombre e catene montuose mostrano più dettaglio rispetto alla Luna piena."
        if (type === "Luna" && title.indexOf("piena") >= 0)
            return "La Luna piena è facile e luminosa, ma lava il cielo profondo debole. Usala per osservazione lunare, pianeti brillanti o sessioni rapide."
        if (type === "Luna")
            return "La fase lunare decide quanto cielo buio avrai e quali dettagli lunari conviene cercare durante la sessione."
        if (type === "Sciame meteorico")
            return "Conta più il cielo buio del telescopio: serve campo visivo ampio, pazienza e vista adattata al buio per cogliere meteore sparse."
        if (type === "Eclissi" && title.indexOf("solare") >= 0)
            return "È un evento da pianificare con attenzione e protezione solare certificata. Senza filtri corretti non va osservato direttamente."
        if (type === "Eclissi")
            return "È un evento comodo da seguire anche a occhio nudo; binocolo o basso ingrandimento aiutano a vedere colore, ombra e avanzamento sul disco lunare."
        if (type === "Congiunzione")
            return "È interessante quando puoi inquadrare più oggetti insieme. Rende meglio con binocolo, bassi ingrandimenti o foto a campo largo."
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
                "Scegli una zona di cielo ampia e buia, lontana da luci dirette.",
                "Sdraiati o usa una sedia reclinabile: serve osservare a lungo.",
                "Se possibile osserva dopo la mezzanotte."
            ]
        if (type === "Luna" && title.indexOf("nuova") >= 0)
            return [
                "Dai priorità a galassie, nebulose e ammassi deboli.",
                "Evita luci dirette e lascia adattare la vista al buio.",
                "Sfrutta finestre meteo con poca umidità e nubi basse."
            ]
        if (type === "Luna" && (title.indexOf("primo quarto") >= 0 || title.indexOf("ultimo quarto") >= 0))
            return [
                "Osserva lungo il terminatore.",
                "Aumenta l'ingrandimento a piccoli passi.",
                "Usa un filtro lunare se l'immagine è troppo luminosa."
            ]
        if (type === "Luna" && title.indexOf("piena") >= 0)
            return [
                "Usa filtro lunare o riduci l'ingrandimento.",
                "Non puntare oggetti deboli del cielo profondo.",
                "Preferisci pianeti brillanti, stelle doppie e dettagli lunari evidenti."
            ]
        if (type === "Eclissi" && title.indexOf("solare") >= 0)
            return [
                "Usa solo filtri solari certificati davanti all'obiettivo.",
                "Non guardare mai il Sole attraverso cercatore o oculare non filtrato.",
                "Prepara il setup prima dell'inizio dell'evento."
            ]
        if (type === "Eclissi")
            return [
                "È osservabile anche a occhio nudo.",
                "Usa binocolo o basso ingrandimento.",
                "Mantieni il disco lunare completo nel campo.",
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
        if (!root.hasEvent)
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

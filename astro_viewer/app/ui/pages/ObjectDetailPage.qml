import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var selectedObjectData: controller ? (controller.selectedObject || ({})) : ({})
    property bool selectedIsCatalogueDetail: selectedObjectData.catalogueObject === true
    property var observingObjectData: controller ? (controller.observingObjectDetail || ({})) : ({})
    property var objectData: selectedIsCatalogueDetail || !observingObjectData.name
                             ? selectedObjectData : observingObjectData
    readonly property var geometryData: objectData.geometry || ({})
    readonly property var sessionData: objectData.session || ({})
    readonly property var evaluationData: objectData.evaluation || ({})
    readonly property var equipmentData: objectData.equipment || ({})
    property bool hasObject: objectData && objectData.name !== undefined && objectData.name !== ""
    property bool isCatalogueDetail: root.hasObject && selectedIsCatalogueDetail
    property int detailMetricHeight: 88
    property string backLabel: "Torna alla Home"
    signal backToHome()

    function safeValue(value) {
        if (value === undefined || value === null || value === "")
            return "n/d"
        return String(value)
    }

    function geometryAccent(state) {
        if (state === "observable_now")
            return theme.green
        if (state === "above_horizon")
            return theme.cyan
        if (state === "later")
            return theme.amber
        if (state === "limited")
            return theme.coral
        return theme.textMuted
    }

    function sessionAccent(state) {
        if (state === "recommended")
            return theme.teal
        if (state === "monitor")
            return theme.amber
        if (state === "discouraged")
            return theme.coral
        if (state === "pending")
            return theme.cyan
        return theme.textMuted
    }

    function hasCatalogueDistance() {
        return root.hasObject && String(objectData.distance || "").indexOf("Catalogo ") === 0
    }

    function originMetricLabel() {
        return root.hasCatalogueDistance() ? "Catalogo" : "Distanza"
    }

    function originMetricValue() {
        if (!root.hasObject)
            return "n/d"
        var distance = String(objectData.distance || "")
        if (distance.indexOf("Catalogo ") === 0)
            return distance.replace("Catalogo ", "")
        return root.safeValue(objectData.distance)
    }

    function maxAngularSizeText() {
        if (!root.hasObject)
            return "n/d"
        if (objectData.maxAngularSizeLabel !== undefined && objectData.maxAngularSizeLabel !== "")
            return objectData.maxAngularSizeLabel
        if (objectData.maxAngularSizeDeg === undefined || objectData.maxAngularSizeDeg === null)
            return "n/d"
        return String(objectData.maxAngularSizeDeg) + " deg"
    }

    function includeCatalogueMetric(value) {
        var text = root.safeValue(value)
        return text !== "n/d" && text !== "undefined" && text !== "null"
    }

    function catalogueBadgeText() {
        if (!root.hasObject)
            return ""
        var catalogue = root.safeValue(objectData.catalogue)
        return catalogue === "n/d" ? "Catalogo" : "Catalogo " + catalogue
    }

    function catalogueSummaryText() {
        if (!root.hasObject)
            return ""
        var parts = []
        if (root.includeCatalogueMetric(objectData.catalogueId))
            parts.push(root.safeValue(objectData.catalogueId))
        if (root.includeCatalogueMetric(objectData.catalogueTypeLabel || objectData.type))
            parts.push(root.safeValue(objectData.catalogueTypeLabel || objectData.type))
        if (root.includeCatalogueMetric(objectData.constellation))
            parts.push("Costellazione " + root.safeValue(objectData.constellation))
        return parts.join("  -  ")
    }

    function catalogueMetadataItems() {
        var source = [
            { "label": "Catalogo", "value": objectData.catalogue, "accent": theme.violet },
            { "label": "ID catalogo", "value": objectData.catalogueId, "accent": theme.cyan },
            { "label": "Tipo", "value": objectData.catalogueTypeLabel || objectData.type, "accent": theme.teal },
            { "label": "Costellazione", "value": objectData.constellation, "accent": theme.amber },
            { "label": "Magnitudine", "value": objectData.magnitude, "accent": theme.cyan },
            { "label": "Dimensione", "value": objectData.apparentSize, "accent": theme.green },
            { "label": "Dim. max", "value": root.maxAngularSizeText(), "accent": theme.teal },
            { "label": "Osservazione", "value": objectData.catalogueObservationTypeLabel || objectData.recommendedObservationType, "accent": theme.amber },
            { "label": "A.R.", "value": objectData.rightAscension, "accent": theme.violet },
            { "label": "Dec", "value": objectData.declination, "accent": theme.coral },
            { "label": "Alt. attuale", "value": objectData.currentAltitude, "accent": theme.cyan },
            { "label": "Azimut", "value": objectData.currentAzimuth, "accent": theme.coral },
            { "label": "Sorge", "value": objectData.riseTime, "accent": theme.teal },
            { "label": "Transita", "value": objectData.culminationTime, "accent": theme.green },
            { "label": "Tramonta", "value": objectData.setTime, "accent": theme.amber },
            { "label": "Utile (≥15°)", "value": objectData.catalogueUsefullyObservableLabel, "accent": objectData.catalogueUsefullyObservable === true ? theme.green : theme.textMuted },
            { "label": "Visibile nel mese corrente", "value": objectData.catalogueVisibleCurrentMonthLabel, "accent": objectData.catalogueVisibleCurrentMonth === true ? theme.green : theme.textMuted }
        ]
        var result = []
        for (var i = 0; i < source.length; i++) {
            if (root.includeCatalogueMetric(source[i].value))
                result.push(source[i])
        }
        return result
    }

    function distinctSetupOptions(options) {
        var result = []
        var seen = {}
        options = options || []
        for (var i = 0; i < options.length; i++) {
            var key = options[i].displayLabel || options[i].detailLabel || options[i].label || ""
            if (key.length === 0 || seen[key])
                continue
            seen[key] = true
            result.push(options[i])
        }
        return result
    }

    function recommendedSetupOption() {
        var options = objectData.setupOptions || []
        for (var i = 0; i < options.length; i++) {
            if (options[i].role === "Consigliato")
                return options[i]
        }
        return options.length > 0 ? options[0] : null
    }

    function isBinocularRecommendation() {
        var option = root.recommendedSetupOption()
        return objectData.recommendedSetupType === "binocular"
            || (option && option.equipmentType === "Binocular")
    }

    function setupOptionMetrics(option) {
        if (!option)
            return ""
        if (option.equipmentType === "Binocular") {
            var parts = []
            if (option.magnification && option.magnification.length > 0)
                parts.push(option.magnification)
            if (option.exitPupil && option.exitPupil.length > 0 && option.exitPupil !== "n/d")
                parts.push("Pupilla " + option.exitPupil)
            return parts.join("  -  ")
        }
        return option.magnification + "  -  " + option.trueField + "  -  " + option.exitPupil
    }

    function setupDetailText() {
        if (root.isBinocularRecommendation()) {
            var option = root.recommendedSetupOption()
            var parts = ["Binocolo: " + objectData.recommended_setup]
            if (option && option.magnification && option.magnification.length > 0)
                parts.push("Ingrandimento: " + option.magnification)
            if (option && option.exitPupil && option.exitPupil.length > 0 && option.exitPupil !== "n/d")
                parts.push("Pupilla d'uscita: " + option.exitPupil)
            parts.push("Difficoltà: " + objectData.difficulty)
            return parts.join("  -  ")
        }
        return "Oculare: " + objectData.bestEyepiece + "  -  Barlow: " + objectData.barlow + "  -  Difficoltà: " + objectData.difficulty
    }

    function drawMoonPhase(ctx, width, height, phaseAngle) {
        var angle = ((phaseAngle % 360) + 360) % 360
        var radius = Math.min(width, height) / 2 - 3
        var centerX = width / 2
        var centerY = height / 2
        ctx.clearRect(0, 0, width, height)

        var glow = ctx.createRadialGradient(centerX, centerY, radius * 0.35, centerX, centerY, radius * 1.45)
        glow.addColorStop(0, "rgba(202, 224, 244, 0.28)")
        glow.addColorStop(1, "rgba(202, 224, 244, 0)")
        ctx.fillStyle = glow
        ctx.beginPath()
        ctx.arc(centerX, centerY, radius * 1.45, 0, Math.PI * 2)
        ctx.fill()

        var darkDisc = ctx.createRadialGradient(centerX - radius * 0.25, centerY - radius * 0.25, radius * 0.15, centerX, centerY, radius)
        darkDisc.addColorStop(0, "#1d2430")
        darkDisc.addColorStop(0.62, "#0b0f16")
        darkDisc.addColorStop(1, "#05070b")
        ctx.beginPath()
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
        ctx.fillStyle = darkDisc
        ctx.fill()

        ctx.save()
        ctx.beginPath()
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
        ctx.clip()

        if (angle > 2 && angle < 358) {
            var lightDisc = ctx.createRadialGradient(centerX - radius * 0.35, centerY - radius * 0.45, radius * 0.1, centerX, centerY, radius)
            lightDisc.addColorStop(0, "#fff7db")
            lightDisc.addColorStop(0.48, "#d7dce3")
            lightDisc.addColorStop(1, "#9ba6b4")
            ctx.fillStyle = lightDisc
            ctx.fillRect(centerX - radius, centerY - radius, radius * 2, radius * 2)

            ctx.globalAlpha = 0.18
            ctx.fillStyle = "#75808d"
            var craters = [
                [-0.30, -0.22, 0.10],
                [0.22, -0.18, 0.075],
                [-0.10, 0.18, 0.065],
                [0.36, 0.24, 0.045],
                [-0.42, 0.30, 0.04]
            ]
            for (var i = 0; i < craters.length; i++) {
                ctx.beginPath()
                ctx.arc(centerX + radius * craters[i][0], centerY + radius * craters[i][1], radius * craters[i][2], 0, Math.PI * 2)
                ctx.fill()
            }
            ctx.globalAlpha = 1

            var shadow = ctx.createRadialGradient(centerX + radius * 0.2, centerY - radius * 0.2, radius * 0.08, centerX, centerY, radius)
            shadow.addColorStop(0, "#151b24")
            shadow.addColorStop(0.72, "#070a0f")
            shadow.addColorStop(1, "#020305")
            var shadowOffset
            if (angle <= 180)
                shadowOffset = -2 * radius * (angle / 180)
            else
                shadowOffset = 2 * radius * (1 - ((angle - 180) / 180))
            ctx.fillStyle = shadow
            ctx.beginPath()
            ctx.arc(centerX + shadowOffset, centerY, radius, 0, Math.PI * 2)
            ctx.fill()
        }

        ctx.restore()
        ctx.beginPath()
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2)
        ctx.strokeStyle = "#46505f"
        ctx.lineWidth = 1
        ctx.stroke()
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
                    text: root.backLabel
                    accentColor: theme.cyan
                    onClicked: root.backToHome()
                }

                Text {
                    Layout.fillWidth: true
                    text: root.hasObject ? (root.isCatalogueDetail ? "Scheda catalogo" : "Dettaglio osservativo") : "Nessun oggetto selezionato"
                    color: theme.textSecondary
                    font.pixelSize: 13
                    elide: Text.ElideRight
                }
            }

            GridLayout {
                id: observingDetailGrid
                visible: root.hasObject && !root.isCatalogueDetail
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 18
                rowSpacing: 18

                ColumnLayout {
                    Layout.fillWidth: observingDetailGrid.columns === 1
                    Layout.preferredWidth: observingDetailGrid.columns === 2 ? 420 : observingDetailGrid.width
                    Layout.maximumWidth: observingDetailGrid.columns === 2 ? 420 : 16777215
                    Layout.fillHeight: true
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
                            anchors.bottomMargin: observingImageCredit.visible ? 56 : 30
                            source: root.hasObject ? root.controller.assetBaseUrl + "/" + root.objectData.image : ""
                            fillMode: Image.PreserveAspectFit
                            sourceSize.width: 520
                            sourceSize.height: 520
                        }

                        Text {
                            id: observingImageCredit
                            visible: (root.objectData.imageSourceUrl || "").length > 0
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            anchors.margins: 14
                            text: root.objectData.imageAttribution || "Fonte immagine"
                            color: theme.cyan
                            font.pixelSize: 10
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                            horizontalAlignment: Text.AlignHCenter

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: Qt.openUrlExternally(root.objectData.imageSourceUrl)
                                ToolTip.visible: containsMouse
                                ToolTip.delay: 500
                                ToolTip.text: (root.objectData.imageAttribution || "") + "\n"
                                              + (root.objectData.imageLicense || "")
                            }
                        }
                    }

                    GlassCard {
                        visible: !root.isCatalogueDetail
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        Layout.minimumHeight: 118
                        title: "Finestra osservativa"
                        subtitle: root.geometryData.durationText || "Durata utile non disponibile"
                        accentColor: theme.teal

                        Text {
                            Layout.fillWidth: true
                            text: root.geometryData.windowLabel || "n/d"
                            color: theme.textPrimary
                            font.pixelSize: 30
                            font.weight: Font.DemiBold
                            wrapMode: Text.WordWrap
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        StatusPill {
                            text: root.geometryData.status || objectData.observingStatus || "Da valutare"
                            accentColor: root.geometryAccent(root.geometryData.state || "unavailable")
                        }

                        StatusPill {
                            visible: (root.sessionData.badge || "").length > 0
                            text: root.sessionData.badge || ""
                            accentColor: root.sessionAccent(root.sessionData.state || "unavailable")
                        }
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
                        text: root.geometryData.detail || objectData.observingStatusDetail || ""
                        color: root.isCatalogueDetail ? theme.textSecondary : theme.amber
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
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: root.originMetricLabel(); value: root.originMetricValue(); accentColor: theme.violet }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Altezza massima"; value: objectData.max_altitude; accentColor: theme.teal }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Direzione"; value: objectData.direction; accentColor: theme.amber }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Momento migliore"; value: root.geometryData.bestTimeLabel || "n/d"; accentColor: theme.green }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Azimut"; value: objectData.azimuth; accentColor: theme.coral }
                        MetricTile { Layout.preferredHeight: root.detailMetricHeight; label: "Altezza attuale"; value: root.geometryData.currentAltitude || objectData.currentAltitude; accentColor: theme.cyan }
                        MetricTile { visible: root.geometryData.showHorizonEvents === true; Layout.preferredHeight: root.detailMetricHeight; label: "Sorge"; value: root.geometryData.riseTime || "n/d"; accentColor: theme.teal }
                        MetricTile { visible: root.geometryData.showHorizonEvents === true; Layout.preferredHeight: root.detailMetricHeight; label: "Tramonta"; value: root.geometryData.setTime || "n/d"; accentColor: theme.amber }
                        MetricTile { visible: root.geometryData.isDeepSky === true; Layout.preferredHeight: root.detailMetricHeight; label: "Inizio utile"; value: root.geometryData.windowStart || "n/d"; accentColor: theme.teal }
                        MetricTile { visible: root.geometryData.isDeepSky === true; Layout.preferredHeight: root.detailMetricHeight; label: "Fine utile"; value: root.geometryData.windowEnd || "n/d"; accentColor: theme.amber }
                    }
                }
            }

            RowLayout {
                visible: root.isCatalogueDetail
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 18

                Rectangle {
                    Layout.preferredWidth: Math.min(420, Math.max(260, root.width * 0.34))
                    Layout.preferredHeight: 300
                    Layout.alignment: Qt.AlignTop
                    radius: 8
                    color: "#111319"
                    border.color: "#303641"
                    border.width: 1

                    Image {
                        anchors.fill: parent
                        anchors.margins: 30
                        anchors.bottomMargin: catalogueImageCredit.visible ? 56 : 30
                        source: root.hasObject ? root.controller.assetBaseUrl + "/" + root.objectData.image : ""
                        fillMode: Image.PreserveAspectFit
                        sourceSize.width: 520
                        sourceSize.height: 520
                    }

                    Text {
                        id: catalogueImageCredit
                        visible: (root.objectData.imageSourceUrl || "").length > 0
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.bottom: parent.bottom
                        anchors.margins: 14
                        text: root.objectData.imageAttribution || "Fonte immagine"
                        color: theme.cyan
                        font.pixelSize: 10
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                        elide: Text.ElideRight
                        horizontalAlignment: Text.AlignHCenter

                        MouseArea {
                            anchors.fill: parent
                            hoverEnabled: true
                            cursorShape: Qt.PointingHandCursor
                            onClicked: Qt.openUrlExternally(root.objectData.imageSourceUrl)
                            ToolTip.visible: containsMouse
                            ToolTip.delay: 500
                            ToolTip.text: (root.objectData.imageAttribution || "") + "\n"
                                          + (root.objectData.imageLicense || "")
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

                    StatusPill {
                        text: root.catalogueBadgeText()
                        accentColor: theme.cyan
                    }

                    Text {
                        Layout.fillWidth: true
                        text: objectData.name
                        color: theme.textPrimary
                        font.pixelSize: 40
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.catalogueSummaryText()
                        color: theme.textSecondary
                        font.pixelSize: 18
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                    }

                    Text {
                        Layout.fillWidth: true
                        text: objectData.catalogueIntroText || objectData.descriptionText || objectData.notes
                        color: theme.textSecondary
                        font.pixelSize: 15
                        wrapMode: Text.WordWrap
                        maximumLineCount: 7
                        elide: Text.ElideRight
                    }
                }
            }

            GlassCard {
                visible: root.isCatalogueDetail
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Dati di catalogo"
                subtitle: root.catalogueSummaryText()
                accentColor: theme.cyan

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1160 ? 4 : root.width > 760 ? 2 : 1
                    columnSpacing: 12
                    rowSpacing: 12

                    Repeater {
                        model: root.catalogueMetadataItems()

                        delegate: MetricTile {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 82
                            label: modelData.label
                            value: modelData.value
                            accentColor: modelData.accent
                        }
                    }
                }
            }

            GlassCard {
                visible: root.hasObject
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Descrizione"
                subtitle: objectData.bestSeen && objectData.bestSeen.length > 0
                          ? "Periodo migliore: " + objectData.bestSeen
                          : (root.isCatalogueDetail ? (objectData.catalogueTypeLabel || objectData.type) : objectData.type)
                accentColor: theme.cyan

                Text {
                    Layout.fillWidth: true
                    text: objectData.descriptionText
                    color: theme.textPrimary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                visible: root.hasObject && (root.objectData.curiosityText || "").length > 0
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Curiosità"
                subtitle: "Storia, scienza e contesto"
                accentColor: theme.violet

                Text {
                    Layout.fillWidth: true
                    text: root.objectData.curiosityText || ""
                    color: theme.textPrimary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }

                Text {
                    visible: (root.objectData.curiositySourceUrl || "").length > 0
                    Layout.fillWidth: true
                    text: "Fonte: <a href=\"" + (root.objectData.curiositySourceUrl || "") + "\">"
                          + (root.objectData.curiositySourceLabel || "Apri la fonte") + "</a>"
                    textFormat: Text.RichText
                    color: theme.textSecondary
                    linkColor: theme.cyan
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                    onLinkActivated: function(link) { Qt.openUrlExternally(link) }
                }
            }

            GlassCard {
                visible: root.hasObject && !root.isCatalogueDetail
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Configurazione consigliata"
                subtitle: (root.equipmentData.telescopeName || "").length > 0
                          ? "Setup scelto per " + root.equipmentData.telescopeName
                          : "Suggerimento operativo"
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
                    visible: objectData.setupReason && objectData.setupReason.length > 0
                    Layout.fillWidth: true
                    text: "Perché questa configurazione: " + objectData.setupReason
                    color: theme.textSecondary
                    font.pixelSize: 13
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
                            text: modelData.displayLabel || modelData.detailLabel || modelData.label
                            color: theme.textPrimary
                            font.pixelSize: 13
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Text {
                            text: root.setupOptionMetrics(modelData)
                            color: theme.textSecondary
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: root.setupDetailText()
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                visible: root.hasObject && !root.isCatalogueDetail && objectData.id === "moon"
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Ciclo lunare"
                subtitle: (objectData.moonPhase || "Fase lunare") + "  -  " + (objectData.moonIllumination || "n/d") + "  -  " + (objectData.moonCycleDay || "")
                accentColor: theme.cyan

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Repeater {
                        model: [
                            { "label": "Nuova", "angle": 0 },
                            { "label": "Crescente", "angle": 45 },
                            { "label": "Primo quarto", "angle": 90 },
                            { "label": "Gibbosa", "angle": 135 },
                            { "label": "Piena", "angle": 180 },
                            { "label": "Calante", "angle": 225 },
                            { "label": "Ultimo quarto", "angle": 270 },
                            { "label": "Falce calante", "angle": 315 }
                        ]

                        delegate: ColumnLayout {
                            Layout.fillWidth: true
                            Layout.preferredWidth: 1
                            spacing: 6

                            Canvas {
                                Layout.alignment: Qt.AlignHCenter
                                Layout.preferredWidth: 44
                                Layout.preferredHeight: 44
                                property real phaseAngle: modelData.angle
                                onPaint: root.drawMoonPhase(getContext("2d"), width, height, phaseAngle)
                                Component.onCompleted: requestPaint()
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.label
                                color: theme.textSecondary
                                font.pixelSize: 11
                                horizontalAlignment: Text.AlignHCenter
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                Item {
                    id: moonCycleIndicator
                    Layout.fillWidth: true
                    Layout.preferredHeight: 14
                    property real rawCycleFraction: {
                        var dayText = String(objectData.moonCycleDay || "")
                        var dayMatch = dayText.match(/[0-9]+([\\.,][0-9]+)?/)
                        if (dayMatch && dayMatch.length > 0) {
                            var dayValue = Number(dayMatch[0].replace(",", "."))
                            if (!isNaN(dayValue))
                                return dayValue / 29.53
                        }
                        var value = Number(objectData.moonCycleFraction)
                        if (!isNaN(value))
                            return value
                        var angle = Number(objectData.moonPhaseAngle)
                        return isNaN(angle) ? 0 : angle / 360
                    }
                    property real cycleFraction: Math.max(0, Math.min(0.875, rawCycleFraction))
                    property real indicatorCenter: width / 16 + cycleFraction * width

                    Rectangle {
                        height: 1
                        anchors.left: parent.left
                        anchors.right: parent.right
                        anchors.leftMargin: parent.width / 16
                        anchors.rightMargin: parent.width / 16
                        anchors.top: parent.top
                        anchors.topMargin: 2
                        color: "#303641"
                    }

                    Canvas {
                        width: 16
                        height: 12
                        x: Math.max(0, Math.min(moonCycleIndicator.width - width, moonCycleIndicator.indicatorCenter - width / 2))
                        y: 2
                        property real cycleFraction: moonCycleIndicator.cycleFraction
                        onPaint: {
                            var ctx = getContext("2d")
                            ctx.clearRect(0, 0, width, height)
                            ctx.beginPath()
                            ctx.moveTo(width / 2, 0)
                            ctx.lineTo(0, height)
                            ctx.lineTo(width, height)
                            ctx.closePath()
                            ctx.fillStyle = theme.cyan
                            ctx.fill()
                        }
                        onCycleFractionChanged: requestPaint()
                        onXChanged: requestPaint()
                        Component.onCompleted: requestPaint()
                    }
                }
            }

            GlassCard {
                visible: !root.hasObject
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Seleziona un oggetto"
                subtitle: "Il dettaglio si apre dalle pagine dell'app"
                accentColor: theme.cyan

                Text {
                    Layout.fillWidth: true
                    text: "Scegli un oggetto dalla Home, dal calendario o dal catalogo."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                visible: root.hasObject && !root.isCatalogueDetail
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: root.evaluationData.title || "Valutazione osservativa"
                subtitle: root.evaluationData.subtitle || "Geometria e condizioni locali"
                accentColor: root.sessionAccent(root.sessionData.state || "unavailable")

                Text {
                    visible: (root.evaluationData.warning || "").length > 0
                    Layout.fillWidth: true
                    text: root.evaluationData.warning || ""
                    color: root.sessionAccent(root.sessionData.state || "unavailable")
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: root.evaluationData.reasons || []

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Rectangle {
                            Layout.preferredWidth: 8
                            Layout.preferredHeight: 8
                            Layout.alignment: Qt.AlignTop
                            Layout.topMargin: 6
                            radius: 4
                            color: theme.green
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

                Text {
                    visible: (root.evaluationData.reasons || []).length === 0
                    Layout.fillWidth: true
                    text: "Valutazione specifica non disponibile."
                    color: theme.textMuted
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

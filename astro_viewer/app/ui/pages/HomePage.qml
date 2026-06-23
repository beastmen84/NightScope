import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    signal openObject(string objectId)

    function assignedEquipment(kind) {
        var items = controller.profileAssignedEquipment || []
        return items.filter(function(item) { return item.kind === kind })
    }

    function firstAssignedName(kind) {
        var items = root.assignedEquipment(kind)
        return items.length > 0 ? items[0].name : ""
    }

    function activeProfileSummary() {
        var telescope = root.firstAssignedName("telescope")
        var eyepiece = root.firstAssignedName("eyepiece")
        var barlows = root.assignedEquipment("barlow")
        var parts = []
        if (telescope.length > 0)
            parts.push(telescope)
        else
            parts.push(controller.activeEquipmentProfile.profile_name || "Occhio nudo")
        if (eyepiece.length > 0)
            parts.push(eyepiece)
        if (barlows.length > 0)
            parts.push(barlows[0].name)
        return "Profilo attivo: " + parts.join(" + ")
    }

    function hasOpticalProfile() {
        return root.assignedEquipment("telescope").length > 0
    }

    function optionByRole(item, role) {
        var options = item.setupOptions || []
        for (var i = 0; i < options.length; i++) {
            if (options[i].role === role)
                return options[i]
        }
        return null
    }

    function displaySetupOption(item) {
        var typeText = ((item.type || "") + " " + (item.name || "")).toLowerCase()
        if (item.id === "venus" || item.id === "mercury")
            return root.optionByRole(item, "Alternativa") || root.optionByRole(item, "Consigliato")
        if (typeText.indexOf("star cloud") >= 0 || typeText.indexOf("milky way") >= 0 || typeText.indexOf("open") >= 0)
            return root.optionByRole(item, "Campo largo") || root.optionByRole(item, "Consigliato")
        if (typeText.indexOf("globular") >= 0 || typeText.indexOf("galaxy") >= 0 || typeText.indexOf("nebula") >= 0 || typeText.indexOf("nebul") >= 0)
            return root.optionByRole(item, "Alternativa") || root.optionByRole(item, "Consigliato")
        return root.optionByRole(item, "Consigliato")
    }

    function recommendedSetup(item) {
        if (!item)
            return ""
        var option = root.displaySetupOption(item)
        var fullSetup = item.recommended_setup || item.setup || ""
        var setup = option ? option.detailLabel : fullSetup
        if (!root.hasOpticalProfile())
            return setup
        var lower = setup.toLowerCase()
        if (lower.indexOf("occhio nudo") >= 0 || lower.indexOf("binocolo") >= 0 || lower.indexOf("serve almeno") >= 0)
            return setup
        var telescope = option && option.telescopeName ? option.telescopeName : root.telescopeFromSetup(fullSetup)
        return telescope.length > 0 ? telescope + " + " + setup : setup
    }

    function telescopeFromSetup(setup) {
        var text = setup || ""
        var separator = text.indexOf(" + ")
        if (separator <= 0)
            return ""
        return text.substring(0, separator)
    }

    function recommendationReason(item) {
        var option = root.displaySetupOption(item)
        var role = option ? option.role : ""
        var typeText = ((item.type || "") + " " + (item.name || "")).toLowerCase()
        if (item.id === "venus" || item.id === "mercury")
            return "Target molto luminoso: ingrandimento moderato e contrasto stabile."
        if (role === "Campo largo" || typeText.indexOf("star cloud") >= 0 || typeText.indexOf("milky way") >= 0 || typeText.indexOf("open") >= 0)
            return "Campo reale piu ampio per inquadrare meglio l'oggetto."
        if ((item.type || "") === "Pianeta")
            return "Miglior compromesso tra dettaglio planetario e seeing previsto."
        if (typeText.indexOf("globular") >= 0)
            return "Ingrandimento medio-alto per separare meglio il nucleo."
        if (typeText.indexOf("galaxy") >= 0 || typeText.indexOf("nebula") >= 0 || typeText.indexOf("nebul") >= 0)
            return "Pupilla e campo bilanciati per contrasto su cielo profondo."
        return item.equipmentExplanation || "Setup scelto in base al profilo attivo."
    }

    function objectById(objectId) {
        var groups = [controller.visiblePlanets || [], controller.recommendedDeepSky || []]
        for (var groupIndex = 0; groupIndex < groups.length; groupIndex++) {
            for (var itemIndex = 0; itemIndex < groups[groupIndex].length; itemIndex++) {
                if (groups[groupIndex][itemIndex].id === objectId)
                    return groups[groupIndex][itemIndex]
            }
        }
        return null
    }

    function planSetup(item) {
        var objectData = root.objectById(item.objectId)
        return objectData ? root.recommendedSetup(objectData) : item.setup
    }

    function planReason(item) {
        var objectData = root.objectById(item.objectId)
        return objectData ? root.recommendationReason(objectData) : "Sequenza ordinata per finestra utile e punteggio."
    }

    function visibilityLabel(item) {
        var value = (item.visibility_class || "").toLowerCase()
        if (value.indexOf("occhio") >= 0)
            return "Visibile a occhio nudo"
        if (value.indexOf("binocolo") >= 0)
            return "Visibile con binocolo"
        if (value.length > 0)
            return "Visibilita: " + item.visibility_class
        return item.observingStatus || "Finestra utile"
    }

    function objectWindow(item) {
        var time = item.homeTimeLabel ? item.homeTimeLabel : item.timeLabel
        var direction = item.direction || ""
        return root.visibilityLabel(item) + "  -  " + time + (direction.length > 0 ? "  -  " + direction : "")
    }

    function difficultyLabel(item) {
        return item.difficulty && item.difficulty !== "n/d" ? "Difficolta: " + item.difficulty : ""
    }

    function diverseEvents(limit) {
        var events = controller.events || []
        var result = []
        var seenTitles = {}
        var seenTypes = {}
        for (var i = 0; i < events.length && result.length < limit; i++) {
            var titleKey = (events[i].title || "").toLowerCase()
            var typeKey = (events[i].type || "").toLowerCase()
            if (seenTitles[titleKey])
                continue
            if (seenTypes[typeKey] && result.length < Math.max(1, limit - 1))
                continue
            seenTitles[titleKey] = true
            seenTypes[typeKey] = true
            result.push(events[i])
        }
        for (var j = 0; j < events.length && result.length < limit; j++) {
            if (result.indexOf(events[j]) < 0)
                result.push(events[j])
        }
        return result
    }

    function smartNotifications(limit) {
        var notifications = controller.notifications || []
        var result = []
        var seen = {}
        for (var i = 0; i < notifications.length && result.length < limit; i++) {
            var key = (notifications[i].title || "").toLowerCase()
            if (seen[key])
                continue
            seen[key] = true
            result.push(notifications[i])
        }
        return result
    }

    function observingLimitFactor() {
        var rain = Number(controller.weatherDigest.rainProbability || 0)
        var cloud = Number(controller.weatherDigest.cloudAverage || 0)
        var seeing = (controller.seeingTransparency.seeing || "").toLowerCase()
        if (rain >= 45)
            return "Fattore limitante: rischio precipitazioni"
        if (cloud >= 65)
            return "Fattore limitante: nuvolosita elevata"
        if (seeing.indexOf("poor") >= 0 || seeing.indexOf("scar") >= 0)
            return "Fattore limitante: seeing scarso"
        if (controller.weatherDigest.windLabel === "forte")
            return "Fattore limitante: vento forte"
        return "Fattore limitante: condizioni bilanciate"
    }

    function planetaryHint() {
        var seeing = (controller.seeingTransparency.seeing || "").toLowerCase()
        if (seeing.indexOf("excellent") >= 0 || seeing.indexOf("eccell") >= 0)
            return "Seeing eccellente"
        if (seeing.indexOf("good") >= 0 || seeing.indexOf("buon") >= 0)
            return "Seeing buono"
        if (seeing.indexOf("poor") >= 0 || seeing.indexOf("scar") >= 0)
            return "Seeing scarso"
        if ((controller.visiblePlanets || []).length > 0)
            return "Migliori target: " + controller.visiblePlanets.slice(0, 2).map(function(item) { return item.name }).join(" • ")
        return "Seeing discreto"
    }

    function deepSkyHint() {
        var bortle = Number(controller.skyQuality.bortleClass || 0)
        if (bortle >= 8)
            return "Evitare: oggetti deboli e diffusi"
        if (bortle >= 6)
            return "Consigliati: ammassi aperti e globulari"
        if (bortle >= 4)
            return "Consigliati: galassie brillanti"
        return "Ottime condizioni per nebulose brillanti"
    }

    function moonImpactHint() {
        var illuminationText = controller.moonSummary.illumination || "0%"
        var illumination = Number(illuminationText.toString().replace("%", "").trim())
        if (illumination >= 70)
            return "Impatto deep sky: elevato"
        if (illumination >= 35)
            return "Impatto deep sky: medio"
        return "Impatto deep sky: basso"
    }

    function weatherMetricColor(kind, value) {
        if (kind === "cloud")
            return value <= 30 ? theme.green : value <= 65 ? theme.amber : theme.red
        if (kind === "rain")
            return value <= 20 ? theme.green : value <= 50 ? theme.amber : theme.red
        var wind = (value || "").toLowerCase()
        if (wind.indexOf("forte") >= 0)
            return theme.red
        if (wind.indexOf("moder") >= 0)
            return theme.amber
        return theme.green
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

                    Text {
                        Layout.fillWidth: true
                        text: root.activeProfileSummary()
                        color: theme.cyan
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
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

            RowLayout {
                id: topOverview
                property real usableWidth: Math.max(0, scroll.availableWidth - 56 - (spacing * 2))

                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 14

                ColumnLayout {
                    Layout.preferredWidth: topOverview.usableWidth / 3
                    Layout.maximumWidth: topOverview.usableWidth / 3
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        title: "Qualita osservativa"
                        subtitle: controller.observingQuality.explanation
                        accentColor: theme.scoreColor(controller.observingQuality.score)
                        headerBadgeText: controller.observingQuality.score
                        headerBadgeColor: theme.scoreColor(controller.observingQuality.score)

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                text: controller.observingQuality.scoreValue + "/100"
                                color: theme.textPrimary
                                font.pixelSize: 34
                                font.weight: Font.DemiBold
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4

                                Text {
                                    Layout.fillWidth: true
                                    text: controller.weatherDigest.bestWindow !== "n/d" ? "Migliore finestra: " + controller.weatherDigest.bestWindow : controller.observingQuality.alert
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignRight
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.observingLimitFactor()
                                    color: theme.textMuted
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignRight
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        title: "Luna"
                        subtitle: controller.moonSummary.best_note
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

                            Text {
                                Layout.fillWidth: true
                                text: "Sorge " + controller.moonSummary.rise_time + "  -  tramonta " + controller.moonSummary.set_time
                                color: theme.textPrimary
                                font.pixelSize: 13
                                elide: Text.ElideRight
                            }

                            ColumnLayout {
                                Layout.preferredWidth: 150
                                spacing: 4

                                Text {
                                    Layout.fillWidth: true
                                    text: controller.moonSummary.phase + "  -  " + controller.moonSummary.illumination
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignRight
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.moonImpactHint()
                                    color: theme.textMuted
                                    font.pixelSize: 12
                                    horizontalAlignment: Text.AlignRight
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.preferredWidth: topOverview.usableWidth / 3
                    Layout.maximumWidth: topOverview.usableWidth / 3
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        title: "Punteggio planetario"
                        subtitle: "Seeing " + controller.seeingTransparency.seeing + ", vento " + controller.weatherDigest.windLabel
                        accentColor: theme.teal
                        headerBadgeText: controller.advancedScores.planetaryLabel
                        headerBadgeColor: theme.scoreColor(controller.advancedScores.planetaryLabel)

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                text: controller.advancedScores.planetaryScore + "/100"
                                color: theme.textPrimary
                                font.pixelSize: 28
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.planetaryHint()
                                color: theme.textMuted
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }
                    }

                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        title: "Punteggio cielo profondo"
                        subtitle: "Bortle " + controller.skyQuality.bortleClass + ", " + controller.skyQuality.description
                        accentColor: theme.violet
                        headerBadgeText: controller.advancedScores.deepSkyLabel
                        headerBadgeColor: theme.scoreColor(controller.advancedScores.deepSkyLabel)

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                text: controller.advancedScores.deepSkyScore + "/100"
                                color: theme.textPrimary
                                font.pixelSize: 28
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.deepSkyHint()
                                color: theme.textMuted
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignRight
                                elide: Text.ElideRight
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.preferredWidth: topOverview.usableWidth / 3
                    Layout.maximumWidth: topOverview.usableWidth / 3
                    Layout.preferredHeight: 334
                    Layout.alignment: Qt.AlignTop
                    title: "Meteo osservativo"
                    subtitle: controller.weatherStatus.length > 0 ? controller.weatherStatus : "Migliore finestra: " + controller.weatherDigest.bestWindow
                    accentColor: theme.scoreColor(controller.weatherSummary.score)

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 54
                            radius: 8
                            color: Qt.rgba(root.weatherMetricColor("cloud", controller.weatherDigest.cloudAverage).r, root.weatherMetricColor("cloud", controller.weatherDigest.cloudAverage).g, root.weatherMetricColor("cloud", controller.weatherDigest.cloudAverage).b, 0.14)
                            border.color: Qt.rgba(root.weatherMetricColor("cloud", controller.weatherDigest.cloudAverage).r, root.weatherMetricColor("cloud", controller.weatherDigest.cloudAverage).g, root.weatherMetricColor("cloud", controller.weatherDigest.cloudAverage).b, 0.5)
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 1

                                Text {
                                    Layout.fillWidth: true
                                    text: "Nuvole (Media)"
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: controller.weatherDigest.cloudAverage + "%"
                                    color: root.weatherMetricColor("cloud", controller.weatherDigest.cloudAverage)
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 54
                            radius: 8
                            color: Qt.rgba(root.weatherMetricColor("wind", controller.weatherDigest.windLabel).r, root.weatherMetricColor("wind", controller.weatherDigest.windLabel).g, root.weatherMetricColor("wind", controller.weatherDigest.windLabel).b, 0.14)
                            border.color: Qt.rgba(root.weatherMetricColor("wind", controller.weatherDigest.windLabel).r, root.weatherMetricColor("wind", controller.weatherDigest.windLabel).g, root.weatherMetricColor("wind", controller.weatherDigest.windLabel).b, 0.5)
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 1

                                Text {
                                    Layout.fillWidth: true
                                    text: "Vento (Media)"
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: controller.weatherDigest.windLabel
                                    color: root.weatherMetricColor("wind", controller.weatherDigest.windLabel)
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 54
                            radius: 8
                            color: Qt.rgba(root.weatherMetricColor("rain", controller.weatherDigest.rainProbability).r, root.weatherMetricColor("rain", controller.weatherDigest.rainProbability).g, root.weatherMetricColor("rain", controller.weatherDigest.rainProbability).b, 0.14)
                            border.color: Qt.rgba(root.weatherMetricColor("rain", controller.weatherDigest.rainProbability).r, root.weatherMetricColor("rain", controller.weatherDigest.rainProbability).g, root.weatherMetricColor("rain", controller.weatherDigest.rainProbability).b, 0.5)
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 1

                                Text {
                                    Layout.fillWidth: true
                                    text: "Pioggia (Max)"
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: controller.weatherDigest.rainProbability + "%"
                                    color: root.weatherMetricColor("rain", controller.weatherDigest.rainProbability)
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 5
                        columnSpacing: 7
                        rowSpacing: 0

                        Repeater {
                            model: controller.weatherDigest.bestHours.slice(0, 5)

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 132
                                radius: 8
                                color: "#1c222b"
                                border.color: "#303641"
                                border.width: 1

                                ColumnLayout {
                                    anchors.fill: parent
                                    anchors.margins: 6
                                    spacing: 4

                                    StatusPill {
                                        Layout.alignment: Qt.AlignHCenter
                                        text: modelData.time
                                        accentColor: theme.scoreColor(controller.weatherSummary.score)
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 3

                                        Image {
                                            Layout.preferredWidth: 14
                                            Layout.preferredHeight: 14
                                            source: controller.assetBaseUrl + "/resources/icons/cloud.svg"
                                            fillMode: Image.PreserveAspectFit
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.cloudCover + "%"
                                            color: theme.textSecondary
                                            font.pixelSize: 11
                                            horizontalAlignment: Text.AlignHCenter
                                            elide: Text.ElideRight
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 3

                                        Image {
                                            Layout.preferredWidth: 14
                                            Layout.preferredHeight: 14
                                            source: controller.assetBaseUrl + "/resources/icons/wind.svg"
                                            fillMode: Image.PreserveAspectFit
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.windKmh + " km/h"
                                            color: theme.textSecondary
                                            font.pixelSize: 11
                                            horizontalAlignment: Text.AlignHCenter
                                            elide: Text.ElideRight
                                        }
                                    }

                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 3

                                        Image {
                                            Layout.preferredWidth: 14
                                            Layout.preferredHeight: 14
                                            source: controller.assetBaseUrl + "/resources/icons/rain.svg"
                                            fillMode: Image.PreserveAspectFit
                                        }

                                        Text {
                                            Layout.fillWidth: true
                                            text: modelData.rainProbability + "%"
                                            color: theme.textSecondary
                                            font.pixelSize: 11
                                            horizontalAlignment: Text.AlignHCenter
                                            elide: Text.ElideRight
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
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
                    spacing: 18

                    Image {
                        Layout.preferredWidth: 96
                        Layout.preferredHeight: 96
                        source: controller.assetBaseUrl + "/" + controller.bestObjectOfNight.image
                        fillMode: Image.PreserveAspectFit
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 5

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                Layout.fillWidth: true
                                text: controller.bestObjectOfNight.name
                                color: theme.textPrimary
                                font.pixelSize: 28
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            StatusPill {
                                text: controller.bestObjectOfNight.observingStatus
                                accentColor: controller.bestObjectOfNight.observingStatus === "Visible now" ? theme.green : theme.amber
                            }
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
                            text: "Consigliato: " + root.recommendedSetup(controller.bestObjectOfNight)
                            color: theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: "Motivo: " + root.recommendationReason(controller.bestObjectOfNight)
                            color: theme.textMuted
                            font.pixelSize: 12
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }
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
                    Layout.minimumHeight: 286
                    Layout.columnSpan: centerGrid.columns > 1 ? 3 : 1
                    Layout.alignment: Qt.AlignTop
                    title: "Piano osservativo"
                    subtitle: "Sequenza consigliata: cosa osservare e quando"
                    accentColor: theme.green

                    Text {
                        Layout.fillWidth: true
                        visible: controller.nightPlan.length === 0
                        text: controller.isLoading ? "Aggiornamento del piano osservativo..." : "Nessun target utile nella finestra notturna."
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
                            model: controller.nightPlan.slice(0, 4)

                            delegate: ObjectRow {
                                itemData: modelData
                                assetBaseUrl: controller.assetBaseUrl
                                typeText: "Tappa consigliata"
                                difficultyText: "Difficolta: " + modelData.difficulty
                                visibilityText: modelData.timeLabel + "  -  " + modelData.direction
                                recommendedSetup: root.planSetup(modelData)
                                reasonText: root.planReason(modelData)
                                scoreText: modelData.score + "/100"
                                onOpenRequested: function(objectId) {
                                    root.openObject(objectId)
                                }
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
                                typeText: modelData.type
                                difficultyText: root.difficultyLabel(modelData)
                                visibilityText: root.objectWindow(modelData)
                                recommendedSetup: root.recommendedSetup(modelData)
                                reasonText: root.recommendationReason(modelData)
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
                    Layout.minimumHeight: lowerGrid.columns > 1 ? 432 : 0
                    Layout.alignment: Qt.AlignTop
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
                            typeText: modelData.type
                            difficultyText: root.difficultyLabel(modelData)
                            visibilityText: root.objectWindow(modelData)
                            recommendedSetup: root.recommendedSetup(modelData)
                            reasonText: root.recommendationReason(modelData)
                            onOpenRequested: function(objectId) {
                                root.openObject(objectId)
                            }
                        }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    Layout.minimumHeight: lowerGrid.columns > 1 ? 432 : 0
                    Layout.alignment: Qt.AlignTop
                    spacing: 14

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
                            model: root.diverseEvents(3)

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
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: lowerGrid.columns > 1 ? 2 : 1
                    title: "Notifiche intelligenti"
                    subtitle: "Promemoria generati dal piano osservativo"
                    accentColor: theme.coral

                    Repeater {
                        model: root.smartNotifications(3)

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

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    readonly property var observingOverview: controller
                                             ? (controller.homeObservingOverview || ({})) : ({})
    readonly property var sessionOverview: observingOverview.session || ({})
    readonly property var weatherOverview: observingOverview.weather || ({})
    readonly property var planetaryOverview: observingOverview.planetary || ({})
    readonly property var deepSkyOverview: observingOverview.deepSky || ({})
    readonly property var moonOverview: observingOverview.moon || ({})
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
        if (!item)
            return null
        var recommended = root.optionByRole(item, "Consigliato")
        if (recommended)
            return recommended
        var options = item.setupOptions || []
        return options.length > 0 ? options[0] : null
    }

    function recommendedSetup(item) {
        if (!item)
            return ""
        var option = root.displaySetupOption(item)
        var fullSetup = item.recommended_setup || item.setup || ""
        var setup = option ? (option.displayLabel || option.detailLabel) : fullSetup
        if (!root.hasOpticalProfile())
            return setup
        if (option && option.equipmentType === "Binocular")
            return setup
        if (option && option.displayLabel && option.displayLabel !== option.detailLabel)
            return option.displayLabel
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
        if (!item)
            return ""
        return item.equipmentExplanation || "Configurazione scelta in base al profilo attivo."
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

    function isInVisiblePlan(limit, objectId) {
        var plan = controller.nightPlan || []
        var itemLimit = Math.min(limit, plan.length)
        for (var i = 0; i < itemLimit; i++) {
            if (plan[i].objectId === objectId)
                return true
        }
        return false
    }

    function outsideVisiblePlan(items, limit) {
        var result = []
        var source = items || []
        for (var i = 0; i < source.length; i++) {
            if (!root.isInVisiblePlan(limit, source[i].id))
                result.push(source[i])
        }
        return result
    }

    function otherVisiblePlanets() {
        return root.outsideVisiblePlan(controller.visiblePlanets || [], 4)
    }

    function otherVisibleDeepSky() {
        return root.outsideVisiblePlan(controller.recommendedDeepSky || [], 4)
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
        if (value.indexOf("telescopio") >= 0 || value.indexOf("pianeta") >= 0)
            return "Visibile con telescopio"
        if (value.length > 0)
            return "Visibile con " + item.visibility_class
        return item.observingStatus || "Finestra utile"
    }

    function objectWindow(item) {
        var time = item.homeTimeLabel ? item.homeTimeLabel : item.timeLabel
        var direction = item.direction || ""
        return root.visibilityLabel(item) + "  -  " + time + (direction.length > 0 ? "  -  " + direction : "")
    }

    function difficultyLabel(item) {
        return item.difficulty && item.difficulty !== "n/d" ? "Difficoltà: " + item.difficulty : ""
    }

    function eventDateValue(eventData) {
        var parts = (eventData.date_label || "").split("/")
        if (parts.length !== 3)
            return 9999999999999
        var day = Number(parts[0])
        var month = Number(parts[1]) - 1
        var year = Number(parts[2])
        return new Date(year, month, day).getTime()
    }

    function eventAccent(type) {
        if (type === "Luna")
            return theme.amber
        if (type === "Sciame meteorico")
            return theme.teal
        if (type === "Eclissi")
            return theme.coral
        if (type === "Congiunzione")
            return theme.violet
        return theme.cyan
    }

    function chronologicalEvents(limit) {
        var events = (controller.events || []).slice(0)
        events.sort(function(left, right) {
            return root.eventDateValue(left) - root.eventDateValue(right)
        })
        var result = []
        var seenTitles = {}
        for (var i = 0; i < events.length && result.length < limit; i++) {
            var titleKey = (events[i].title || "").toLowerCase()
            if (seenTitles[titleKey])
                continue
            seenTitles[titleKey] = true
            result.push(events[i])
        }
        return result
    }

    function skyCompassRotation(direction) {
        if (direction === "Nord-Est")
            return 45
        if (direction === "Est")
            return 90
        if (direction === "Sud-Est")
            return 135
        if (direction === "Sud")
            return 180
        if (direction === "Sud-Ovest")
            return 225
        if (direction === "Ovest")
            return 270
        if (direction === "Nord-Ovest")
            return 315
        return 0
    }

    function skyCompassTypeIconKind(typeText) {
        var value = (typeText || "").toLowerCase()
        if (value.indexOf("pianeta") >= 0)
            return "planet"
        if (value.indexOf("galass") >= 0 || value.indexOf("galaxy") >= 0)
            return "galaxy"
        if (value.indexOf("nebul") >= 0)
            return "nebula"
        if (value.indexOf("globular") >= 0)
            return "globular_cluster"
        if (value.indexOf("ammasso") >= 0 || value.indexOf("cluster") >= 0)
            return "open_cluster"
        return "target"
    }

    function sessionAccent(state) {
        if (state === "recommended")
            return theme.teal
        if (state === "monitor")
            return theme.amber
        if (state === "discouraged")
            return theme.red
        return theme.textMuted
    }

    function nightPlanEmptyText() {
        return controller.isLoading ? "Aggiornamento del piano osservativo..." : "Nessun oggetto utile nella finestra notturna."
    }

    function scoreText(item) {
        return item && item.score !== undefined && item.score !== null ? item.score + "/100" : ""
    }

    function potentialTargetsText(limit) {
        var sources = [controller.visiblePlanets || [], controller.recommendedDeepSky || []]
        var names = []
        var seen = {}
        for (var groupIndex = 0; groupIndex < sources.length; groupIndex++) {
            for (var itemIndex = 0; itemIndex < sources[groupIndex].length; itemIndex++) {
                var name = sources[groupIndex][itemIndex].name || ""
                if (name.length === 0 || seen[name])
                    continue
                seen[name] = true
                names.push(name)
                if (names.length >= limit)
                    return "• " + names.join("\n• ")
            }
        }
        return names.length > 0 ? "• " + names.join("\n• ") : ""
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
                        title: "Sessione di stasera"
                        subtitle: root.sessionOverview.detail || ""
                        accentColor: root.sessionAccent(root.sessionOverview.state || "unavailable")
                        headerBadgeText: root.sessionOverview.badge || ""
                        headerBadgeColor: accentColor

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                Layout.fillWidth: true
                                text: root.sessionOverview.windowText || "Finestra osservativa non disponibile"
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.sessionOverview.limitingFactor || ""
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
                        title: "Luna"
                        subtitle: root.moonOverview.summary || ""
                        accentColor: theme.amber

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 82
                            radius: 8
                            color: moonMouse.containsMouse ? "#20242b" : "transparent"
                            border.color: moonMouse.containsMouse ? "#303641" : "transparent"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 12

                                Rectangle {
                                    Layout.preferredWidth: 62
                                    Layout.preferredHeight: 62
                                    radius: 8
                                    color: "#111319"
                                    border.color: "#303641"
                                    border.width: 1

                                    Image {
                                        anchors.fill: parent
                                        anchors.margins: 8
                                        source: controller.assetBaseUrl + "/" + controller.moonSummary.image
                                        fillMode: Image.PreserveAspectFit
                                        sourceSize.width: 96
                                        sourceSize.height: 96
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Text {
                                        Layout.fillWidth: true
                                        text: "Sorge " + controller.moonSummary.rise_time
                                        color: theme.textPrimary
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: "Tramonta " + controller.moonSummary.set_time
                                        color: theme.textPrimary
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }
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
                                        text: root.moonOverview.impactLabel || ""
                                        color: theme.textMuted
                                        font.pixelSize: 12
                                        horizontalAlignment: Text.AlignRight
                                        elide: Text.ElideRight
                                    }
                                }
                            }

                            MouseArea {
                                id: moonMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: root.openObject("moon")
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
                        title: "Condizioni planetarie"
                        subtitle: root.planetaryOverview.secondaryMetric || ""
                        accentColor: theme.teal
                        headerBadgeText: root.planetaryOverview.label || ""
                        headerBadgeColor: root.planetaryOverview.label === "n/d"
                                          ? theme.textMuted
                                          : theme.scoreColor(root.planetaryOverview.label || "")

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                text: root.planetaryOverview.primaryMetric || ""
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.planetaryOverview.hint || ""
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
                        title: "Condizioni del cielo profondo"
                        subtitle: root.deepSkyOverview.secondaryMetric || ""
                        accentColor: theme.violet
                        headerBadgeText: root.deepSkyOverview.label || ""
                        headerBadgeColor: root.deepSkyOverview.label === "n/d"
                                          ? theme.textMuted
                                          : theme.scoreColor(root.deepSkyOverview.label || "")

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                text: root.deepSkyOverview.primaryMetric || ""
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: root.deepSkyOverview.hint || ""
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
                    subtitle: controller.weatherStatus.length > 0
                              ? controller.weatherStatus : (root.weatherOverview.windowText || "")
                    accentColor: root.weatherOverview.available
                                 ? theme.scoreColor(root.weatherOverview.scoreLabel || "")
                                 : theme.textMuted
                    headerBadgeText: root.weatherOverview.available
                                     ? ((root.weatherOverview.scoreLabel || "n/d") + "  "
                                        + root.weatherOverview.scoreValue + "/100") : "n/d"
                    headerBadgeColor: accentColor

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 8

                        Rectangle {
                            id: cloudMetric

                            property color metricColor: root.weatherOverview.available
                                                        ? root.weatherMetricColor("cloud", controller.weatherDigest.cloudAverage)
                                                        : theme.textMuted

                            Layout.fillWidth: true
                            Layout.preferredHeight: 54
                            radius: 8
                            color: Qt.rgba(metricColor.r, metricColor.g, metricColor.b, 0.14)
                            border.color: Qt.rgba(metricColor.r, metricColor.g, metricColor.b, 0.5)
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 1

                                Text {
                                    Layout.fillWidth: true
                                    text: "Nuvole (media)"
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.weatherOverview.available
                                          ? controller.weatherDigest.cloudAverage + "%" : "n/d"
                                    color: cloudMetric.metricColor
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            id: windMetric

                            property color metricColor: root.weatherOverview.available
                                                        ? root.weatherMetricColor("wind", controller.weatherDigest.windLabel)
                                                        : theme.textMuted

                            Layout.fillWidth: true
                            Layout.preferredHeight: 54
                            radius: 8
                            color: Qt.rgba(metricColor.r, metricColor.g, metricColor.b, 0.14)
                            border.color: Qt.rgba(metricColor.r, metricColor.g, metricColor.b, 0.5)
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 1

                                Text {
                                    Layout.fillWidth: true
                                    text: "Vento (media)"
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.weatherOverview.available
                                          ? controller.weatherDigest.windLabel : "n/d"
                                    color: windMetric.metricColor
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }
                            }
                        }

                        Rectangle {
                            id: rainMetric

                            property color metricColor: root.weatherOverview.available
                                                        ? root.weatherMetricColor("rain", controller.weatherDigest.rainProbability)
                                                        : theme.textMuted

                            Layout.fillWidth: true
                            Layout.preferredHeight: 54
                            radius: 8
                            color: Qt.rgba(metricColor.r, metricColor.g, metricColor.b, 0.14)
                            border.color: Qt.rgba(metricColor.r, metricColor.g, metricColor.b, 0.5)
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 6
                                spacing: 1

                                Text {
                                    Layout.fillWidth: true
                                    text: "Pioggia (max)"
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.weatherOverview.available
                                          ? controller.weatherDigest.rainProbability + "%" : "n/d"
                                    color: rainMetric.metricColor
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
                            model: root.weatherOverview.available
                                   ? controller.weatherDigest.bestHours.slice(0, 5) : []

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
                                        accentColor: theme.scoreColor(root.weatherOverview.scoreLabel || "")
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
                id: skyCompassCard

                property var compassData: controller.skyCompass || {}
                property bool wide: root.width > 1180
                property bool medium: root.width > 760

                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                Layout.minimumHeight: skyCompassCard.compassData.available && wide ? 286 : 0
                title: "Sky Compass"
                subtitle: "Dove iniziare stasera"
                accentColor: theme.teal
                headerContent: [
                    RowLayout {
                        visible: skyCompassCard.compassData.available
                                 && (skyCompassCard.compassData.alternatives || []).length > 0
                        spacing: 8

                        Text {
                            text: "Alternative"
                            color: theme.textSecondary
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Repeater {
                            model: skyCompassCard.compassData.alternatives || []

                            delegate: StatusPill {
                                text: modelData.direction
                                accentColor: theme.teal
                                opacity: 0.9
                            }
                        }
                    }
                ]

                Text {
                    Layout.fillWidth: true
                    visible: !skyCompassCard.compassData.available
                    text: skyCompassCard.compassData.message || "Nessun target consigliato al momento."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }

                GridLayout {
                    Layout.fillWidth: true
                    visible: skyCompassCard.compassData.available
                    columns: skyCompassCard.wide ? 3 : skyCompassCard.medium ? 2 : 1
                    columnSpacing: 26
                    rowSpacing: 18

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: skyCompassCard.wide ? 380 : 0
                        Layout.alignment: Qt.AlignTop
                        spacing: 12

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 18

                            Rectangle {
                                Layout.preferredWidth: 168
                                Layout.preferredHeight: 168
                                Layout.alignment: Qt.AlignVCenter
                                radius: 84
                                color: "#111820"
                                border.color: "#26404a"
                                border.width: 1

                                Canvas {
                                    id: skyCompassCanvas
                                    anchors.fill: parent
                                    anchors.margins: 12
                                    antialiasing: true

                                    property real selectedDegrees: root.skyCompassRotation(skyCompassCard.compassData.direction || "")

                                    onSelectedDegreesChanged: requestPaint()
                                    onWidthChanged: requestPaint()
                                    onHeightChanged: requestPaint()

                                    onPaint: {
                                        var ctx = getContext("2d")
                                        var cx = width / 2
                                        var cy = height / 2
                                        var outerRadius = Math.min(width, height) / 2 - 5
                                        var midRadius = outerRadius - 24
                                        var innerRadius = 42
                                        var centerAngle = (selectedDegrees - 90) * Math.PI / 180
                                        var sectorWidth = Math.PI / 4
                                        var startAngle = centerAngle - sectorWidth / 2
                                        var endAngle = centerAngle + sectorWidth / 2

                                        ctx.clearRect(0, 0, width, height)
                                        ctx.lineWidth = 2
                                        ctx.strokeStyle = "#243746"
                                        ctx.beginPath()
                                        ctx.arc(cx, cy, outerRadius, 0, Math.PI * 2, false)
                                        ctx.stroke()

                                        ctx.strokeStyle = "#1f5861"
                                        ctx.globalAlpha = 0.72
                                        ctx.beginPath()
                                        ctx.arc(cx, cy, midRadius, 0, Math.PI * 2, false)
                                        ctx.stroke()
                                        ctx.globalAlpha = 1

                                        ctx.fillStyle = "rgba(67, 226, 181, 0.26)"
                                        ctx.strokeStyle = "rgba(67, 226, 181, 0.82)"
                                        ctx.lineWidth = 2
                                        ctx.beginPath()
                                        ctx.arc(cx, cy, outerRadius - 8, startAngle, endAngle, false)
                                        ctx.lineTo(cx + Math.cos(endAngle) * innerRadius, cy + Math.sin(endAngle) * innerRadius)
                                        ctx.arc(cx, cy, innerRadius, endAngle, startAngle, true)
                                        ctx.closePath()
                                        ctx.fill()
                                        ctx.stroke()

                                        ctx.strokeStyle = "#2b6570"
                                        ctx.lineWidth = 2
                                        for (var tick = 0; tick < 8; tick++) {
                                            var angle = (tick * 45 - 90) * Math.PI / 180
                                            var from = outerRadius - 18
                                            var to = outerRadius - 9
                                            ctx.beginPath()
                                            ctx.moveTo(cx + Math.cos(angle) * from, cy + Math.sin(angle) * from)
                                            ctx.lineTo(cx + Math.cos(angle) * to, cy + Math.sin(angle) * to)
                                            ctx.stroke()
                                        }

                                        ctx.save()
                                        ctx.translate(cx, cy)
                                        ctx.rotate(centerAngle + Math.PI / 2)
                                        ctx.fillStyle = "rgba(67, 226, 181, 0.9)"
                                        ctx.beginPath()
                                        ctx.moveTo(0, -31)
                                        ctx.lineTo(17, 17)
                                        ctx.lineTo(0, 7)
                                        ctx.lineTo(-17, 17)
                                        ctx.closePath()
                                        ctx.fill()
                                        ctx.restore()
                                    }
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.top: parent.top
                                    anchors.topMargin: 10
                                    text: "N"
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.right: parent.right
                                    anchors.rightMargin: 12
                                    text: "E"
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 10
                                    text: "S"
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: 12
                                    text: "O"
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignVCenter
                                spacing: 8

                                Text {
                                    Layout.fillWidth: true
                                    text: "Inizia da"
                                    color: theme.textSecondary
                                    font.pixelSize: 13
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: skyCompassCard.compassData.direction || "—"
                                    color: theme.textPrimary
                                    font.pixelSize: 42
                                    font.weight: Font.Bold
                                    elide: Text.ElideRight
                                }

                                RowLayout {
                                    Layout.fillWidth: true
                                    spacing: 8

                                    Rectangle {
                                        Layout.preferredWidth: 8
                                        Layout.preferredHeight: 8
                                        radius: 4
                                        color: theme.teal
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: skyCompassCard.compassData.zoneLabel || "Zona consigliata"
                                        color: theme.teal
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: skyCompassCard.compassData.targetCountLabel || ""
                                    color: theme.textSecondary
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    visible: (skyCompassCard.compassData.cautionText || "").length > 0
                                    text: skyCompassCard.compassData.cautionText || ""
                                    color: theme.amber
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: skyCompassCard.wide ? 360 : 0
                        Layout.alignment: Qt.AlignTop
                        spacing: 10

                        Text {
                            Layout.fillWidth: true
                            text: "Perché questa direzione?"
                            color: theme.textPrimary
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Repeater {
                            model: skyCompassCard.compassData.decisionReasons || []

                            delegate: RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Rectangle {
                                    Layout.preferredWidth: 26
                                    Layout.preferredHeight: 26
                                    Layout.alignment: Qt.AlignTop
                                    radius: 13
                                    color: Qt.rgba(theme.teal.r, theme.teal.g, theme.teal.b, 0.13)
                                    border.color: Qt.rgba(theme.teal.r, theme.teal.g, theme.teal.b, 0.34)
                                    border.width: 1

                                    Rectangle {
                                        anchors.centerIn: parent
                                        width: 8
                                        height: 8
                                        radius: 4
                                        color: theme.teal
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData
                                    color: theme.textSecondary
                                    font.pixelSize: 13
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.preferredWidth: skyCompassCard.wide ? 330 : 0
                        Layout.alignment: Qt.AlignTop
                        spacing: 10

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                text: "Target principali"
                                color: theme.textPrimary
                                font.pixelSize: 15
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                        }

                        Repeater {
                            model: skyCompassCard.compassData.primaryTargets || []

                            delegate: RowLayout {
                                Layout.fillWidth: true
                                spacing: 10

                                Canvas {
                                    Layout.preferredWidth: 28
                                    Layout.preferredHeight: 28
                                    Layout.alignment: Qt.AlignVCenter
                                    antialiasing: true

                                    property string iconKind: root.skyCompassTypeIconKind(modelData.type)

                                    onIconKindChanged: requestPaint()
                                    onWidthChanged: requestPaint()
                                    onHeightChanged: requestPaint()

                                    onPaint: {
                                        var ctx = getContext("2d")
                                        var cx = width / 2
                                        var cy = height / 2
                                        ctx.clearRect(0, 0, width, height)
                                        ctx.lineWidth = 2
                                        ctx.strokeStyle = "rgba(67, 226, 181, 0.88)"
                                        ctx.fillStyle = "rgba(67, 226, 181, 0.16)"

                                        if (iconKind === "planet") {
                                            ctx.beginPath()
                                            ctx.arc(cx, cy, 7, 0, Math.PI * 2, false)
                                            ctx.fill()
                                            ctx.stroke()
                                            ctx.save()
                                            ctx.translate(cx, cy)
                                            ctx.rotate(-0.36)
                                            ctx.beginPath()
                                            ctx.moveTo(-13, 1)
                                            ctx.quadraticCurveTo(0, -5, 13, 1)
                                            ctx.moveTo(-13, -1)
                                            ctx.quadraticCurveTo(0, 5, 13, -1)
                                            ctx.stroke()
                                            ctx.restore()
                                        } else if (iconKind === "galaxy") {
                                            ctx.beginPath()
                                            ctx.arc(cx, cy, 2.4, 0, Math.PI * 2, false)
                                            ctx.fill()
                                            ctx.beginPath()
                                            ctx.arc(cx, cy, 5, 0.3, Math.PI * 1.35, false)
                                            ctx.stroke()
                                            ctx.beginPath()
                                            ctx.arc(cx, cy, 9, Math.PI * 1.15, Math.PI * 2.15, false)
                                            ctx.stroke()
                                        } else if (iconKind === "nebula") {
                                            ctx.globalAlpha = 0.82
                                            for (var nebulaIndex = 0; nebulaIndex < 4; nebulaIndex++) {
                                                var cloudX = cx + [-5, 2, 6, -1][nebulaIndex]
                                                var cloudY = cy + [1, -4, 3, 6][nebulaIndex]
                                                ctx.beginPath()
                                                ctx.arc(cloudX, cloudY, [6, 7, 5, 5][nebulaIndex], 0, Math.PI * 2, false)
                                                ctx.fill()
                                                ctx.stroke()
                                            }
                                            ctx.globalAlpha = 1
                                        } else {
                                            var compact = iconKind === "globular_cluster"
                                            var points = compact ? [[0, 0], [-5, -2], [5, -1], [-3, 5], [4, 4], [0, -6]] : [[-8, -5], [0, -8], [8, -4], [-6, 5], [2, 4], [9, 7]]
                                            for (var pointIndex = 0; pointIndex < points.length; pointIndex++) {
                                                ctx.beginPath()
                                                ctx.arc(cx + points[pointIndex][0], cy + points[pointIndex][1], compact ? 2.2 : 2, 0, Math.PI * 2, false)
                                                ctx.fill()
                                                ctx.stroke()
                                            }
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 1

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.name
                                        color: theme.textPrimary
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        maximumLineCount: 1
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        visible: (modelData.type || "").length > 0
                                        text: modelData.type || ""
                                        color: theme.textMuted
                                        font.pixelSize: 11
                                        maximumLineCount: 1
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: (skyCompassCard.compassData.otherTargetCountLabel || "").length > 0
                            text: skyCompassCard.compassData.otherTargetCountLabel || ""
                            color: theme.textSecondary
                            font.pixelSize: 12
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
                    Layout.minimumHeight: controller.nightPlan.length > 0 ? 286 : 0
                    Layout.columnSpan: centerGrid.columns > 1 ? 3 : 1
                    Layout.alignment: Qt.AlignTop
                    title: "Piano osservativo consigliato"
                    subtitle: "Sequenza consigliata: cosa osservare e quando"
                    accentColor: theme.green

                    ColumnLayout {
                        id: sessionDecisionContent

                        Layout.fillWidth: true
                        visible: controller.nightPlan.length === 0 && controller.isObservingSessionBlocked
                        spacing: 14

                        property bool opportunityWide: root.width > 760 && controller.showObservingSessionOpportunity

                        GridLayout {
                            Layout.fillWidth: true
                            columns: sessionDecisionContent.opportunityWide ? 2 : 1
                            columnSpacing: 36
                            rowSpacing: 12

                            RowLayout {
                                Layout.row: 0
                                Layout.column: 0
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                spacing: 8

                                Text {
                                    text: controller.observingSessionIcon
                                    color: controller.observingSessionState === "monitor" ? theme.amber : theme.red
                                    font.pixelSize: 18
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: controller.observingSessionTitle
                                    color: theme.textPrimary
                                    font.pixelSize: 17
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }
                            }

                            ColumnLayout {
                                Layout.row: 1
                                Layout.column: 0
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                spacing: 10

                                Text {
                                    Layout.fillWidth: true
                                    text: controller.observingSessionDetail
                                    color: controller.observingSessionState === "monitor" ? theme.amber : theme.red
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: controller.observingSessionDescription
                                    color: theme.textSecondary
                                    font.pixelSize: 13
                                    wrapMode: Text.WordWrap
                                }
                            }

                            ColumnLayout {
                                Layout.row: sessionDecisionContent.opportunityWide ? 0 : 2
                                Layout.column: sessionDecisionContent.opportunityWide ? 1 : 0
                                Layout.rowSpan: sessionDecisionContent.opportunityWide ? 2 : 1
                                Layout.fillWidth: true
                                Layout.alignment: Qt.AlignTop
                                visible: controller.showObservingSessionOpportunity
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: controller.suggestedObservingWindow.length > 0
                                    spacing: 2

                                    Text {
                                        Layout.fillWidth: true
                                        text: "Migliore finestra prevista"
                                        color: theme.textMuted
                                        font.pixelSize: 12
                                        wrapMode: Text.WordWrap
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: controller.suggestedObservingWindow
                                        color: theme.textPrimary
                                        font.pixelSize: 16
                                        font.weight: Font.DemiBold
                                        wrapMode: Text.WordWrap
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    visible: root.potentialTargetsText(3).length > 0
                                    spacing: 4

                                    Text {
                                        Layout.fillWidth: true
                                        text: "Target potenzialmente interessanti"
                                        color: theme.textMuted
                                        font.pixelSize: 12
                                        wrapMode: Text.WordWrap
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: root.potentialTargetsText(3)
                                        color: theme.textSecondary
                                        font.pixelSize: 13
                                        lineHeight: 1.15
                                        wrapMode: Text.WordWrap
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: controller.nightPlan.length === 0 && !controller.isObservingSessionBlocked
                        text: root.nightPlanEmptyText()
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
                                difficultyText: "Difficoltà: " + modelData.difficulty
                                visibilityText: modelData.timeLabel + "  -  " + modelData.direction
                                recommendedSetup: root.planSetup(modelData)
                                reasonText: root.planReason(modelData)
                                scoreText: "#" + (index + 1)
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
                    title: controller.isObservingSessionBlocked ? "Pianeti potenzialmente visibili" : "Altri pianeti visibili"
                    subtitle: "Oggetti utili non già presenti nel piano consigliato"
                    accentColor: theme.teal

                    Text {
                        Layout.fillWidth: true
                        visible: root.otherVisiblePlanets().length === 0
                        text: controller.isLoading ? "Calcolo della visibilità..." : "Nessun altro pianeta utile fuori dal piano consigliato."
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
                            model: root.otherVisiblePlanets().slice(0, 4)

                            delegate: ObjectRow {
                                itemData: modelData
                                assetBaseUrl: controller.assetBaseUrl
                                typeText: modelData.type
                                difficultyText: root.difficultyLabel(modelData)
                                visibilityText: root.objectWindow(modelData)
                                recommendedSetup: root.recommendedSetup(modelData)
                                reasonText: root.recommendationReason(modelData)
                                scoreText: root.scoreText(modelData)
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
                    Layout.alignment: Qt.AlignTop
                    title: controller.isObservingSessionBlocked ? "Oggetti cielo profondo potenzialmente visibili" : "Oggetti cielo profondo visibili"
                    subtitle: controller.skyQualityWarning.length > 0 ? controller.skyQualityWarning : "Oggetti utili non già presenti nel piano consigliato"
                    accentColor: theme.violet

                    Text {
                        Layout.fillWidth: true
                        visible: root.otherVisibleDeepSky().length === 0
                        text: controller.isLoading ? "Calcolo della visibilità..." : "Nessun altro oggetto cielo profondo utile fuori dal piano consigliato."
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
                            model: root.otherVisibleDeepSky().slice(0, 4)

                            delegate: ObjectRow {
                                itemData: modelData
                                assetBaseUrl: controller.assetBaseUrl
                                typeText: modelData.type
                                difficultyText: root.difficultyLabel(modelData)
                                visibilityText: root.objectWindow(modelData)
                                recommendedSetup: root.recommendedSetup(modelData)
                                reasonText: root.recommendationReason(modelData)
                                scoreText: root.scoreText(modelData)
                                onOpenRequested: function(objectId) {
                                    root.openObject(objectId)
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
                Layout.alignment: Qt.AlignTop
                title: "Prossimi eventi"
                subtitle: "Ordinati per data"
                accentColor: theme.amber

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1040 ? 4 : root.width > 760 ? 2 : 1
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: root.chronologicalEvents(root.width > 900 ? 8 : 4)

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 74
                            radius: 8
                            color: "#151a20"
                            border.color: "#29313b"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                StatusPill {
                                    text: modelData.date_label
                                    accentColor: root.eventAccent(modelData.type)
                                    Layout.alignment: Qt.AlignVCenter
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
                                        maximumLineCount: 1
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.type + "  -  " + modelData.best_time
                                        color: theme.textSecondary
                                        font.pixelSize: 12
                                        maximumLineCount: 1
                                        elide: Text.ElideRight
                                    }
                                }
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.chronologicalEvents(1).length === 0
                    text: "Nessun evento in calendario."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

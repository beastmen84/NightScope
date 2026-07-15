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
    readonly property var nightOverview: controller
                                           ? (controller.homeNightPlanOverview || ({})) : ({})
    readonly property var nightProfileOverview: nightOverview.profile || ({})
    readonly property var nightPlanOverview: nightOverview.plan || ({})
    readonly property var nightAlternativesOverview: nightOverview.alternatives || ({})
    readonly property var calendarOverview: controller ? (controller.calendarOverview || ({})) : ({})
    readonly property var skyCompassOverview: controller ? (controller.skyCompass || ({})) : ({})
    readonly property bool skyCompassFilterAvailable: skyCompassOverview.available === true
                                                      && (skyCompassOverview.targets || []).length > 0
    property string targetFilter: "all"
    property bool skyCompassFilterEnabled: false
    property var skyCompassFilterTargetIds: ({})
    property string skyCompassFilterTargetSignature: ""
    signal openObject(string objectId)
    signal openEvent(string eventId)
    signal openCalendar()
    signal openLocation()

    function normalizedTargetId(value) {
        return String(value || "").trim().toLowerCase()
    }

    function skyCompassTargetState(data) {
        var targets = data && data.targets ? data.targets : []
        var ids = {}
        var signatureIds = []
        for (var i = 0; i < targets.length; i++) {
            var objectId = root.normalizedTargetId(targets[i].id)
            if (objectId.length === 0 || ids[objectId] === true)
                continue
            ids[objectId] = true
            signatureIds.push(objectId)
        }
        signatureIds.sort()
        return {"ids": ids, "signature": signatureIds.join("|")}
    }

    function syncSkyCompassFilter(data) {
        var state = root.skyCompassTargetState(data)
        var available = data && data.available === true && state.signature.length > 0
        if (!available) {
            var wasEnabled = root.skyCompassFilterEnabled
            root.skyCompassFilterEnabled = false
            root.skyCompassFilterTargetIds = ({})
            root.skyCompassFilterTargetSignature = ""
            if (wasEnabled)
                Qt.callLater(root.resetVisibleTargetScroll)
            return
        }
        if (state.signature === root.skyCompassFilterTargetSignature)
            return
        root.skyCompassFilterTargetIds = state.ids
        root.skyCompassFilterTargetSignature = state.signature
        if (root.skyCompassFilterEnabled)
            Qt.callLater(root.resetVisibleTargetScroll)
    }

    function setSkyCompassFilter(enabled) {
        root.syncSkyCompassFilter(root.skyCompassOverview)
        if (enabled && !root.skyCompassFilterAvailable)
            return
        root.skyCompassFilterEnabled = Boolean(enabled)
        if (root.skyCompassFilterEnabled)
            root.targetFilter = "all"
        Qt.callLater(root.resetVisibleTargetScroll)
    }

    function resetVisibleTargetScroll() {
        if (visibleTargetList && visibleTargetList.count > 0)
            visibleTargetList.positionViewAtBeginning()
    }

    function skyCompassScopedItems(items) {
        if (!root.skyCompassFilterEnabled)
            return items
        var ids = root.skyCompassFilterTargetIds
        return items.filter(function(item) {
            return ids[root.normalizedTargetId(item.objectId)] === true
        })
    }

    function filteredNightPlanItems() {
        return root.skyCompassScopedItems(root.nightPlanOverview.items || [])
    }

    function eventAccent(typeCode) {
        if (typeCode === "moon")
            return theme.amber
        if (typeCode === "meteor_shower")
            return theme.teal
        if (typeCode === "eclipse")
            return theme.coral
        if (typeCode === "planetary_conjunction")
            return theme.violet
        if (typeCode === "solar_conjunction")
            return theme.coral
        if (typeCode === "satellite_pass")
            return theme.cyan
        if (typeCode === "comet_window")
            return theme.teal
        return theme.cyan
    }

    function chronologicalEvents(limit) {
        return (root.calendarOverview.homeItems || root.calendarOverview.items || []).slice(0, limit)
    }

    function skyCompassRotation(directionCode) {
        if (directionCode === "north_east")
            return 45
        if (directionCode === "east")
            return 90
        if (directionCode === "south_east")
            return 135
        if (directionCode === "south")
            return 180
        if (directionCode === "south_west")
            return 225
        if (directionCode === "west")
            return 270
        if (directionCode === "north_west")
            return 315
        return 0
    }

    function skyCompassTypeIconKind(typeCode) {
        return typeCode || "target"
    }

    function skyCompassGeometricTargetCountLabel(count) {
        var value = Number(count || 0)
        if (value === 1)
            return qsTr("1 oggetto geometricamente visibile")
        return qsTr("%1 oggetti geometricamente visibili").arg(value)
    }

    function alternativeCountLabel(count) {
        var value = Number(count || 0)
        return value === 1 ? qsTr("1 oggetto") : qsTr("%1 oggetti").arg(value)
    }

    function sessionAccent(state) {
        if (state === "pending")
            return theme.cyan
        if (state === "recommended")
            return theme.teal
        if (state === "monitor")
            return theme.amber
        if (state === "discouraged")
            return theme.red
        return theme.textMuted
    }

    function planAccent(state) {
        if (state === "recommended")
            return theme.green
        if (state === "monitor")
            return theme.amber
        if (state === "discouraged")
            return theme.red
        if (state === "pending")
            return theme.cyan
        return theme.textMuted
    }

    function alternativeItems() {
        return root.skyCompassScopedItems(root.nightAlternativesOverview.items || [])
    }

    function filteredNightAlternatives() {
        var items = root.alternativeItems()
        if (root.targetFilter === "all")
            return items
        return items.filter(function(item) {
            return item.category === root.targetFilter
        })
    }

    function alternativeCount(filter) {
        if (filter === "all")
            return root.alternativeItems().length
        var items = root.alternativeItems()
        var count = 0
        for (var i = 0; i < items.length; i++) {
            if (items[i].category === filter)
                count += 1
        }
        return count
    }

    function alternativeFilterLabel(filter) {
        if (filter === "planet")
            return qsTr("Pianeti (%1)").arg(root.alternativeCount(filter))
        if (filter === "deep_sky")
            return qsTr("Cielo profondo (%1)").arg(root.alternativeCount(filter))
        return qsTr("Tutti (%1)").arg(root.alternativeCount("all"))
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

    Component.onCompleted: root.syncSkyCompassFilter(root.skyCompassOverview)

    Connections {
        target: root.controller

        function onSkyCompassChanged() {
            root.syncSkyCompassFilter(root.controller ? (root.controller.skyCompass || ({})) : ({}))
        }
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
                        text: qsTr("Stasera dal tuo cielo")
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.hasValidLocation
                              ? controller.activeLocationLabel + "  -  " + controller.activeLocationSource
                              : controller.activeLocationLabel
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: root.nightProfileOverview.summary || qsTr("Profilo attivo: Default  ·  occhio nudo")
                        color: theme.cyan
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        wrapMode: Text.WordWrap
                        maximumLineCount: 2
                    }
                }

                DarkButton {
                    visible: !controller.hasValidLocation
                    Layout.preferredWidth: 154
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    text: qsTr("Configura località")
                    accentColor: theme.cyan
                    onClicked: root.openLocation()
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                visible: controller.isLoading || controller.serviceStatus.length > 0
                radius: 8
                color: "#1c222b"
                border.color: controller.startupLocationDetectionRunning
                              ? theme.cyan
                              : (controller.serviceStatus.length > 0 ? theme.coral : theme.cyan)
                border.width: 1
                implicitHeight: statusText.implicitHeight + 22

                Text {
                    id: statusText
                    anchors.fill: parent
                    anchors.margins: 11
                    text: controller.isLoading ? qsTr("Aggiornamento dei dati del cielo...") : controller.serviceStatus
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
                        title: qsTr("Sessione di stasera")
                        subtitle: root.sessionOverview.detail || ""
                        subtitleWrap: true
                        accentColor: root.sessionAccent(root.sessionOverview.state || "unavailable")
                        headerBadgeText: root.sessionOverview.badge || ""
                        headerBadgeColor: accentColor

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            Text {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                text: root.sessionOverview.windowText || qsTr("Finestra osservativa non disponibile")
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }

                            Text {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                text: root.sessionOverview.limitingFactor || ""
                                color: theme.textMuted
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignRight
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }
                        }
                    }

                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        title: qsTr("Luna")
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
                                        anchors.centerIn: parent
                                        width: 38
                                        height: 38
                                        visible: controller.hasValidLocation
                                        source: visible
                                                ? controller.assetBaseUrl + "/resources/icons/moon.svg"
                                                : ""
                                        fillMode: Image.PreserveAspectFit
                                        sourceSize.width: 64
                                        sourceSize.height: 64
                                    }

                                    Text {
                                        anchors.centerIn: parent
                                        visible: !controller.hasValidLocation
                                        text: qsTr("n/d")
                                        color: theme.textMuted
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                    }
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Text {
                                        Layout.fillWidth: true
                                        text: qsTr("Sorge %1").arg(controller.moonSummary.rise_time)
                                        color: theme.textPrimary
                                        font.pixelSize: 13
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: qsTr("Tramonta %1").arg(controller.moonSummary.set_time)
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
                                        Layout.minimumWidth: 0
                                        text: root.moonOverview.impactLabel || ""
                                        color: theme.textMuted
                                        font.pixelSize: 12
                                        horizontalAlignment: Text.AlignRight
                                        wrapMode: Text.WordWrap
                                        elide: Text.ElideRight
                                        maximumLineCount: 2
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
                        title: qsTr("Condizioni planetarie")
                        subtitle: root.planetaryOverview.secondaryMetric || ""
                        subtitleWrap: true
                        accentColor: theme.teal
                        headerBadgeText: root.planetaryOverview.label || ""
                        headerBadgeColor: root.planetaryOverview.state === "pending"
                                          ? theme.cyan
                                          : (root.planetaryOverview.state === "unavailable"
                                             ? theme.textMuted
                                             : theme.scoreColor(root.planetaryOverview.scoreValue))

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                text: root.planetaryOverview.primaryMetric || ""
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }

                            Text {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                text: root.planetaryOverview.hint || ""
                                color: theme.textMuted
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignRight
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }
                        }
                    }

                    GlassCard {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 160
                        title: qsTr("Condizioni del cielo profondo")
                        subtitle: root.deepSkyOverview.secondaryMetric || ""
                        subtitleWrap: true
                        accentColor: theme.violet
                        headerBadgeText: root.deepSkyOverview.label || ""
                        headerBadgeColor: root.deepSkyOverview.state === "pending"
                                          ? theme.cyan
                                          : (root.deepSkyOverview.state === "partial"
                                             ? theme.amber
                                             : (root.deepSkyOverview.state === "unavailable"
                                                ? theme.textMuted
                                                : theme.scoreColor(root.deepSkyOverview.scoreValue)))

                        RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                text: root.deepSkyOverview.primaryMetric || ""
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }

                            Text {
                                Layout.fillWidth: true
                                Layout.minimumWidth: 0
                                text: root.deepSkyOverview.hint || ""
                                color: theme.textMuted
                                font.pixelSize: 12
                                horizontalAlignment: Text.AlignRight
                                wrapMode: Text.WordWrap
                                elide: Text.ElideRight
                                maximumLineCount: 2
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.preferredWidth: topOverview.usableWidth / 3
                    Layout.maximumWidth: topOverview.usableWidth / 3
                    Layout.preferredHeight: 334
                    Layout.alignment: Qt.AlignTop
                    title: qsTr("Meteo osservativo")
                    subtitle: controller.weatherStatus.length > 0
                              ? controller.weatherStatus : (root.weatherOverview.windowText || "")
                    subtitleWrap: true
                    accentColor: root.weatherOverview.state === "pending"
                                 ? theme.cyan
                                 : (root.weatherOverview.available
                                    ? theme.scoreColor(root.weatherOverview.scoreValue)
                                    : theme.textMuted)
                    headerBadgeText: root.weatherOverview.badge || qsTr("n/d")
                    headerBadgeColor: root.weatherOverview.state === "pending" ? theme.cyan : accentColor

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
                                    text: qsTr("Nuvole (media)")
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.weatherOverview.available
                                          ? controller.weatherDigest.cloudAverageLabel : qsTr("n/d")
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
                                    text: qsTr("Vento (media)")
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.weatherOverview.available
                                          ? controller.weatherDigest.windLabel : qsTr("n/d")
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
                                    text: qsTr("Pioggia (max)")
                                    color: theme.textSecondary
                                    font.pixelSize: 10
                                    horizontalAlignment: Text.AlignHCenter
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.weatherOverview.available
                                          ? controller.weatherDigest.rainProbabilityLabel : qsTr("n/d")
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
                                        accentColor: theme.scoreColor(root.weatherOverview.scoreValue)
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
                                            text: modelData.cloudCoverLabel
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
                                            text: modelData.windLabel
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
                                            text: modelData.rainProbabilityLabel
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

                property var compassData: root.skyCompassOverview
                property bool wide: root.width > 1180
                property bool medium: root.width > 760
                property bool sessionRecommended: root.sessionOverview.state === "recommended"
                property string sessionCaution: compassData.cautionText
                                                || (sessionRecommended ? "" :
                                                    qsTr("Condizioni della sessione non confermate: usa la direzione solo come orientamento."))

                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                Layout.minimumHeight: skyCompassCard.compassData.available && wide ? 286 : 0
                title: qsTr("Sky Compass")
                subtitle: skyCompassCard.sessionRecommended
                          ? qsTr("Dove iniziare stasera") : qsTr("Orientamento del cielo")
                accentColor: theme.teal
                headerContent: [
                    RowLayout {
                        visible: skyCompassCard.compassData.available
                                 && (skyCompassCard.compassData.alternatives || []).length > 0
                        spacing: 8

                        Text {
                            text: skyCompassCard.sessionRecommended ? qsTr("Alternative") : qsTr("Altre direzioni")
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
                    text: skyCompassCard.compassData.message || qsTr("Nessun oggetto consigliato al momento.")
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

                                    property real selectedDegrees: root.skyCompassRotation(skyCompassCard.compassData.directionCode || "")

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
                                    text: qsTr("N")
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.right: parent.right
                                    anchors.rightMargin: 12
                                    text: qsTr("E")
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    anchors.horizontalCenter: parent.horizontalCenter
                                    anchors.bottom: parent.bottom
                                    anchors.bottomMargin: 10
                                    text: qsTr("S")
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                }

                                Text {
                                    anchors.verticalCenter: parent.verticalCenter
                                    anchors.left: parent.left
                                    anchors.leftMargin: 12
                                    text: qsTr("O")
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
                                    text: skyCompassCard.sessionRecommended ? qsTr("Inizia da") : qsTr("Guarda verso")
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
                                        text: skyCompassCard.sessionRecommended
                                              ? (skyCompassCard.compassData.zoneLabel || qsTr("Zona consigliata"))
                                              : qsTr("Zona con più oggetti")
                                        color: theme.teal
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: skyCompassCard.sessionRecommended
                                          ? (skyCompassCard.compassData.targetCountLabel || "")
                                          : root.skyCompassGeometricTargetCountLabel(
                                                skyCompassCard.compassData.targetCount)
                                    color: theme.textSecondary
                                    font.pixelSize: 13
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    visible: skyCompassCard.sessionCaution.length > 0
                                    text: skyCompassCard.sessionCaution
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
                            text: qsTr("Perché questa direzione?")
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
                                text: skyCompassCard.sessionRecommended
                                      ? qsTr("Oggetti principali") : qsTr("Oggetti nella direzione")
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

                                    property string iconKind: root.skyCompassTypeIconKind(modelData.typeCode)

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
                                        text: modelData.typeLabel || modelData.type
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

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 12

                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: qsTr("Piano della notte")
                    color: theme.textPrimary
                    font.pixelSize: 18
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                DarkButton {
                    id: skyCompassFilterButton
                    Layout.preferredWidth: 164
                    Layout.alignment: Qt.AlignRight | Qt.AlignVCenter
                    text: qsTr("Solo suggeriti ora")
                    enabled: root.skyCompassFilterAvailable
                    checkable: true
                    checked: root.skyCompassFilterEnabled
                    accentColor: theme.cyan
                    ToolTip.visible: hovered
                    ToolTip.text: root.skyCompassFilterAvailable
                                  ? qsTr("Mostra nelle due schede solo gli oggetti nella zona indicata da Sky Compass")
                                  : qsTr("Nessun oggetto osservabile in questo momento")
                    onClicked: root.setSkyCompassFilter(checked)
                }
            }

            GridLayout {
                id: centerGrid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 14
                rowSpacing: 14

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: centerGrid.columns > 1 ? 2 : 1
                    Layout.alignment: Qt.AlignTop
                    title: root.nightPlanOverview.title || qsTr("Piano osservativo")
                    subtitle: root.skyCompassFilterEnabled && root.nightPlanOverview.showsSequence
                              ? qsTr("Tappe del piano nella zona indicata da Sky Compass")
                              : (root.nightPlanOverview.subtitle || "")
                    subtitleWrap: true
                    headerBadgeText: root.nightPlanOverview.badge || ""
                    headerBadgeColor: root.planAccent(root.nightPlanOverview.state || "unavailable")
                    accentColor: root.planAccent(root.nightPlanOverview.state || "unavailable")

                    ColumnLayout {
                        Layout.fillWidth: true
                        visible: !root.nightPlanOverview.showsSequence
                        spacing: 12

                        Text {
                            Layout.fillWidth: true
                            visible: (root.nightPlanOverview.message || "").length > 0
                            text: root.nightPlanOverview.message || ""
                            color: root.planAccent(root.nightPlanOverview.state || "unavailable")
                            font.pixelSize: 15
                            font.weight: Font.DemiBold
                            wrapMode: Text.WordWrap
                        }

                        Text {
                            Layout.fillWidth: true
                            visible: (root.nightPlanOverview.supportingText || "").length > 0
                            text: root.nightPlanOverview.supportingText || ""
                            color: theme.textSecondary
                            font.pixelSize: 13
                            wrapMode: Text.WordWrap
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            visible: root.nightPlanOverview.showWindow
                            radius: 8
                            color: "#151a20"
                            border.color: Qt.rgba(root.planAccent(root.nightPlanOverview.state || "unavailable").r,
                                                  root.planAccent(root.nightPlanOverview.state || "unavailable").g,
                                                  root.planAccent(root.nightPlanOverview.state || "unavailable").b,
                                                  0.42)
                            border.width: 1
                            implicitHeight: windowLayout.implicitHeight + 18

                            ColumnLayout {
                                id: windowLayout
                                anchors.fill: parent
                                anchors.margins: 9
                                spacing: 3

                                Text {
                                    Layout.fillWidth: true
                                    text: root.nightPlanOverview.windowLabel || qsTr("Possibile finestra")
                                    color: theme.textMuted
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: root.nightPlanOverview.windowValue || ""
                                    color: theme.textPrimary
                                    font.pixelSize: 16
                                    font.weight: Font.DemiBold
                                    wrapMode: Text.WordWrap
                                }
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.nightPlanOverview.showsSequence
                                 && root.filteredNightPlanItems().length > 0
                        columns: root.width > 1180 ? 2 : 1
                        columnSpacing: 10
                        rowSpacing: 8

                        Repeater {
                            model: root.filteredNightPlanItems()

                            delegate: HomePlanStepRow {
                                itemData: modelData
                                assetBaseUrl: controller.assetBaseUrl
                                accentColor: theme.green
                                onOpenRequested: function(objectId) {
                                    root.openObject(objectId)
                                }
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.skyCompassFilterEnabled
                                 && root.nightPlanOverview.showsSequence
                                 && root.filteredNightPlanItems().length === 0
                        text: qsTr("Nessuna tappa del piano nella zona suggerita in questo momento.")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: centerGrid.columns > 1 ? 2 : 1
                    Layout.alignment: Qt.AlignTop
                    title: root.nightAlternativesOverview.title || qsTr("Altri oggetti visibili stasera")
                    subtitle: root.skyCompassFilterEnabled
                              ? qsTr("Oggetti nella zona indicata da Sky Compass; filtra ulteriormente per categoria")
                              : (root.nightAlternativesOverview.subtitle || "")
                    subtitleWrap: true
                    headerBadgeText: root.alternativeCount("all") > 0
                                     ? root.alternativeCountLabel(root.alternativeCount("all"))
                                     : ""
                    headerBadgeColor: theme.cyan
                    accentColor: theme.cyan

                    GridLayout {
                        Layout.fillWidth: true
                        visible: root.alternativeCount("all") > 0
                        columns: root.width > 620 ? 3 : 1
                        columnSpacing: 6
                        rowSpacing: 6

                        Repeater {
                            model: [
                                {"key": "all"},
                                {"key": "planet"},
                                {"key": "deep_sky"}
                            ]

                            delegate: Rectangle {
                                Layout.fillWidth: true
                                Layout.preferredHeight: 34
                                radius: 8
                                color: root.targetFilter === modelData.key ? Qt.rgba(theme.cyan.r, theme.cyan.g, theme.cyan.b, 0.16) : "#151a20"
                                border.color: root.targetFilter === modelData.key ? Qt.rgba(theme.cyan.r, theme.cyan.g, theme.cyan.b, 0.55) : theme.border
                                border.width: 1

                                Text {
                                    anchors.centerIn: parent
                                    width: parent.width - 18
                                    text: root.alternativeFilterLabel(modelData.key)
                                    color: root.targetFilter === modelData.key ? theme.cyan : theme.textSecondary
                                    font.pixelSize: 12
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    maximumLineCount: 1
                                    elide: Text.ElideRight
                                }

                                MouseArea {
                                    anchors.fill: parent
                                    cursorShape: Qt.PointingHandCursor
                                    onClicked: root.targetFilter = modelData.key
                                }
                            }
                        }
                    }

                    HomeVisibleTargetRow {
                        Layout.fillWidth: true
                        visible: root.width > 900 && root.filteredNightAlternatives().length > 0
                        headerMode: true
                        itemData: ({
                            "name": qsTr("Oggetto"),
                            "typeLabel": qsTr("Tipo"),
                            "windowLabel": qsTr("Finestra"),
                            "direction": qsTr("Direzione"),
                            "difficulty": qsTr("Difficoltà")
                        })
                    }

                    ListView {
                        id: visibleTargetList
                        Layout.fillWidth: true
                        Layout.preferredHeight: Math.min(
                                                    Math.max(contentHeight, root.width > 900 ? 46 : 82),
                                                    root.width > 900 ? 322 : 410)
                        visible: root.filteredNightAlternatives().length > 0
                        clip: true
                        model: root.filteredNightAlternatives()
                        spacing: 2
                        boundsBehavior: Flickable.StopAtBounds
                        interactive: contentHeight > height

                        WheelHandler {
                            enabled: visibleTargetList.interactive
                            target: null
                            orientation: Qt.Vertical
                            acceptedDevices: PointerDevice.Mouse | PointerDevice.TouchPad
                            blocking: true

                            onWheel: function(event) {
                                var delta = event.pixelDelta.y
                                if (delta === 0)
                                    delta = event.angleDelta.y / 2
                                var minimumY = visibleTargetList.originY
                                var maximumY = Math.max(
                                            minimumY,
                                            minimumY + visibleTargetList.contentHeight - visibleTargetList.height)
                                visibleTargetList.cancelFlick()
                                visibleTargetList.contentY = Math.max(
                                            minimumY,
                                            Math.min(maximumY, visibleTargetList.contentY - delta))
                                event.accepted = true
                            }
                        }

                        delegate: HomeVisibleTargetRow {
                            width: visibleTargetList.width
                            compact: root.width <= 900
                            itemData: modelData
                            onOpenRequested: function(objectId) {
                                root.openObject(objectId)
                            }
                        }

                        ScrollBar.vertical: ScrollBar {
                            policy: visibleTargetList.contentHeight > visibleTargetList.height
                                    ? ScrollBar.AsNeeded
                                    : ScrollBar.AlwaysOff
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: root.filteredNightAlternatives().length === 0
                        text: !controller.hasValidLocation
                              ? qsTr("Oggetti non disponibili senza località.")
                              : root.skyCompassFilterEnabled
                              ? qsTr("Nessun altro oggetto fuori dal piano nella zona suggerita in questo momento.")
                              : (root.nightAlternativesOverview.emptyText || qsTr("Nessun altro oggetto utile fuori dal piano."))
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
                Layout.alignment: Qt.AlignTop
                title: qsTr("Prossimi eventi")
                subtitle: qsTr("Ordinati per data")
                accentColor: theme.amber
                headerActionText: qsTr("Vedi tutti")
                headerActionAccentColor: theme.amber
                onHeaderActionClicked: root.openCalendar()

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1040 ? 4 : root.width > 760 ? 2 : 1
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: root.chronologicalEvents(root.width > 900 ? 8 : 4)

                        delegate: Rectangle {
                            property bool hovered: false

                            Layout.fillWidth: true
                            Layout.preferredHeight: 108
                            radius: 8
                            color: hovered ? "#1b222a" : "#151a20"
                            border.color: hovered ? root.eventAccent(modelData.typeCode) : "#29313b"
                            border.width: 1

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onEntered: parent.hovered = true
                                onExited: parent.hovered = false
                                onClicked: root.openEvent(modelData.id)
                            }

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                StatusPill {
                                    text: modelData.dateLabel
                                    accentColor: root.eventAccent(modelData.typeCode)
                                    Layout.alignment: Qt.AlignVCenter
                                }

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    Layout.minimumWidth: 0
                                    spacing: 2

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.title
                                        color: theme.textPrimary
                                        font.pixelSize: 14
                                        font.weight: Font.DemiBold
                                        wrapMode: Text.WordWrap
                                        maximumLineCount: 2
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.timingValue + "  -  " + modelData.visibilityLabel
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
                    text: controller.hasValidLocation
                          ? qsTr("Nessun evento imminente disponibile.")
                          : qsTr("Eventi non disponibili senza località.")
                    color: theme.textSecondary
                    font.pixelSize: 13
                }
            }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

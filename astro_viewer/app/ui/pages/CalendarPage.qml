import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property string selectedDateFilter: "30 giorni"
    property string selectedTypeFilter: "Tutti"
    property string selectedEventId: ""
    property string initialEventId: ""
    readonly property var calendarOverview: controller ? (controller.calendarOverview || ({})) : ({})
    readonly property var calendarEvents: calendarOverview.items || []
    property var selectedEventData: selectedEventById(selectedEventId)

    signal openObject(string objectId)
    signal eventSelected(string eventId)
    signal eventSelectionCleared()

    AppTheme {
        id: theme
    }

    function eventAccent(type) {
        if (type === "Luna")
            return theme.amber
        if (type === "Sciame meteorico")
            return theme.teal
        if (type === "Eclissi")
            return theme.coral
        if (type === "Congiunzione" || type === "Congiunzione planetaria")
            return theme.violet
        if (type === "Congiunzione solare")
            return theme.coral
        return theme.cyan
    }

    function visibilityAccent(state) {
        if (state === "visible" || state === "favorable" || state === "nearby_night")
            return theme.teal
        if (state === "check" || state === "unknown")
            return theme.amber
        return theme.coral
    }

    function matchesDateFilter(eventData) {
        var days = Number(eventData.daysUntil)
        if (days < 0)
            return false
        if (selectedDateFilter === "30 giorni")
            return days <= 30
        if (selectedDateFilter === "6 mesi")
            return days <= 183
        if (selectedDateFilter === "12 mesi")
            return days <= 365
        return true
    }

    function matchesTypeFilter(eventData) {
        return selectedTypeFilter === "Tutti" || eventData.type === selectedTypeFilter
    }

    function filteredEvents() {
        var result = []
        for (var index = 0; index < root.calendarEvents.length; index += 1) {
            var item = root.calendarEvents[index]
            if (matchesDateFilter(item) && matchesTypeFilter(item))
                result.push(item)
        }
        return result
    }

    function periodEvents() {
        var result = []
        for (var index = 0; index < root.calendarEvents.length; index += 1) {
            if (matchesDateFilter(root.calendarEvents[index]))
                result.push(root.calendarEvents[index])
        }
        return result
    }

    function countEvents(type) {
        var total = 0
        var events = periodEvents()
        for (var index = 0; index < events.length; index += 1) {
            if (type === "Tutti" || events[index].type === type)
                total += 1
        }
        return total
    }

    function nextEventLabel() {
        var events = filteredEvents()
        if (events.length === 0)
            return "-"
        return events[0].dateLabel
    }

    function hasSelectedEvent() {
        return selectedEventData && selectedEventData.title !== undefined && selectedEventData.title !== ""
    }

    function selectedEventById(eventId) {
        if (!eventId)
            return null
        for (var index = 0; index < root.calendarEvents.length; index += 1) {
            if (root.calendarEvents[index].id === eventId)
                return root.calendarEvents[index]
        }
        return null
    }

    function showEvent(eventId) {
        root.selectedEventId = eventId
        root.eventSelected(eventId)
    }

    Component.onCompleted: {
        if (root.initialEventId.length > 0)
            root.showEvent(root.initialEventId)
    }

    onInitialEventIdChanged: {
        if (root.initialEventId.length > 0)
            root.showEvent(root.initialEventId)
    }

    EventDetailPage {
        anchors.fill: parent
        visible: root.hasSelectedEvent()
        controller: root.controller
        eventData: root.selectedEventData
        accentColor: root.hasSelectedEvent() ? root.eventAccent(root.selectedEventData.type) : theme.cyan
        onBackToCalendar: {
            root.selectedEventId = ""
            root.eventSelectionCleared()
        }
        onOpenObject: function(objectId) {
            root.openObject(objectId)
        }
    }

    ScrollView {
        id: scroll
        visible: !root.hasSelectedEvent()
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
                        text: qsTr("Calendario astronomico")
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Opposizioni, congiunzioni, Luna, eclissi e sciami meteorici")
                        color: theme.textSecondary
                        font.pixelSize: 14
                        elide: Text.ElideRight
                    }
                }
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: scroll.availableWidth >= 1180 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 212
                    title: qsTr("In evidenza nei prossimi 30 giorni")
                    subtitle: qsTr("Eventi osservativi da controllare per primi")
                    accentColor: theme.amber

                    Text {
                        Layout.fillWidth: true
                        visible: (root.calendarOverview.highlights || []).length === 0
                        text: qsTr("Nessun evento rilevante nei prossimi 30 giorni.")
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: root.calendarOverview.highlights || []

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 12

                            StatusPill {
                                text: modelData.dateLabel
                                accentColor: root.eventAccent(modelData.type)
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

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
                                    text: modelData.timingValue + "  -  " + modelData.visibilityLabel
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.minimumHeight: 212
                    title: qsTr("Panoramica")
                    subtitle: root.filteredEvents().length + qsTr(" eventi nella vista corrente")
                    accentColor: theme.cyan

                    GridLayout {
                        Layout.fillWidth: true
                        columns: scroll.availableWidth >= 1420 ? 4 : 2
                        columnSpacing: 10
                        rowSpacing: 10

                        MetricTile {
                            label: qsTr("Prossimo")
                            value: root.nextEventLabel()
                            accentColor: theme.amber
                        }

                        MetricTile {
                            label: qsTr("Luna")
                            value: root.countEvents("Luna").toString()
                            accentColor: theme.amber
                        }

                        MetricTile {
                            label: qsTr("Opposizioni")
                            value: root.countEvents("Opposizione").toString()
                            accentColor: theme.cyan
                        }

                        MetricTile {
                            label: qsTr("Cong. planetarie")
                            value: root.countEvents("Congiunzione planetaria").toString()
                            accentColor: theme.violet
                        }

                        MetricTile {
                            label: qsTr("Cong. solari")
                            value: root.countEvents("Congiunzione solare").toString()
                            accentColor: theme.coral
                        }

                        MetricTile {
                            label: qsTr("Sciami")
                            value: root.countEvents("Sciame meteorico").toString()
                            accentColor: theme.teal
                        }

                        MetricTile {
                            label: qsTr("Eclissi")
                            value: root.countEvents("Eclissi").toString()
                            accentColor: theme.coral
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Vista calendario")
                subtitle: root.filteredEvents().length + qsTr(" di ") + root.calendarEvents.length + qsTr(" eventi")
                accentColor: theme.violet

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Periodo")
                        color: theme.textSecondary
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Flow {
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        spacing: 8

                        Repeater {
                            model: [
                                { "label": qsTr("30 giorni"), "value": "30 giorni" },
                                { "label": qsTr("6 mesi"), "value": "6 mesi" },
                                { "label": qsTr("12 mesi"), "value": "12 mesi" }
                            ]

                            delegate: DarkButton {
                                text: modelData.label
                                checkable: true
                                checked: root.selectedDateFilter === modelData.value
                                accentColor: theme.violet
                                onClicked: root.selectedDateFilter = modelData.value
                            }
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Tipo evento")
                        color: theme.textSecondary
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                    }

                    Flow {
                        Layout.fillWidth: true
                        Layout.preferredHeight: implicitHeight
                        spacing: 8

                        Repeater {
                            model: [
                                { "label": qsTr("Tutti"), "value": "Tutti" },
                                { "label": qsTr("Luna"), "value": "Luna" },
                                { "label": qsTr("Opposizioni"), "value": "Opposizione" },
                                { "label": qsTr("Cong. planetarie"), "value": "Congiunzione planetaria" },
                                { "label": qsTr("Cong. solari"), "value": "Congiunzione solare" },
                                { "label": qsTr("Sciami"), "value": "Sciame meteorico" },
                                { "label": qsTr("Eclissi"), "value": "Eclissi" }
                            ]

                            delegate: DarkButton {
                                text: modelData.label
                                checkable: true
                                checked: root.selectedTypeFilter === modelData.value
                                accentColor: root.eventAccent(modelData.value)
                                onClicked: root.selectedTypeFilter = modelData.value
                            }
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
                    text: qsTr("Timeline eventi")
                    color: theme.textPrimary
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                StatusPill {
                    text: root.filteredEvents().length + qsTr(" eventi")
                    accentColor: theme.cyan
                }
            }

            GridLayout {
                id: eventGrid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: scroll.availableWidth >= 1320 ? 2 : 1
                columnSpacing: 12
                rowSpacing: 12

                Repeater {
                    model: root.filteredEvents()

                    delegate: EventRow {
                        Layout.fillWidth: true
                        Layout.preferredWidth: (eventGrid.width - eventGrid.columnSpacing * (eventGrid.columns - 1)) / eventGrid.columns
                        eventData: modelData
                        accentColor: root.eventAccent(modelData.type)
                        visibilityAccentColor: root.visibilityAccent(modelData.visibilityState)
                        onClicked: root.showEvent(modelData.id)
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                visible: root.filteredEvents().length === 0
                text: qsTr("Nessun evento per i filtri selezionati.")
                color: theme.textSecondary
                font.pixelSize: 13
                horizontalAlignment: Text.AlignHCenter
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window
import "components"
import "pages"

ApplicationWindow {
    id: window

    width: 1240
    height: 820
    minimumWidth: 1040
    minimumHeight: 700
    visibility: Window.Maximized
    title: qsTr("NightScope")
    color: theme.background
    palette.window: theme.background
    palette.windowText: theme.textPrimary
    palette.base: theme.surfaceRaised
    palette.alternateBase: theme.surface
    palette.text: theme.textPrimary
    palette.placeholderText: theme.textMuted
    palette.button: theme.surfaceRaised
    palette.buttonText: theme.textPrimary
    palette.highlight: theme.cyan
    palette.highlightedText: theme.background

    property string currentPage: "home"
    property string detailBackTarget: "home"
    property string calendarEventId: ""
    property var observingOverview: appController.homeObservingOverview || ({})
    property var sidebarSession: observingOverview.session || ({})

    function sidebarSessionAccent(state) {
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

    AppTheme {
        id: theme
    }

    Rectangle {
        anchors.fill: parent
        color: theme.background

        Canvas {
            anchors.fill: parent
            opacity: 0.32
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.fillStyle = "#f4f7fb"
                for (var i = 0; i < 120; i++) {
                    var x = (i * 97) % width
                    var y = (i * 53) % height
                    var size = (i % 5 === 0) ? 1.8 : 1
                    ctx.globalAlpha = (i % 7 === 0) ? 0.75 : 0.32
                    ctx.fillRect(x, y, size, size)
                }
                ctx.globalAlpha = 1
            }
        }
    }

    RowLayout {
        anchors.fill: parent
        spacing: 0

        Rectangle {
            Layout.preferredWidth: 266
            Layout.fillHeight: true
            color: "#12151a"
            border.color: "#252b34"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                anchors.margins: 14
                spacing: 12

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 12

                    Rectangle {
                        Layout.preferredWidth: 42
                        Layout.preferredHeight: 42
                        radius: 8
                        color: "#20242b"
                        border.color: theme.cyan
                        border.width: 1

                        Image {
                            anchors.centerIn: parent
                            width: 26
                            height: 26
                            source: appController.assetBaseUrl + "/resources/icons/telescope.svg"
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2

                        Text {
                            Layout.fillWidth: true
                            text: qsTr("NightScope")
                            color: theme.textPrimary
                            font.pixelSize: 22
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: appController.location.city + (appController.location.country ? ", " + appController.location.country : "")
                            color: theme.textSecondary
                            font.pixelSize: 12
                            elide: Text.ElideRight
                        }
                    }
                }

                ScrollView {
                    id: sidebarNavigation
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    contentWidth: availableWidth
                    ScrollBar.horizontal.policy: ScrollBar.AlwaysOff

                    ColumnLayout {
                        width: sidebarNavigation.availableWidth
                        spacing: 4

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Home")
                        iconSource: appController.assetBaseUrl + "/resources/icons/home.svg"
                        selected: window.currentPage === "home" || (window.currentPage === "detail" && window.detailBackTarget === "home")
                        onClicked: window.currentPage = "home"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Calendario")
                        iconSource: appController.assetBaseUrl + "/resources/icons/calendar.svg"
                        selected: window.currentPage === "calendar" || (window.currentPage === "detail" && window.detailBackTarget === "calendar")
                        onClicked: {
                            window.calendarEventId = ""
                            window.currentPage = "calendar"
                        }
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Log Osservazioni")
                        iconSource: appController.assetBaseUrl + "/resources/icons/target.svg"
                        selected: window.currentPage === "observationLog"
                        onClicked: window.currentPage = "observationLog"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Meteo")
                        iconSource: appController.assetBaseUrl + "/resources/icons/cloud.svg"
                        selected: window.currentPage === "weather"
                        onClicked: window.currentPage = "weather"
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        text: qsTr("Configurazione")
                        color: theme.textMuted
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Località")
                        iconSource: appController.assetBaseUrl + "/resources/icons/location.svg"
                        selected: window.currentPage === "location"
                        onClicked: window.currentPage = "location"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Provider dati")
                        iconSource: appController.assetBaseUrl + "/resources/icons/cloud.svg"
                        selected: window.currentPage === "dataProviders"
                        onClicked: window.currentPage = "dataProviders"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Profili")
                        iconSource: appController.assetBaseUrl + "/resources/icons/equipment.svg"
                        selected: window.currentPage === "equipmentProfiles"
                        onClicked: window.currentPage = "equipmentProfiles"
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.topMargin: 4
                        text: qsTr("Cataloghi")
                        color: theme.textMuted
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Oggetti celesti")
                        iconSource: appController.assetBaseUrl + "/resources/icons/target.svg"
                        selected: window.currentPage === "objectCatalogue" || (window.currentPage === "detail" && window.detailBackTarget === "objectCatalogue")
                        onClicked: window.currentPage = "objectCatalogue"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Telescopi")
                        iconSource: appController.assetBaseUrl + "/resources/icons/telescope.svg"
                        selected: window.currentPage === "equipmentTelescopes"
                        onClicked: window.currentPage = "equipmentTelescopes"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Oculari e Barlow")
                        iconSource: appController.assetBaseUrl + "/resources/icons/equipment.svg"
                        selected: window.currentPage === "equipmentOptics"
                        onClicked: window.currentPage = "equipmentOptics"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: qsTr("Filtri e riduttori")
                        iconSource: appController.assetBaseUrl + "/resources/icons/equipment.svg"
                        selected: window.currentPage === "equipmentFiltersReducers"
                        onClicked: window.currentPage = "equipmentFiltersReducers"
                    }

                        NavButton {
                            Layout.fillWidth: true
                            text: qsTr("Binocoli")
                            iconSource: appController.assetBaseUrl + "/resources/icons/target.svg"
                            selected: window.currentPage === "equipmentBinoculars"
                            onClicked: window.currentPage = "equipmentBinoculars"
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Lingua")
                        color: theme.textSecondary
                        font.pixelSize: 12
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    DarkComboBox {
                        id: languageSelector
                        Layout.preferredWidth: 128
                        model: translationManager.languageOptions
                        textRole: "label"
                        valueRole: "code"
                        currentIndex: {
                            var options = translationManager.languageOptions
                            for (var index = 0; index < options.length; index += 1) {
                                if (options[index].code === translationManager.languageCode)
                                    return index
                            }
                            return 0
                        }
                        onActivated: function(index) {
                            translationManager.setLanguage(model[index].code)
                        }
                    }
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: 8
                    color: "#171a20"
                    border.color: "#303641"
                    border.width: 1
                    implicitHeight: 112

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 10
                        spacing: 4

                        RowLayout {
                            Layout.fillWidth: true

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("Stasera")
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            StatusPill {
                                text: window.sidebarSession.badge || qsTr("Da valutare")
                                accentColor: window.sidebarSessionAccent(window.sidebarSession.state || "unavailable")
                            }
                        }

                        Text {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            text: window.sidebarSession.windowText || qsTr("Finestra osservativa non disponibile")
                            color: theme.textPrimary
                            font.pixelSize: 12
                            font.weight: Font.DemiBold
                            wrapMode: Text.WordWrap
                            maximumLineCount: 2
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            Layout.minimumWidth: 0
                            text: window.sidebarSession.limitingFactor || qsTr("Condizioni della sessione non valutabili")
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

        Loader {
            id: pageLoader
            Layout.fillWidth: true
            Layout.fillHeight: true
            sourceComponent: {
                if (window.currentPage === "detail") return detailPage
                if (window.currentPage === "calendar") return calendarPage
                if (window.currentPage === "observationLog") return observationLogPage
                if (window.currentPage === "weather") return weatherPage
                if (window.currentPage === "location") return locationPage
                if (window.currentPage === "dataProviders") return dataProvidersPage
                if (window.currentPage === "equipmentProfiles") return equipmentProfilesPage
                if (window.currentPage === "objectCatalogue") return objectCataloguePage
                if (window.currentPage === "equipmentTelescopes") return equipmentTelescopesPage
                if (window.currentPage === "equipmentOptics") return equipmentOpticsPage
                if (window.currentPage === "equipmentFiltersReducers") return equipmentFiltersReducersPage
                if (window.currentPage === "equipmentBinoculars") return equipmentBinocularsPage
                return homePage
            }
        }
    }

    Component {
        id: homePage
        HomePage {
            controller: appController
            onOpenObject: function(objectId) {
                appController.selectObject(objectId)
                window.detailBackTarget = "home"
                window.currentPage = "detail"
            }
            onOpenEvent: function(eventId) {
                window.calendarEventId = eventId
                window.currentPage = "calendar"
            }
            onOpenCalendar: {
                window.calendarEventId = ""
                window.currentPage = "calendar"
            }
        }
    }

    Component {
        id: detailPage
        ObjectDetailPage {
            controller: appController
            backLabel: window.detailBackTarget === "objectCatalogue" ? qsTr("Torna al catalogo")
                : window.detailBackTarget === "calendar" ? qsTr("Torna al calendario")
                : qsTr("Torna alla Home")
            onBackToHome: window.currentPage = window.detailBackTarget
        }
    }

    Component {
        id: objectCataloguePage
        ObjectCataloguePage {
            controller: appController
            onOpenObject: function(objectId) {
                appController.selectCatalogueObject(objectId)
                window.detailBackTarget = "objectCatalogue"
                window.currentPage = "detail"
            }
        }
    }

    Component {
        id: calendarPage
        CalendarPage {
            controller: appController
            initialEventId: window.calendarEventId
            onEventSelected: function(eventId) {
                window.calendarEventId = eventId
            }
            onEventSelectionCleared: window.calendarEventId = ""
            onOpenObject: function(objectId) {
                appController.selectObject(objectId)
                window.detailBackTarget = "calendar"
                window.currentPage = "detail"
            }
        }
    }

    Component {
        id: observationLogPage
        ObservationLogPage {
            controller: appController
        }
    }

    Component {
        id: weatherPage
        WeatherPage {
            controller: appController
        }
    }

    Component {
        id: locationPage
        LocationPage {
            controller: appController
        }
    }

    Component {
        id: dataProvidersPage
        DataProvidersPage {
            controller: appController
        }
    }

    Component {
        id: equipmentProfilesPage
        EquipmentProfilesPage {
            controller: appController
        }
    }

    Component {
        id: equipmentTelescopesPage
        EquipmentTelescopesPage {
            controller: appController
        }
    }

    Component {
        id: equipmentOpticsPage
        EquipmentOpticsPage {
            controller: appController
        }
    }

    Component {
        id: equipmentFiltersReducersPage
        EquipmentFiltersReducersPage {
            controller: appController
        }
    }

    Component {
        id: equipmentBinocularsPage
        EquipmentBinocularsPage {
            controller: appController
        }
    }
}

// Purpose: Own the application window, navigation shell, and page/dialog composition.
// Contract: Consumes injected context objects and routes UI events; domain decisions stay in Python.

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
            return theme.green
        if (state === "monitor")
            return theme.amber
        if (state === "discouraged")
            return theme.coral
        if (state === "unavailable")
            return theme.textMuted
        return theme.teal
    }

    AppTheme {
        id: theme
    }

    Connections {
        target: updateManager

        function onUpdateAvailable() {
            ignoreUpdateCheck.checked = false
            updateAvailableDialog.open()
        }
    }

    DarkDialog {
        id: updateAvailableDialog
        objectName: "updateAvailableDialog"
        parent: Overlay.overlay
        title: qsTr("Nuova versione disponibile")
        acceptText: qsTr("Scarica aggiornamento")
        cancelText: qsTr("Più tardi")
        preferredWidth: 560

        onAccepted: Qt.openUrlExternally(updateManager.releaseUrl)
        onClosed: {
            if (ignoreUpdateCheck.checked)
                updateManager.ignoreCurrentUpdate()
        }

        Text {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            text: qsTr("È disponibile NightScope %1. Stai utilizzando la versione %2.")
                .arg(updateManager.latestVersion)
                .arg(updateManager.currentVersion)
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }

        DarkCheckBox {
            id: ignoreUpdateCheck
            Layout.fillWidth: true
            text: qsTr("Non mostrare più questa versione")
        }
    }

    Rectangle {
        anchors.fill: parent
        color: theme.background

        Canvas {
            id: starField
            anchors.fill: parent
            opacity: theme.redNightVision ? 0.16 : 0.32
            property bool redNightVision: theme.redNightVision
            onRedNightVisionChanged: requestPaint()
            onPaint: {
                var ctx = getContext("2d")
                ctx.clearRect(0, 0, width, height)
                ctx.fillStyle = theme.textPrimary
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
            color: theme.sidebar
            border.color: theme.sidebarBorder
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
                        color: theme.surfaceRaised
                        border.color: theme.cyan
                        border.width: 1

                        NightVisionIcon {
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

                    DarkButton {
                        id: manualButton
                        Layout.preferredWidth: 38
                        Layout.preferredHeight: 38
                        leftPadding: 0
                        rightPadding: 0
                        text: qsTr("?")
                        Accessible.name: qsTr("Apri manuale")
                        ToolTip.visible: hovered
                        ToolTip.text: qsTr("Apri manuale")
                        onClicked: Qt.openUrlExternally(
                            appController.manualUrl + "?lang=" + translationManager.languageCode
                        )
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
                        text: qsTr("Cameras")
                        iconSource: appController.assetBaseUrl + "/resources/icons/equipment.svg"
                        selected: window.currentPage === "equipmentCameras"
                        onClicked: window.currentPage = "equipmentCameras"
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
                    color: theme.surface
                    border.color: theme.border
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

                Rectangle {
                    Layout.fillWidth: true
                    implicitHeight: 40
                    radius: 8
                    color: theme.surface
                    border.color: theme.border
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.margins: 3
                        spacing: 3

                        Button {
                            id: normalModeButton
                            objectName: "normalModeButton"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: qsTr("Normale")
                            Accessible.name: qsTr("Normale")
                            Accessible.role: Accessible.RadioButton
                            Accessible.checked: !theme.redNightVision
                            onClicked: appearanceManager.setRedNightVisionEnabled(false)

                            contentItem: Text {
                                text: parent.text
                                color: theme.redNightVision ? theme.textSecondary : theme.textPrimary
                                font.pixelSize: 11
                                font.weight: theme.redNightVision ? Font.Normal : Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }

                            background: Rectangle {
                                radius: 6
                                color: !theme.redNightVision
                                       ? theme.navSelected
                                       : parent.hovered ? theme.navHover : "transparent"
                                border.color: !theme.redNightVision
                                              ? theme.navSelectedBorder : "transparent"
                                border.width: 1
                            }
                        }

                        Button {
                            id: redNightVisionButton
                            objectName: "redNightVisionButton"
                            Layout.fillWidth: true
                            Layout.fillHeight: true
                            text: qsTr("Visione rossa")
                            Accessible.name: qsTr("Visione rossa")
                            Accessible.role: Accessible.RadioButton
                            Accessible.checked: theme.redNightVision
                            onClicked: appearanceManager.setRedNightVisionEnabled(true)

                            contentItem: Text {
                                text: parent.text
                                color: theme.redNightVision ? theme.textPrimary : theme.textSecondary
                                font.pixelSize: 11
                                font.weight: theme.redNightVision ? Font.DemiBold : Font.Normal
                                horizontalAlignment: Text.AlignHCenter
                                verticalAlignment: Text.AlignVCenter
                                elide: Text.ElideRight
                            }

                            background: Rectangle {
                                radius: 6
                                color: theme.redNightVision
                                       ? theme.navSelected
                                       : parent.hovered ? theme.navHover : "transparent"
                                border.color: theme.redNightVision
                                              ? theme.navSelectedBorder : "transparent"
                                border.width: 1
                            }
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
                if (window.currentPage === "equipmentCameras") return equipmentCamerasPage
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
            onOpenLocation: window.currentPage = "location"
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
            onOpenObject: function(objectId, catalogue, designation) {
                appController.selectCatalogueDesignation(
                    objectId,
                    catalogue,
                    designation
                )
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
            onOpenLocation: window.currentPage = "location"
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
            onOpenLocation: window.currentPage = "location"
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
        id: equipmentCamerasPage
        EquipmentCamerasPage {
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

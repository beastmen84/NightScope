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
    title: "NightScope"
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
                anchors.margins: 18
                spacing: 18

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
                            text: "NightScope"
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

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 8

                    NavButton {
                        Layout.fillWidth: true
                        text: "Home"
                        iconSource: appController.assetBaseUrl + "/resources/icons/home.svg"
                        selected: window.currentPage === "home" || window.currentPage === "detail"
                        onClicked: window.currentPage = "home"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: "Calendario"
                        iconSource: appController.assetBaseUrl + "/resources/icons/calendar.svg"
                        selected: window.currentPage === "calendar"
                        onClicked: window.currentPage = "calendar"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: "Meteo"
                        iconSource: appController.assetBaseUrl + "/resources/icons/cloud.svg"
                        selected: window.currentPage === "weather"
                        onClicked: window.currentPage = "weather"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: "Località"
                        iconSource: appController.assetBaseUrl + "/resources/icons/location.svg"
                        selected: window.currentPage === "location"
                        onClicked: window.currentPage = "location"
                    }

                    Text {
                        Layout.fillWidth: true
                        Layout.topMargin: 8
                        text: "Strumenti"
                        color: theme.textMuted
                        font.pixelSize: 11
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: "Profili"
                        iconSource: appController.assetBaseUrl + "/resources/icons/equipment.svg"
                        selected: window.currentPage === "equipmentProfiles"
                        onClicked: window.currentPage = "equipmentProfiles"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: "Telescopi"
                        iconSource: appController.assetBaseUrl + "/resources/icons/telescope.svg"
                        selected: window.currentPage === "equipmentTelescopes"
                        onClicked: window.currentPage = "equipmentTelescopes"
                    }

                    NavButton {
                        Layout.fillWidth: true
                        text: "Oculari e Barlow"
                        iconSource: appController.assetBaseUrl + "/resources/icons/equipment.svg"
                        selected: window.currentPage === "equipmentOptics"
                        onClicked: window.currentPage = "equipmentOptics"
                    }
                }

                Item {
                    Layout.fillHeight: true
                }

                Rectangle {
                    Layout.fillWidth: true
                    radius: 8
                    color: "#171a20"
                    border.color: "#303641"
                    border.width: 1
                    implicitHeight: 126

                    ColumnLayout {
                        anchors.fill: parent
                        anchors.margins: 14
                        spacing: 8

                        Text {
                            Layout.fillWidth: true
                            text: appController.weatherSummary.score
                            color: theme.scoreColor(appController.weatherSummary.score)
                            font.pixelSize: 20
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        Text {
                            Layout.fillWidth: true
                            text: appController.weatherSummary.alert
                            color: theme.textSecondary
                            wrapMode: Text.WordWrap
                            maximumLineCount: 3
                            elide: Text.ElideRight
                            font.pixelSize: 12
                        }

                        Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 6
                            radius: 3
                            color: "#252b34"

                            Rectangle {
                                width: parent.width * (appController.weatherSummary.scoreValue / 100)
                                height: parent.height
                                radius: 3
                                color: theme.scoreColor(appController.weatherSummary.score)
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
                if (window.currentPage === "weather") return weatherPage
                if (window.currentPage === "location") return locationPage
                if (window.currentPage === "equipmentProfiles") return equipmentProfilesPage
                if (window.currentPage === "equipmentTelescopes") return equipmentTelescopesPage
                if (window.currentPage === "equipmentOptics") return equipmentOpticsPage
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
                window.currentPage = "detail"
            }
        }
    }

    Component {
        id: detailPage
        ObjectDetailPage {
            controller: appController
            onBackToHome: window.currentPage = "home"
        }
    }

    Component {
        id: calendarPage
        CalendarPage {
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
}

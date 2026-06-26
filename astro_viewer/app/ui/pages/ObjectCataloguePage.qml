import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property string allFilter: "Tutti"
    signal openObject(string objectId)

    function optionModel(key) {
        var options = controller.catalogueFilterOptions || {}
        var source = options[key] || []
        var result = [root.allFilter]
        for (var i = 0; i < source.length; i++)
            result.push(String(source[i]))
        return result
    }

    function magnitudeText(item) {
        if (item.magnitude_label !== undefined && item.magnitude_label !== "")
            return item.magnitude_label
        if (item.magnitude === null || item.magnitude === undefined)
            return "—"
        if (String(item.magnitude) === "")
            return "—"
        return String(item.magnitude)
    }

    function sizeText(item) {
        if (item.max_angular_size_label !== undefined && item.max_angular_size_label !== "")
            return item.max_angular_size_label
        if (item.max_angular_size_deg === null || item.max_angular_size_deg === undefined)
            return "—"
        return String(item.max_angular_size_deg) + " deg"
    }

    function textOrDash(value) {
        if (value === null || value === undefined || String(value) === "")
            return "—"
        return String(value)
    }

    function visibleText(item) {
        if (item.visible_this_month_label !== undefined && item.visible_this_month_label !== "")
            return item.visible_this_month_label
        return item.visible_this_month === true ? "Sì" : "—"
    }

    function observableText(item) {
        if (item.observable_label !== undefined && item.observable_label !== "")
            return item.observable_label
        return item.observable === true ? "Sì" : "—"
    }

    function clearFilters() {
        searchField.text = ""
        catalogueFilter.currentIndex = 0
        typeFilter.currentIndex = 0
        constellationFilter.currentIndex = 0
        observationTypeFilter.currentIndex = 0
        controller.clearCatalogueFilters()
    }

    AppTheme { id: theme }

    ScrollView {
        id: scroll
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
                spacing: 14

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Text {
                        Layout.fillWidth: true
                        text: "Oggetti celesti"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: "Esplora gli oggetti astronomici disponibili nel catalogo."
                        color: theme.textSecondary
                        font.pixelSize: 14
                        wrapMode: Text.WordWrap
                    }
                }

            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: ""
                subtitle: ""
                accentColor: theme.cyan

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1280 ? 7 : root.width > 880 ? 3 : 2
                    columnSpacing: 10
                    rowSpacing: 10

                    ColumnLayout {
                        Layout.fillWidth: true
                        Layout.columnSpan: root.width > 880 ? 1 : 2
                        spacing: 6

                        FilterLabel { text: "Ricerca" }

                        DarkTextField {
                            id: searchField
                            Layout.fillWidth: true
                            placeholderText: "Cerca ID o nome..."
                            onTextChanged: controller.searchCatalogue(text)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        FilterLabel { text: "Mese" }

                        DarkComboBox {
                            id: monthFilter
                            Layout.fillWidth: true
                            enabled: controller.catalogueVisibleThisMonthFilter
                            opacity: enabled ? 1.0 : 0.55
                            model: controller.catalogueMonthLabels
                            currentIndex: Math.max(0, controller.catalogueSelectedMonth - 1)
                            onActivated: controller.setCatalogueMonth(currentIndex + 1)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        FilterLabel { text: "Catalogo" }

                        DarkComboBox {
                            id: catalogueFilter
                            Layout.fillWidth: true
                            model: root.optionModel("catalogues")
                            onActivated: controller.setCatalogueFilter("catalogue", currentText)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        FilterLabel { text: "Tipo" }

                        DarkComboBox {
                            id: typeFilter
                            Layout.fillWidth: true
                            model: root.optionModel("types")
                            onActivated: controller.setCatalogueFilter("type", currentText)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        FilterLabel { text: "Costellazione" }

                        DarkComboBox {
                            id: constellationFilter
                            Layout.fillWidth: true
                            model: root.optionModel("constellations")
                            onActivated: controller.setCatalogueFilter("constellation", currentText)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        FilterLabel { text: "Osservazione" }

                        DarkComboBox {
                            id: observationTypeFilter
                            Layout.fillWidth: true
                            model: root.optionModel("observationTypes")
                            onActivated: controller.setCatalogueFilter("observation_type", currentText)
                        }
                    }

                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 6

                        FilterLabel { text: "Visibilità" }

                        CheckBox {
                            id: visibleThisMonthFilter
                            Layout.fillWidth: true
                            text: "Visibili nel mese"
                            checked: controller.catalogueVisibleThisMonthFilter
                            onToggled: controller.setCatalogueVisibleThisMonthFilter(checked)
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        Layout.fillWidth: true
                        text: controller.catalogueFilteredCount + " di " + controller.catalogueTotalCount + " oggetti"
                        color: theme.textSecondary
                        font.pixelSize: 13
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    DarkButton {
                        text: "Pulisci filtri"
                        accentColor: theme.teal
                        onClicked: root.clearFilters()
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: ""
                subtitle: ""
                accentColor: theme.teal

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 36
                    radius: 6
                    color: "#20242b"
                    border.color: "#303641"
                    border.width: 1

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 10
                        anchors.rightMargin: 10
                        spacing: 8

                        TableHeader { text: "ID"; Layout.preferredWidth: 64 }
                        TableHeader { text: "Nome"; Layout.fillWidth: true; Layout.minimumWidth: 120 }
                        TableHeader { text: "Tipo"; Layout.preferredWidth: 110 }
                        TableHeader { text: "Costellazione"; Layout.preferredWidth: 112 }
                        TableHeader { text: "Magnitudine"; Layout.preferredWidth: 92 }
                        TableHeader { text: "Dimensione"; Layout.preferredWidth: 94 }
                        TableHeader { text: "Osservazione"; Layout.preferredWidth: 116 }
                        TableHeader { text: "Osservabile"; Layout.preferredWidth: 92 }
                        TableHeader { text: "Visibile nel mese"; Layout.preferredWidth: 124 }
                    }
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 4

                    Repeater {
                        model: controller.catalogueObjects

                        delegate: Rectangle {
                            id: row
                            property var itemData: modelData
                            property bool hovered: false

                            Layout.fillWidth: true
                            implicitHeight: 46
                            radius: 6
                            color: hovered ? "#252b34" : "#171a20"
                            border.color: hovered ? theme.cyan : "#303641"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 8

                                TableCell { text: itemData.catalogue_id; color: theme.cyan; font.weight: Font.DemiBold; Layout.preferredWidth: 64 }
                                TableCell { text: itemData.name; color: theme.textPrimary; Layout.fillWidth: true; Layout.minimumWidth: 120 }
                                TableCell { text: itemData.type; Layout.preferredWidth: 110 }
                                TableCell { text: root.textOrDash(itemData.constellation); Layout.preferredWidth: 112 }
                                TableCell { text: root.magnitudeText(itemData); Layout.preferredWidth: 92 }
                                TableCell { text: root.sizeText(itemData); Layout.preferredWidth: 94 }
                                TableCell { text: root.textOrDash(itemData.recommended_observation_type); Layout.preferredWidth: 116 }
                                TableCell {
                                    text: root.observableText(itemData)
                                    color: itemData.observable === true ? theme.green : theme.textMuted
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    Layout.preferredWidth: 92
                                }
                                TableCell {
                                    text: root.visibleText(itemData)
                                    color: itemData.visible_this_month === true ? theme.green : theme.textMuted
                                    font.weight: Font.DemiBold
                                    horizontalAlignment: Text.AlignHCenter
                                    Layout.preferredWidth: 124
                                }
                            }

                            MouseArea {
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onEntered: row.hovered = true
                                onExited: row.hovered = false
                                onClicked: root.openObject(row.itemData.object_id)
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: controller.catalogueFilteredCount === 0
                    text: "Nessun oggetto trovato."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    component TableHeader: Text {
        color: theme.textMuted
        font.pixelSize: 11
        font.weight: Font.DemiBold
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        maximumLineCount: 1
    }

    component TableCell: Text {
        color: theme.textSecondary
        font.pixelSize: 12
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
        maximumLineCount: 1
    }

    component FilterLabel: Text {
        Layout.fillWidth: true
        color: theme.textMuted
        font.pixelSize: 11
        font.weight: Font.DemiBold
        elide: Text.ElideRight
        maximumLineCount: 1
    }
}

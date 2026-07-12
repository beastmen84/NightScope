pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var editFilter: ({})
    property var editReducer: ({})
    property var deleteFilter: ({})
    property var deleteReducer: ({})
    property string accessorySearch: ""
    readonly property var filterTypeCodes: [
        "UHC", "OIII", "H_BETA", "CLS", "MOON_SKYGLOW", "ND",
        "POLARIZING", "COLOR", "CONTRAST", "CHROMATIC", "COMET"
    ]
    readonly property var filterTypeLabels: [
        "UHC", "OIII", "H-beta", "Riduzione inquinamento luminoso",
        "Luna e contrasto", "Densità neutra", "Polarizzatore",
        "Colorato planetario", "Contrasto planetario",
        "Correzione cromatica", "Comete"
    ]
    readonly property var opticalSystemCodes: [
        "SCT_CLASSIC", "EDGEHD", "REFRACTOR", "RC", "UNIVERSAL", "OTHER"
    ]
    readonly property var opticalSystemLabels: [
        "SCT classico", "EdgeHD", "Rifrattore", "Ritchey-Chrétien",
        "Universale", "Altro"
    ]

    function optionalText(value) {
        return value === undefined || value === null ? "" : String(value)
    }

    function searchText() {
        return root.accessorySearch.toLowerCase().trim()
    }

    function matchesFilter(item) {
        var query = root.searchText()
        if (query.length === 0)
            return true
        var text = (
            item.brand + " " + item.model + " " + item.filter_class_label + " " +
            item.barrel_size + " " + (item.notes || "")
        ).toLowerCase()
        return text.indexOf(query) >= 0
    }

    function matchesReducer(item) {
        var query = root.searchText()
        if (query.length === 0)
            return true
        var text = (
            item.brand + " " + item.model + " " + item.reduction_factor + " " +
            item.optical_system_label + " " + (item.compatible_models || "") + " " +
            (item.connection || "")
        ).toLowerCase()
        return text.indexOf(query) >= 0
    }

    function filteredFilters() {
        return root.controller.filterCatalog.filter(function(item) {
            return root.matchesFilter(item)
        })
    }

    function filteredReducers() {
        return root.controller.reducerCatalog.filter(function(item) {
            return root.matchesReducer(item)
        })
    }

    function openFilterDialog(item) {
        editFilter = item || ({})
        filterBrand.text = item ? item.brand : ""
        filterModel.text = item ? item.model : ""
        filterType.currentIndex = Math.max(0, root.filterTypeCodes.indexOf(item ? item.filter_class : "UHC"))
        filterBarrel.currentIndex = item && item.barrel_size === "2" ? 1 : 0
        filterCentral.text = item ? root.optionalText(item.central_wavelength_nm) : ""
        filterBandwidth.text = item ? root.optionalText(item.bandwidth_nm) : ""
        filterTransmission.text = item ? root.optionalText(item.transmission_pct) : ""
        filterAperture.text = item ? root.optionalText(item.minimum_aperture_mm) : ""
        filterNotes.text = item ? (item.notes || "") : ""
        filterDialog.title = item ? "Modifica filtro" : "Aggiungi filtro"
        filterDialog.open()
    }

    function openReducerDialog(item) {
        editReducer = item || ({})
        reducerBrand.text = item ? item.brand : ""
        reducerModel.text = item ? item.model : ""
        reducerFactor.text = item ? root.optionalText(item.reduction_factor) : ""
        reducerSystem.currentIndex = Math.max(0, root.opticalSystemCodes.indexOf(item ? item.optical_system : "SCT_CLASSIC"))
        reducerModels.text = item ? (item.compatible_models || "") : ""
        reducerConnection.text = item ? (item.connection || "") : ""
        reducerBackfocus.text = item ? root.optionalText(item.backfocus_mm) : ""
        reducerVisual.checked = item ? item.visual_compatible : false
        reducerImaging.checked = item ? item.imaging_compatible : true
        reducerCorrected.checked = item ? item.corrected_field : true
        reducerNotes.text = item ? (item.notes || "") : ""
        reducerDialog.title = item ? "Modifica riduttore" : "Aggiungi riduttore"
        reducerDialog.open()
    }

    function reducerUseLabel(item) {
        if (item.visual_compatible && item.imaging_compatible)
            return "Visuale + foto"
        if (item.visual_compatible)
            return "Visuale"
        return "Fotografico"
    }

    AppTheme { id: theme }

    ColumnLayout {
        anchors.fill: parent
        spacing: 18

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
                    text: "Catalogo filtri e riduttori"
                    color: theme.textPrimary
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: "Accessori ottici disponibili per i profili osservativi"
                    color: theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }

            DarkTextField {
                Layout.preferredWidth: 330
                placeholderText: "Cerca filtro o riduttore..."
                onTextChanged: root.accessorySearch = text
            }
        }

        GridLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 28
            Layout.rightMargin: 28
            Layout.bottomMargin: 28
            columns: root.width > 760 ? 2 : 1
            columnSpacing: 16
            rowSpacing: 16

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 8
                color: "#171a20"
                border.color: "#303641"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Rectangle {
                            Layout.preferredWidth: 4
                            Layout.preferredHeight: 28
                            radius: 2
                            color: theme.teal
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                Layout.fillWidth: true
                                text: "Catalogo filtri"
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.filteredFilters().length + " di " + root.controller.filterCatalog.length + " filtri"
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }

                        DarkButton {
                            text: "Aggiungi filtro"
                            accentColor: theme.teal
                            onClicked: root.openFilterDialog(null)
                        }
                    }

                    ScrollView {
                        id: filterScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: Math.max(0, availableWidth - 14)

                        ColumnLayout {
                            width: Math.max(0, filterScroll.availableWidth - 14)
                            spacing: 10

                            Repeater {
                                model: root.filteredFilters()
                                delegate: FilterRow {
                                    required property var modelData
                                    itemData: modelData
                                    onEdit: root.openFilterDialog(modelData)
                                    onDeleteRequested: {
                                        root.deleteFilter = modelData
                                        deleteFilterDialog.open()
                                    }
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: root.filteredFilters().length === 0
                                text: "Nessun filtro trovato."
                                color: theme.textSecondary
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
                radius: 8
                color: "#171a20"
                border.color: "#303641"
                border.width: 1

                ColumnLayout {
                    anchors.fill: parent
                    anchors.margins: 16
                    spacing: 12

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Rectangle {
                            Layout.preferredWidth: 4
                            Layout.preferredHeight: 28
                            radius: 2
                            color: theme.amber
                        }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Text {
                                Layout.fillWidth: true
                                text: "Catalogo riduttori"
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: root.filteredReducers().length + " di " + root.controller.reducerCatalog.length + " riduttori"
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }

                        DarkButton {
                            text: "Aggiungi riduttore"
                            accentColor: theme.amber
                            onClicked: root.openReducerDialog(null)
                        }
                    }

                    ScrollView {
                        id: reducerScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: Math.max(0, availableWidth - 14)

                        ColumnLayout {
                            width: Math.max(0, reducerScroll.availableWidth - 14)
                            spacing: 10

                            Repeater {
                                model: root.filteredReducers()
                                delegate: ReducerRow {
                                    required property var modelData
                                    itemData: modelData
                                    onEdit: root.openReducerDialog(modelData)
                                    onDeleteRequested: {
                                        root.deleteReducer = modelData
                                        deleteReducerDialog.open()
                                    }
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: root.filteredReducers().length === 0
                                text: "Nessun riduttore trovato."
                                color: theme.textSecondary
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }

    component FilterRow: Rectangle {
        id: filterRow
        property var itemData
        signal edit()
        signal deleteRequested()

        Layout.fillWidth: true
        implicitHeight: filterContent.implicitHeight + 22
        radius: 8
        color: "#20242b"
        border.color: "#303641"
        border.width: 1

        ColumnLayout {
            id: filterContent
            anchors.fill: parent
            anchors.margins: 11
            spacing: 7

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    Layout.fillWidth: true
                    text: filterRow.itemData.brand + " " + filterRow.itemData.model
                    color: theme.textPrimary
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }
                DarkButton { text: "Modifica"; onClicked: filterRow.edit() }
                DarkButton {
                    visible: !filterRow.itemData.is_builtin
                    text: "Elimina"
                    danger: true
                    onClicked: filterRow.deleteRequested()
                }
            }

            Text {
                Layout.fillWidth: true
                text: filterRow.itemData.notes || ""
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8
                StatusPill { text: filterRow.itemData.filter_class_label; accentColor: theme.teal }
                StatusPill { text: filterRow.itemData.barrel_size + "\""; accentColor: theme.cyan }
                StatusPill {
                    visible: filterRow.itemData.bandwidth_nm !== null
                    text: root.optionalText(filterRow.itemData.bandwidth_nm) + " nm"
                    accentColor: theme.violet
                }
                StatusPill {
                    visible: filterRow.itemData.transmission_pct !== null
                    text: root.optionalText(filterRow.itemData.transmission_pct) + "%"
                    accentColor: theme.amber
                }
            }
        }
    }

    component ReducerRow: Rectangle {
        id: reducerRow
        property var itemData
        signal edit()
        signal deleteRequested()

        Layout.fillWidth: true
        implicitHeight: reducerContent.implicitHeight + 22
        radius: 8
        color: "#20242b"
        border.color: "#303641"
        border.width: 1

        ColumnLayout {
            id: reducerContent
            anchors.fill: parent
            anchors.margins: 11
            spacing: 7

            RowLayout {
                Layout.fillWidth: true
                spacing: 8
                Text {
                    Layout.fillWidth: true
                    text: reducerRow.itemData.brand + " " + reducerRow.itemData.model
                    color: theme.textPrimary
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }
                DarkButton { text: "Modifica"; onClicked: reducerRow.edit() }
                DarkButton {
                    visible: !reducerRow.itemData.is_builtin
                    text: "Elimina"
                    danger: true
                    onClicked: reducerRow.deleteRequested()
                }
            }

            Text {
                Layout.fillWidth: true
                text: reducerRow.itemData.compatible_models || reducerRow.itemData.notes || ""
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8
                StatusPill { text: reducerRow.itemData.reduction_factor + "x"; accentColor: theme.amber }
                StatusPill { text: reducerRow.itemData.optical_system_label; accentColor: theme.cyan }
                StatusPill { text: root.reducerUseLabel(reducerRow.itemData); accentColor: reducerRow.itemData.visual_compatible ? theme.green : theme.violet }
                StatusPill {
                    visible: reducerRow.itemData.backfocus_mm !== null
                    text: root.optionalText(reducerRow.itemData.backfocus_mm) + " mm"
                    accentColor: theme.teal
                }
            }
        }
    }

    DarkDialog {
        id: filterDialog
        title: "Aggiungi filtro"
        acceptText: "Salva"
        onAccepted: {
            var typeCode = root.filterTypeCodes[filterType.currentIndex]
            var barrel = filterBarrel.currentIndex === 1 ? "2" : "1.25"
            if (root.editFilter.id !== undefined) {
                root.controller.updateFilterModel(root.editFilter.id, filterBrand.text, filterModel.text, typeCode, barrel, filterCentral.text, filterBandwidth.text, filterTransmission.text, filterAperture.text, filterNotes.text)
            } else {
                root.controller.addFilterModel(filterBrand.text, filterModel.text, typeCode, barrel, filterCentral.text, filterBandwidth.text, filterTransmission.text, filterAperture.text, filterNotes.text)
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8
            DarkTextField { id: filterBrand; Layout.fillWidth: true; placeholderText: "Marca" }
            DarkTextField { id: filterModel; Layout.fillWidth: true; placeholderText: "Modello" }
            DarkComboBox { id: filterType; Layout.fillWidth: true; model: root.filterTypeLabels }
            DarkComboBox { id: filterBarrel; Layout.fillWidth: true; model: ["1.25\"", "2\""] }
            DarkTextField { id: filterCentral; Layout.fillWidth: true; placeholderText: "Lunghezza d'onda centrale (nm)"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: filterBandwidth; Layout.fillWidth: true; placeholderText: "Larghezza banda (nm)"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: filterTransmission; Layout.fillWidth: true; placeholderText: "Trasmissione (%)"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: filterAperture; Layout.fillWidth: true; placeholderText: "Apertura minima (mm)"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: filterNotes; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: "Note" }
        }
    }

    DarkDialog {
        id: reducerDialog
        title: "Aggiungi riduttore"
        acceptText: "Salva"
        preferredWidth: 780
        onAccepted: {
            var systemCode = root.opticalSystemCodes[reducerSystem.currentIndex]
            if (root.editReducer.id !== undefined) {
                root.controller.updateReducerModel(root.editReducer.id, reducerBrand.text, reducerModel.text, reducerFactor.text, systemCode, reducerModels.text, reducerConnection.text, reducerBackfocus.text, reducerVisual.checked, reducerImaging.checked, reducerCorrected.checked, reducerNotes.text)
            } else {
                root.controller.addReducerModel(reducerBrand.text, reducerModel.text, reducerFactor.text, systemCode, reducerModels.text, reducerConnection.text, reducerBackfocus.text, reducerVisual.checked, reducerImaging.checked, reducerCorrected.checked, reducerNotes.text)
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8
            DarkTextField { id: reducerBrand; Layout.fillWidth: true; placeholderText: "Marca" }
            DarkTextField { id: reducerModel; Layout.fillWidth: true; placeholderText: "Modello" }
            DarkTextField { id: reducerFactor; Layout.fillWidth: true; placeholderText: "Fattore (es. 0.63)"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkComboBox { id: reducerSystem; Layout.fillWidth: true; model: root.opticalSystemLabels }
            DarkTextField { id: reducerModels; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: "Telescopi compatibili" }
            DarkTextField { id: reducerConnection; Layout.fillWidth: true; placeholderText: "Connessione" }
            DarkTextField { id: reducerBackfocus; Layout.fillWidth: true; placeholderText: "Backfocus (mm)"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            CheckBox { id: reducerVisual; Layout.fillWidth: true; text: "Uso visuale" }
            CheckBox { id: reducerImaging; Layout.fillWidth: true; text: "Uso fotografico" }
            CheckBox { id: reducerCorrected; Layout.columnSpan: 2; Layout.fillWidth: true; text: "Correzione del campo" }
            DarkTextField { id: reducerNotes; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: "Note" }
        }
    }

    DarkDialog {
        id: deleteFilterDialog
        title: "Elimina filtro"
        acceptText: root.controller.equipmentUsage("filter", root.deleteFilter.catalog_id || "") > 0 ? "Rimuovi dai profili e continua" : "Elimina"
        acceptDanger: true
        onAccepted: root.controller.deleteFilterModel(root.deleteFilter.id, root.controller.equipmentUsage("filter", root.deleteFilter.catalog_id || "") > 0)
        Text {
            Layout.fillWidth: true
            text: root.controller.equipmentUsage("filter", root.deleteFilter.catalog_id || "") > 0
                ? "Questo elemento è utilizzato da uno o più profili."
                : "Eliminare il filtro dal catalogo?"
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: deleteReducerDialog
        title: "Elimina riduttore"
        acceptText: root.controller.equipmentUsage("reducer", root.deleteReducer.catalog_id || "") > 0 ? "Rimuovi dai profili e continua" : "Elimina"
        acceptDanger: true
        onAccepted: root.controller.deleteReducerModel(root.deleteReducer.id, root.controller.equipmentUsage("reducer", root.deleteReducer.catalog_id || "") > 0)
        Text {
            Layout.fillWidth: true
            text: root.controller.equipmentUsage("reducer", root.deleteReducer.catalog_id || "") > 0
                ? "Questo elemento è utilizzato da uno o più profili."
                : "Eliminare il riduttore dal catalogo?"
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }
}

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
    property string reducerTelescopeSearch: ""
    property var reducerTelescopeIds: []
    readonly property var filterTypeOptions: controller ? controller.filterClassOptions : []
    readonly property var filterTypeCodes: filterTypeOptions.map(function(item) { return item.code })
    readonly property var filterTypeLabels: filterTypeOptions.map(function(item) { return item.label })
    readonly property var opticalSystemCodes: [
        "SCT_CLASSIC", "EDGEHD", "REFRACTOR", "RC", "UNIVERSAL", "OTHER"
    ]
    readonly property var opticalSystemLabels: [
        qsTr("SCT classico"), qsTr("EdgeHD"), qsTr("Rifrattore"), qsTr("Ritchey-Chrétien"),
        qsTr("Universale"), qsTr("Altro")
    ]

    function optionalText(value) {
        return value === undefined || value === null ? "" : String(value)
    }

    function numberValue(value) {
        return Number(String(value).trim().replace(",", "."))
    }

    function validReductionFactor(value) {
        var number = root.numberValue(value)
        return isFinite(number) && number > 0 && number < 1
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
            (item.notes || "")
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

    function filteredReducerTelescopeModels() {
        var query = root.reducerTelescopeSearch.toLowerCase().trim()
        return root.controller.telescopeCatalogModels.filter(function(item) {
            if (query.length === 0)
                return true
            return (item.brand + " " + item.name + " " + item.optical_type)
                    .toLowerCase().indexOf(query) >= 0
        })
    }

    function setReducerTelescopeSelected(catalogId, selected) {
        var next = root.reducerTelescopeIds.slice()
        var index = next.indexOf(catalogId)
        if (selected && index < 0)
            next.push(catalogId)
        else if (!selected && index >= 0)
            next.splice(index, 1)
        root.reducerTelescopeIds = next
    }

    function openFilterDialog(item) {
        editFilter = item || ({})
        filterBrand.text = item ? item.brand : ""
        filterModel.text = item ? item.model : ""
        var typeIndex = root.filterTypeCodes.indexOf(item ? item.filter_class : "UHC")
        filterType.currentIndex = item && typeIndex < 0 ? -1 : Math.max(0, typeIndex)
        filterCentral.text = item ? root.optionalText(item.central_wavelength_nm) : ""
        filterBandwidth.text = item ? root.optionalText(item.bandwidth_nm) : ""
        filterTransmission.text = item ? root.optionalText(item.transmission_pct) : ""
        filterAperture.text = item ? root.optionalText(item.minimum_aperture_mm) : ""
        filterNotes.text = item ? (item.notes || "") : ""
        filterDialog.title = item ? qsTr("Modifica filtro") : qsTr("Aggiungi filtro")
        filterDialog.open()
    }

    function openReducerDialog(item) {
        editReducer = item || ({})
        reducerBrand.text = item ? item.brand : ""
        reducerModel.text = item ? item.model : ""
        reducerFactor.text = item ? root.optionalText(item.reduction_factor) : ""
        reducerSystem.currentIndex = Math.max(0, root.opticalSystemCodes.indexOf(item ? item.optical_system : "SCT_CLASSIC"))
        reducerTelescopeIds = item ? (item.compatible_telescope_ids || []).slice() : []
        reducerTelescopeSearch = ""
        reducerTelescopeSearchField.text = ""
        reducerConnection.text = item ? (item.connection || "") : ""
        reducerBackfocus.text = item ? root.optionalText(item.backfocus_mm) : ""
        reducerVisual.checked = item ? item.visual_compatible : false
        reducerImaging.checked = item ? item.imaging_compatible : true
        reducerCorrected.checked = item ? item.corrected_field : true
        reducerNotes.text = item ? (item.notes || "") : ""
        reducerDialog.title = item ? qsTr("Modifica riduttore") : qsTr("Aggiungi riduttore")
        reducerDialog.open()
    }

    function reducerUseLabel(item) {
        if (item.visual_compatible && item.imaging_compatible)
            return qsTr("Visuale + foto")
        if (item.visual_compatible)
            return qsTr("Visuale")
        return qsTr("Fotografico")
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
                    text: qsTr("Catalogo filtri e riduttori")
                    color: theme.textPrimary
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Accessori ottici disponibili per i profili osservativi")
                    color: theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }

            DarkTextField {
                Layout.preferredWidth: 330
                placeholderText: qsTr("Cerca filtro o riduttore...")
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
                                text: qsTr("Catalogo filtri")
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: qsTr("%1 di %2 filtri")
                                    .arg(root.filteredFilters().length)
                                    .arg(root.controller.filterCatalog.length)
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }

                        DarkButton {
                            text: qsTr("Aggiungi filtro")
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
                                text: qsTr("Nessun filtro trovato.")
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
                                text: qsTr("Catalogo riduttori")
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }
                            Text {
                                Layout.fillWidth: true
                                text: qsTr("%1 di %2 riduttori")
                                    .arg(root.filteredReducers().length)
                                    .arg(root.controller.reducerCatalog.length)
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }

                        DarkButton {
                            text: qsTr("Aggiungi riduttore")
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
                                text: qsTr("Nessun riduttore trovato.")
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
                DarkButton {
                    text: qsTr("Modifica")
                    onClicked: filterRow.edit()
                }
                DarkButton {
                    visible: !filterRow.itemData.is_builtin
                    text: qsTr("Elimina")
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
                StatusPill {
                    visible: String(filterRow.itemData.bandwidth_label || "").trim().length > 0
                    text: filterRow.itemData.bandwidth_label || ""
                    accentColor: theme.violet
                }
                StatusPill {
                    visible: String(filterRow.itemData.transmission_label || "").trim().length > 0
                    text: filterRow.itemData.transmission_label || ""
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
                DarkButton {
                    text: qsTr("Modifica")
                    onClicked: reducerRow.edit()
                }
                DarkButton {
                    visible: !reducerRow.itemData.is_builtin
                    text: qsTr("Elimina")
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
                StatusPill { text: reducerRow.itemData.reduction_factor_label; accentColor: theme.amber }
                StatusPill { text: reducerRow.itemData.optical_system_label; accentColor: theme.cyan }
                StatusPill { text: root.reducerUseLabel(reducerRow.itemData); accentColor: reducerRow.itemData.visual_compatible ? theme.green : theme.violet }
                StatusPill {
                    visible: String(reducerRow.itemData.backfocus_label || "").trim().length > 0
                    text: reducerRow.itemData.backfocus_label || ""
                    accentColor: theme.teal
                }
            }
        }
    }

    DarkDialog {
        id: filterDialog
        title: qsTr("Aggiungi filtro")
        acceptText: qsTr("Salva")
        closeOnAccept: false
        acceptEnabled: filterBrand.text.trim().length > 0
            && filterModel.text.trim().length > 0
            && filterType.currentIndex >= 0
        onOpened: root.controller.clearEquipmentMessage()
        onAccepted: {
            var typeCode = root.filterTypeCodes[filterType.currentIndex]
            var saved
            if (root.editFilter.id !== undefined) {
                saved = root.controller.updateFilterModel(root.editFilter.id, filterBrand.text, filterModel.text, typeCode, filterCentral.text, filterBandwidth.text, filterTransmission.text, filterAperture.text, filterNotes.text)
            } else {
                saved = root.controller.addFilterModel(filterBrand.text, filterModel.text, typeCode, filterCentral.text, filterBandwidth.text, filterTransmission.text, filterAperture.text, filterNotes.text)
            }
            if (saved)
                filterDialog.close()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8
            DarkTextField { id: filterBrand; Layout.fillWidth: true; placeholderText: qsTr("Marca *") }
            DarkTextField { id: filterModel; Layout.fillWidth: true; placeholderText: qsTr("Modello *") }
            DarkComboBox { id: filterType; Layout.columnSpan: 2; Layout.fillWidth: true; model: root.filterTypeLabels }
            DarkTextField { id: filterCentral; Layout.fillWidth: true; placeholderText: qsTr("Lunghezza d'onda centrale (nm, facoltativa)"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: filterBandwidth; Layout.fillWidth: true; placeholderText: qsTr("Larghezza banda (nm, facoltativa)"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: filterTransmission; Layout.fillWidth: true; placeholderText: qsTr("Trasmissione (%, facoltativa)"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: filterAperture; Layout.fillWidth: true; placeholderText: qsTr("Apertura minima (mm, facoltativa)"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: filterNotes; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: qsTr("Note (facoltative)") }
        }

        Text {
            Layout.fillWidth: true
            visible: root.controller.equipmentMessage.length > 0
            text: root.controller.equipmentMessage
            color: theme.red
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: reducerDialog
        title: qsTr("Aggiungi riduttore")
        acceptText: qsTr("Salva")
        preferredWidth: 780
        closeOnAccept: false
        acceptEnabled: reducerBrand.text.trim().length > 0
            && reducerModel.text.trim().length > 0
            && root.validReductionFactor(reducerFactor.text)
            && reducerSystem.currentIndex >= 0
            && (reducerVisual.checked || reducerImaging.checked)
        onOpened: root.controller.clearEquipmentMessage()
        onAccepted: {
            var systemCode = root.opticalSystemCodes[reducerSystem.currentIndex]
            var saved
            if (root.editReducer.id !== undefined) {
                saved = root.controller.updateReducerModel(root.editReducer.id, reducerBrand.text, reducerModel.text, reducerFactor.text, systemCode, root.reducerTelescopeIds.join(","), reducerConnection.text, reducerBackfocus.text, reducerVisual.checked, reducerImaging.checked, reducerCorrected.checked, reducerNotes.text)
            } else {
                saved = root.controller.addReducerModel(reducerBrand.text, reducerModel.text, reducerFactor.text, systemCode, root.reducerTelescopeIds.join(","), reducerConnection.text, reducerBackfocus.text, reducerVisual.checked, reducerImaging.checked, reducerCorrected.checked, reducerNotes.text)
            }
            if (saved)
                reducerDialog.close()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8
            DarkTextField { id: reducerBrand; Layout.fillWidth: true; placeholderText: qsTr("Marca *") }
            DarkTextField { id: reducerModel; Layout.fillWidth: true; placeholderText: qsTr("Modello *") }
            DarkTextField { id: reducerFactor; Layout.fillWidth: true; placeholderText: qsTr("Fattore * (es. 0,63)"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkComboBox { id: reducerSystem; Layout.fillWidth: true; model: root.opticalSystemLabels }
            DarkTextField { id: reducerConnection; Layout.fillWidth: true; placeholderText: qsTr("Connessione (facoltativa)") }
            DarkTextField { id: reducerBackfocus; Layout.fillWidth: true; placeholderText: qsTr("Backfocus (mm, facoltativo)"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            CheckBox { id: reducerVisual; Layout.fillWidth: true; text: qsTr("Uso visuale") }
            CheckBox { id: reducerImaging; Layout.fillWidth: true; text: qsTr("Uso fotografico") }
            CheckBox { id: reducerCorrected; Layout.columnSpan: 2; Layout.fillWidth: true; text: qsTr("Correzione del campo") }
            DarkTextField { id: reducerNotes; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: qsTr("Note (facoltative)") }

            RowLayout {
                Layout.columnSpan: 2
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Telescopi compatibili (facoltativi)")
                    color: theme.textPrimary
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                }

                Text {
                    text: root.reducerTelescopeIds.length === 1
                          ? qsTr("1 selezionato")
                          : qsTr("%1 selezionati").arg(root.reducerTelescopeIds.length)
                    color: theme.textMuted
                    font.pixelSize: 12
                }
            }

            DarkTextField {
                id: reducerTelescopeSearchField
                Layout.columnSpan: 2
                Layout.fillWidth: true
                placeholderText: qsTr("Cerca telescopio compatibile...")
                onTextChanged: root.reducerTelescopeSearch = text
            }

            GridView {
                id: reducerTelescopeGrid
                Layout.columnSpan: 2
                Layout.fillWidth: true
                Layout.preferredHeight: 176
                clip: true
                cellWidth: width > 620 ? Math.floor(width / 2) : width
                cellHeight: 42
                boundsBehavior: Flickable.StopAtBounds
                model: root.filteredReducerTelescopeModels()
                ScrollBar.vertical: ScrollBar { }

                delegate: CheckBox {
                    required property var modelData
                    width: GridView.view.cellWidth
                    text: modelData.brand + " " + modelData.name
                    checked: root.reducerTelescopeIds.indexOf(modelData.catalog_id) >= 0
                    onToggled: root.setReducerTelescopeSelected(
                        modelData.catalog_id,
                        checked
                    )
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: root.controller.equipmentMessage.length > 0
            text: root.controller.equipmentMessage
            color: theme.red
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: deleteFilterDialog
        title: qsTr("Elimina filtro")
        acceptText: root.controller.equipmentUsage("filter", root.deleteFilter.catalog_id || "") > 0 ? qsTr("Rimuovi dai profili e continua") : qsTr("Elimina")
        acceptDanger: true
        onAccepted: root.controller.deleteFilterModel(root.deleteFilter.id, root.controller.equipmentUsage("filter", root.deleteFilter.catalog_id || "") > 0)
        Text {
            Layout.fillWidth: true
            text: root.controller.equipmentUsage("filter", root.deleteFilter.catalog_id || "") > 0
                ? qsTr("Questo elemento è utilizzato da uno o più profili.")
                : qsTr("Eliminare il filtro dal catalogo?")
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: deleteReducerDialog
        title: qsTr("Elimina riduttore")
        acceptText: root.controller.equipmentUsage("reducer", root.deleteReducer.catalog_id || "") > 0 ? qsTr("Rimuovi dai profili e continua") : qsTr("Elimina")
        acceptDanger: true
        onAccepted: root.controller.deleteReducerModel(root.deleteReducer.id, root.controller.equipmentUsage("reducer", root.deleteReducer.catalog_id || "") > 0)
        Text {
            Layout.fillWidth: true
            text: root.controller.equipmentUsage("reducer", root.deleteReducer.catalog_id || "") > 0
                ? qsTr("Questo elemento è utilizzato da uno o più profili.")
                : qsTr("Eliminare il riduttore dal catalogo?")
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }
}

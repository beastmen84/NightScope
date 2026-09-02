// Purpose: Present telescope and smart-telescope catalogue CRUD workflows.
// Contract: Performs form affordance checks; canonicalization and persistence stay behind controller slots.

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var editModel: ({})
    property var deleteModel: ({})
    property string telescopeSearch: ""

    function numberValue(value) {
        return Number(String(value).trim().replace(",", "."))
    }

    function isPositiveInteger(value) {
        var number = root.numberValue(value)
        return isFinite(number) && number > 0 && Math.floor(number) === number
    }

    function isPositiveNumber(value) {
        var number = root.numberValue(value)
        return isFinite(number) && number > 0
    }

    function optionalPositiveInteger(value) {
        return String(value).trim().length === 0
            || root.isPositiveInteger(value)
    }

    function optionalPositiveNumber(value) {
        return String(value).trim().length === 0
            || root.isPositiveNumber(value)
    }

    function optionIndex(options, value, fallbackCode) {
        for (var index = 0; index < options.length; index += 1) {
            if (options[index].code === value)
                return index
        }
        for (var fallbackIndex = 0; fallbackIndex < options.length; fallbackIndex += 1) {
            if (options[fallbackIndex].code === fallbackCode)
                return fallbackIndex
        }
        return 0
    }

    function selectedOpticalType() {
        if (String(telescopeType.currentValue || "") === "OTHER")
            return telescopeCustomType.text.trim()
        return String(telescopeType.currentValue || "")
    }

    function normalizedSmartFilterCodes(value) {
        var source = []
        if (typeof value === "string")
            source = value.split(/[;,]+/)
        else if (value && value.length !== undefined)
            source = value
        var result = []
        for (var index = 0; index < source.length; index += 1) {
            var code = String(source[index] || "")
                .trim().toUpperCase().replace(/\s+/g, "_")
            if (code.length > 0 && result.indexOf(code) < 0)
                result.push(code)
        }
        return result
    }

    function isStandardSmartFilterCode(code) {
        return code === "UV_IR_CUT"
            || code === "DUAL_BAND"
            || code === "DARK"
    }

    function smartIntegratedFilterCodes() {
        var codes = []
        if (smartFilterUvIrCut.checked)
            codes.push("UV_IR_CUT")
        if (smartFilterDualBand.checked)
            codes.push("DUAL_BAND")
        if (smartFilterDark.checked)
            codes.push("DARK")
        var additional = smartAdditionalFilters.checked
            ? smartAdditionalFilterNames.text.trim() : ""
        if (additional.length > 0)
            codes.push(additional)
        return codes.join(";")
    }

    function smartCapabilitiesPayload() {
        return {
            "supports_optical_visual": smartOpticalVisual.checked,
            "supports_interchangeable_eyepieces": smartEyepieces.checked,
            "supports_external_cameras": smartExternalCameras.checked,
            "supports_external_optical_modifiers": smartExternalModifiers.checked,
            "sensor_model": smartSensorModel.text,
            "sensor_width_mm": smartSensorWidth.text,
            "sensor_height_mm": smartSensorHeight.text,
            "resolution_width_px": smartResolutionWidth.text,
            "resolution_height_px": smartResolutionHeight.text,
            "pixel_size_um": smartPixelSize.text,
            "bit_depth": smartBitDepth.text,
            "color_mode": String(smartColorMode.currentValue || ""),
            "full_resolution_fps": smartMaxFps.text,
            "supports_live_stacking": smartLiveStacking.checked,
            "supports_video": smartVideo.checked,
            "supports_mosaic": smartMosaic.checked,
            "exposure_control_mode": String(
                smartExposureControl.currentValue || "DEVICE_MANAGED"
            ),
            "integrated_filter_codes": root.smartIntegratedFilterCodes(),
            "specification_source_url": smartSource.text
        }
    }

    function smartFormValid() {
        if (String(telescopeCategory.currentValue || "")
                !== "SMART_INTEGRATED")
            return true
        return root.optionalPositiveNumber(smartSensorWidth.text)
            && root.optionalPositiveNumber(smartSensorHeight.text)
            && root.optionalPositiveInteger(smartResolutionWidth.text)
            && root.optionalPositiveInteger(smartResolutionHeight.text)
            && root.optionalPositiveNumber(smartPixelSize.text)
            && root.optionalPositiveInteger(smartBitDepth.text)
            && root.optionalPositiveNumber(smartMaxFps.text)
    }

    function resetSmartFields(item) {
        var capabilities = item
            && item.instrument_category === "SMART_INTEGRATED"
            && item.smart_capabilities
            ? item.smart_capabilities : ({})
        smartOpticalVisual.checked =
            capabilities.supports_optical_visual === true
        smartEyepieces.checked =
            capabilities.supports_interchangeable_eyepieces === true
        smartExternalCameras.checked =
            capabilities.supports_external_cameras === true
        smartExternalModifiers.checked =
            capabilities.supports_external_optical_modifiers === true
        smartSensorModel.text = capabilities.sensor_model || ""
        smartSensorWidth.text = capabilities.sensor_width_mm || ""
        smartSensorHeight.text = capabilities.sensor_height_mm || ""
        smartResolutionWidth.text = capabilities.resolution_width_px || ""
        smartResolutionHeight.text = capabilities.resolution_height_px || ""
        smartPixelSize.text = capabilities.pixel_size_um || ""
        smartBitDepth.text = capabilities.bit_depth || ""
        smartMaxFps.text = capabilities.full_resolution_fps || ""
        smartColorMode.currentIndex = root.optionIndex(
            controller.sensorColorModeOptions,
            capabilities.color_mode || "",
            "COLOR"
        )
        smartExposureControl.currentIndex = root.optionIndex(
            [
                {"code": "DEVICE_MANAGED"},
                {"code": "USER_CONFIGURABLE"}
            ],
            capabilities.exposure_control_mode || "",
            "DEVICE_MANAGED"
        )
        smartLiveStacking.checked =
            capabilities.supports_live_stacking === true
        smartVideo.checked = capabilities.supports_video === true
        smartMosaic.checked = capabilities.supports_mosaic === true
        var filterCodes = root.normalizedSmartFilterCodes(
            capabilities.integrated_filter_codes || []
        )
        smartFilterUvIrCut.checked =
            filterCodes.indexOf("UV_IR_CUT") >= 0
        smartFilterDualBand.checked =
            filterCodes.indexOf("DUAL_BAND") >= 0
        smartFilterDark.checked = filterCodes.indexOf("DARK") >= 0
        var additionalFilters = []
        for (var filterIndex = 0;
             filterIndex < filterCodes.length;
             filterIndex += 1) {
            if (!root.isStandardSmartFilterCode(filterCodes[filterIndex]))
                additionalFilters.push(
                    filterCodes[filterIndex].replace(/_/g, " ")
                )
        }
        smartAdditionalFilters.checked = additionalFilters.length > 0
        smartAdditionalFilterNames.text = additionalFilters.join("; ")
        smartSource.text = capabilities.specification_source_url || ""
    }

    function openEditDialog(item) {
        editModel = item
        telescopeBrand.text = item.brand || ""
        telescopeName.text = item.name || ""
        telescopeCategory.currentIndex = root.optionIndex(
            controller.telescopeCategoryOptions,
            item.instrument_category || "",
            "TRADITIONAL"
        )
        telescopeType.currentIndex = root.optionIndex(
            controller.telescopeOpticalTypeOptions,
            item.optical_type_code || "",
            "OTHER"
        )
        telescopeCustomType.text = item.optical_type_code === "OTHER"
            ? (item.optical_type || "") : ""
        telescopeAperture.text = String(item.aperture_mm || "")
        telescopeFocal.text = String(item.focal_length_mm || "")
        telescopeMount.currentIndex = root.optionIndex(
            controller.telescopeMountTypeOptions,
            item.mount_type || "",
            "OTHER"
        )
        telescopeNotes.text = item.notes || ""
        root.resetSmartFields(item)
        telescopeDialog.title = qsTr("Modifica modello")
        telescopeDialog.open()
    }

    function openAddDialog() {
        editModel = ({})
        telescopeBrand.text = ""
        telescopeName.text = ""
        telescopeCategory.currentIndex = root.optionIndex(
            controller.telescopeCategoryOptions,
            "TRADITIONAL",
            "TRADITIONAL"
        )
        telescopeType.currentIndex = root.optionIndex(
            controller.telescopeOpticalTypeOptions,
            "REFRACTOR",
            "REFRACTOR"
        )
        telescopeCustomType.text = ""
        telescopeAperture.text = ""
        telescopeFocal.text = ""
        telescopeMount.currentIndex = 0
        telescopeNotes.text = ""
        root.resetSmartFields(null)
        telescopeDialog.title = qsTr("Aggiungi modello")
        telescopeDialog.open()
    }

    function matchesTelescope(item) {
        var query = root.telescopeSearch.toLowerCase().trim()
        if (query.length === 0)
            return true
        var text = (
            item.brand + " " + item.name + " "
            + (item.instrument_category_label || "") + " "
            + (item.optical_type_label || item.optical_type)
        ).toLowerCase()
        return text.indexOf(query) >= 0
    }

    function filteredTelescopeModels() {
        return controller.telescopeCatalogModels.filter(function(item) {
            return root.matchesTelescope(item)
        })
    }

    AppTheme { id: theme }

    ScrollView {
        id: scroll
        anchors.fill: parent
        clip: true
        contentWidth: availableWidth

        ColumnLayout {
            width: scroll.availableWidth
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
                        text: qsTr("Catalogo telescopi")
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Modelli disponibili per i profili osservativi")
                        color: theme.textSecondary
                        font.pixelSize: 14
                        wrapMode: Text.WordWrap
                    }
                }

                DarkTextField {
                    Layout.preferredWidth: 300
                    placeholderText: qsTr("Cerca telescopio...")
                    onTextChanged: root.telescopeSearch = text
                }

                DarkButton {
                    text: qsTr("Aggiungi modello")
                    accentColor: theme.cyan
                    onClicked: root.openAddDialog()
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: ""
                subtitle: ""
                accentColor: theme.cyan

                Text {
                    Layout.fillWidth: true
                    text: qsTr("%1 di %2 modelli")
                        .arg(root.filteredTelescopeModels().length)
                        .arg(controller.telescopeCatalogModels.length)
                    color: theme.textSecondary
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                GridLayout {
                    id: telescopeCatalogGrid
                    Layout.fillWidth: true
                    columns: root.width > 1060 ? 2 : 1
                    columnSpacing: 12
                    rowSpacing: 12

                    Repeater {
                        model: root.filteredTelescopeModels()

                        delegate: TelescopeCatalogCard {
                            itemData: modelData
                            onEdit: root.openEditDialog(modelData)
                            onDeleteRequested: {
                                root.deleteModel = modelData
                                deleteTelescopeDialog.open()
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.filteredTelescopeModels().length === 0
                    text: qsTr("Nessun telescopio trovato.")
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    component TelescopeCatalogCard: Rectangle {
        id: telescopeCard
        property var itemData
        signal edit()
        signal deleteRequested()

        Layout.fillWidth: true
        implicitHeight: telescopeCardContent.implicitHeight + 20
        radius: 8
        color: theme.surfaceRaised
        border.color: theme.border
        border.width: 1

        ColumnLayout {
            id: telescopeCardContent
            anchors.fill: parent
            anchors.margins: 10
            spacing: 6

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: itemData.brand + " " + itemData.name
                    color: theme.textPrimary
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                DarkButton {
                    text: qsTr("Modifica")
                    implicitHeight: 32
                    leftPadding: 10
                    rightPadding: 10
                    onClicked: telescopeCard.edit()
                }

                DarkButton {
                    visible: !itemData.is_builtin
                    text: qsTr("Elimina")
                    implicitHeight: 32
                    leftPadding: 10
                    rightPadding: 10
                    danger: true
                    onClicked: telescopeCard.deleteRequested()
                }
            }

            Text {
                Layout.fillWidth: true
                text: (itemData.optical_type_label || itemData.optical_type)
                    + "  -  "
                    + (itemData.mount_type_label || itemData.mount_type)
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8
                StatusPill {
                    text: itemData.instrument_category_label || ""
                    accentColor: itemData.instrument_category === "SMART_INTEGRATED"
                                 ? theme.violet : theme.textMuted
                }
                StatusPill { text: itemData.aperture_label; accentColor: theme.cyan }
                StatusPill { text: itemData.focal_length_label; accentColor: theme.teal }
                StatusPill {
                    visible: String(itemData.focal_ratio_label || "").trim().length > 0
                    text: itemData.focal_ratio_label || ""
                    accentColor: theme.amber
                }
                StatusPill {
                    visible: itemData.instrument_category === "SMART_INTEGRATED"
                        && String(itemData.sensor_model || "").length > 0
                    text: itemData.sensor_model || ""
                    accentColor: theme.violet
                }
            }
        }
    }

    DarkDialog {
        id: telescopeDialog
        objectName: "telescopeDialog"
        preferredWidth: 780
        title: qsTr("Aggiungi modello")
        acceptText: qsTr("Salva")
        closeOnAccept: false
        acceptEnabled: telescopeBrand.text.trim().length > 0
            && telescopeName.text.trim().length > 0
            && String(telescopeCategory.currentValue || "").length > 0
            && root.selectedOpticalType().length > 0
            && root.isPositiveInteger(telescopeAperture.text)
            && root.isPositiveInteger(telescopeFocal.text)
            && String(telescopeMount.currentValue || "").length > 0
            && root.smartFormValid()
        onOpened: controller.clearEquipmentMessage()
        onAccepted: {
            var saved
            if (root.editModel.id !== undefined) {
                saved = controller.updateTelescopeModel(
                    root.editModel.id,
                    telescopeBrand.text,
                    telescopeName.text,
                    root.selectedOpticalType(),
                    telescopeAperture.text,
                    telescopeFocal.text,
                    String(telescopeMount.currentValue || ""),
                    telescopeNotes.text,
                    String(telescopeCategory.currentValue || ""),
                    root.smartCapabilitiesPayload()
                )
            } else {
                saved = controller.addTelescopeModel(
                    telescopeBrand.text,
                    telescopeName.text,
                    root.selectedOpticalType(),
                    telescopeAperture.text,
                    telescopeFocal.text,
                    String(telescopeMount.currentValue || ""),
                    telescopeNotes.text,
                    String(telescopeCategory.currentValue || ""),
                    root.smartCapabilitiesPayload()
                )
            }
            if (saved)
                telescopeDialog.close()
        }

        ScrollView {
            id: telescopeFormScroll
            objectName: "telescopeForm"
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(
                telescopeFormContent.implicitHeight,
                Math.max(
                    300,
                    telescopeDialog.parent
                        ? telescopeDialog.parent.height - 250 : 560
                )
            )
            contentWidth: availableWidth
            clip: true

            ColumnLayout {
                id: telescopeFormContent
                width: Math.max(0, telescopeFormScroll.availableWidth - 12)
                spacing: 14

                GridLayout {
                    id: telescopeForm
                    Layout.fillWidth: true
                    columns: telescopeDialog.width < 620 ? 1 : 2
                    uniformCellWidths: true
                    columnSpacing: 8
                    rowSpacing: 8

                    DarkTextField {
                        id: telescopeBrand
                        objectName: "telescopeBrand"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        labelText: qsTr("Marca *")
                    }

                    DarkTextField {
                        id: telescopeName
                        objectName: "telescopeName"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        labelText: qsTr("Modello *")
                    }

                    DarkComboBox {
                        id: telescopeCategory
                        objectName: "telescopeCategory"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        labelText: qsTr("Categoria strumento *")
                        model: controller.telescopeCategoryOptions
                        textRole: "label"
                        valueRole: "code"
                    }

                    DarkComboBox {
                        id: telescopeType
                        objectName: "telescopeType"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        labelText: qsTr("Tipo ottico *")
                        model: controller.telescopeOpticalTypeOptions
                        textRole: "label"
                        valueRole: "code"
                    }

                    DarkTextField {
                        id: telescopeCustomType
                        objectName: "telescopeCustomType"
                        visible: String(telescopeType.currentValue || "")
                            === "OTHER"
                        Layout.columnSpan: telescopeForm.columns
                        Layout.fillWidth: true
                        labelText: qsTr("Tipo ottico personalizzato *")
                    }

                    DarkTextField {
                        id: telescopeAperture
                        objectName: "telescopeAperture"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        labelText: qsTr("Apertura (mm) *")
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                    }

                    DarkTextField {
                        id: telescopeFocal
                        objectName: "telescopeFocal"
                        Layout.fillWidth: true
                        Layout.preferredWidth: 1
                        labelText: qsTr("Focale (mm) *")
                        inputMethodHints: Qt.ImhFormattedNumbersOnly
                    }

                    DarkComboBox {
                        id: telescopeMount
                        objectName: "telescopeMount"
                        Layout.columnSpan: telescopeForm.columns
                        Layout.fillWidth: true
                        labelText: qsTr("Montatura *")
                        model: controller.telescopeMountTypeOptions
                        textRole: "label"
                        valueRole: "code"
                    }

                    DarkTextField {
                        id: telescopeNotes
                        objectName: "telescopeNotes"
                        Layout.columnSpan: telescopeForm.columns
                        Layout.fillWidth: true
                        labelText: qsTr("Note (facoltative)")
                    }
                }

                ColumnLayout {
                    visible: String(telescopeCategory.currentValue || "")
                        === "SMART_INTEGRATED"
                    Layout.fillWidth: true
                    spacing: 10

                    Text {
                        Layout.fillWidth: true
                        text: qsTr("Treno ottico e sensore integrati")
                        color: theme.textPrimary
                        font.pixelSize: 15
                        font.weight: Font.DemiBold
                    }

                    Text {
                        Layout.fillWidth: true
                        text: qsTr(
                            "Inserisci il canale astronomico principale. "
                            + "I campi possono restare incompleti, ma in quel "
                            + "caso NightScope non inventerà un piano EAA."
                        )
                        color: theme.textSecondary
                        font.pixelSize: 12
                        wrapMode: Text.WordWrap
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: telescopeDialog.width < 620 ? 1 : 3
                        uniformCellWidths: true
                        columnSpacing: 8
                        rowSpacing: 8

                        DarkTextField {
                            id: smartSensorModel
                            Layout.fillWidth: true
                            labelText: qsTr("Sensore integrato")
                        }
                        DarkComboBox {
                            id: smartColorMode
                            Layout.fillWidth: true
                            labelText: qsTr("Modalità colore")
                            model: controller.sensorColorModeOptions
                            textRole: "label"
                            valueRole: "code"
                        }
                        DarkComboBox {
                            id: smartExposureControl
                            Layout.fillWidth: true
                            labelText: qsTr("Controllo delle pose")
                            model: [
                                {
                                    "code": "DEVICE_MANAGED",
                                    "label": qsTr("Gestito dal dispositivo")
                                },
                                {
                                    "code": "USER_CONFIGURABLE",
                                    "label": qsTr("Configurabile dall'utente")
                                }
                            ]
                            textRole: "label"
                            valueRole: "code"
                        }

                        DarkTextField {
                            id: smartSensorWidth
                            Layout.fillWidth: true
                            labelText: qsTr("Sensore, larghezza (mm)")
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                        DarkTextField {
                            id: smartSensorHeight
                            Layout.fillWidth: true
                            labelText: qsTr("Sensore, altezza (mm)")
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                        DarkTextField {
                            id: smartPixelSize
                            Layout.fillWidth: true
                            labelText: qsTr("Passo pixel (µm)")
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }

                        DarkTextField {
                            id: smartResolutionWidth
                            Layout.fillWidth: true
                            labelText: qsTr("Risoluzione orizzontale (px)")
                            inputMethodHints: Qt.ImhDigitsOnly
                        }
                        DarkTextField {
                            id: smartResolutionHeight
                            Layout.fillWidth: true
                            labelText: qsTr("Risoluzione verticale (px)")
                            inputMethodHints: Qt.ImhDigitsOnly
                        }
                        DarkTextField {
                            id: smartBitDepth
                            Layout.fillWidth: true
                            labelText: qsTr("Profondità (bit)")
                            inputMethodHints: Qt.ImhDigitsOnly
                        }

                        DarkTextField {
                            id: smartMaxFps
                            Layout.fillWidth: true
                            labelText: qsTr("FPS verificati (facoltativo)")
                            inputMethodHints: Qt.ImhFormattedNumbersOnly
                        }
                    }

                    Rectangle {
                        id: smartFilterPanel
                        objectName: "smartFilterPanel"

                        Layout.fillWidth: true
                        implicitHeight: smartFilterLayout.implicitHeight + 20
                        radius: 8
                        color: theme.surfaceDeep
                        border.color: theme.border
                        border.width: 1

                        ColumnLayout {
                            id: smartFilterLayout

                            anchors.fill: parent
                            anchors.margins: 10
                            spacing: 5

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("Filtri integrati")
                                color: theme.textPrimary
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                            }

                            Text {
                                Layout.fillWidth: true
                                text: qsTr(
                                    "Seleziona i filtri presenti nel dispositivo. "
                                    + "NightScope segnala il dual-band nei consigli "
                                    + "per le nebulose; il filtro dark descrive la "
                                    + "calibrazione automatica."
                                )
                                color: theme.textSecondary
                                font.pixelSize: 11
                                wrapMode: Text.WordWrap
                            }

                            DarkCheckBox {
                                id: smartFilterUvIrCut
                                objectName: "smartFilterUvIrCut"
                                Layout.fillWidth: true
                                text: qsTr("UV/IR-cut (ripresa a banda larga)")
                            }

                            DarkCheckBox {
                                id: smartFilterDualBand
                                objectName: "smartFilterDualBand"
                                Layout.fillWidth: true
                                text: qsTr(
                                    "Dual-band Hα/OIII (nebulose e cielo urbano)"
                                )
                            }

                            DarkCheckBox {
                                id: smartFilterDark
                                objectName: "smartFilterDark"
                                Layout.fillWidth: true
                                text: qsTr("Filtro dark (calibrazione automatica)")
                            }

                            DarkCheckBox {
                                id: smartAdditionalFilters
                                objectName: "smartAdditionalFilters"
                                Layout.fillWidth: true
                                text: qsTr("Altri filtri non elencati")
                            }

                            DarkTextField {
                                id: smartAdditionalFilterNames
                                objectName: "smartAdditionalFilterNames"
                                visible: smartAdditionalFilters.checked
                                Layout.fillWidth: true
                                labelText: qsTr("Altri filtri (facoltativo)")
                                placeholderText: qsTr("H-alpha; OIII")
                            }

                            Text {
                                visible: smartAdditionalFilters.checked
                                Layout.fillWidth: true
                                text: qsTr(
                                    "Scrivi nomi brevi separati da punto e virgola, "
                                    + "per esempio H-alpha; OIII."
                                )
                                color: theme.textMuted
                                font.pixelSize: 10
                                wrapMode: Text.WordWrap
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: telescopeDialog.width < 620 ? 1 : 2
                        uniformCellWidths: true
                        columnSpacing: 8
                        rowSpacing: 4

                        DarkCheckBox {
                            id: smartLiveStacking
                            Layout.fillWidth: true
                            text: qsTr("Live stacking / EAA")
                        }
                        DarkCheckBox {
                            id: smartVideo
                            Layout.fillWidth: true
                            text: qsTr("Video lunare e planetario")
                        }
                        DarkCheckBox {
                            id: smartMosaic
                            Layout.fillWidth: true
                            text: qsTr("Mosaico automatico")
                        }
                        DarkCheckBox {
                            id: smartOpticalVisual
                            Layout.fillWidth: true
                            text: qsTr("Osservazione ottica visuale")
                        }
                        DarkCheckBox {
                            id: smartEyepieces
                            Layout.fillWidth: true
                            enabled: smartOpticalVisual.checked
                            text: qsTr("Oculari intercambiabili")
                        }
                        DarkCheckBox {
                            id: smartExternalCameras
                            Layout.fillWidth: true
                            text: qsTr("Camere esterne supportate")
                        }
                        DarkCheckBox {
                            id: smartExternalModifiers
                            Layout.fillWidth: true
                            text: qsTr("Barlow e riduttori esterni supportati")
                        }
                    }

                    DarkTextField {
                        id: smartSource
                        Layout.fillWidth: true
                        labelText: qsTr(
                            "Fonte ufficiale delle specifiche (URL)"
                        )
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            visible: controller.equipmentMessage.length > 0
            text: controller.equipmentMessage
            color: theme.red
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: deleteTelescopeDialog
        title: qsTr("Elimina modello")
        acceptText: controller.equipmentUsage("telescope", root.deleteModel.catalog_id || "") > 0 ? qsTr("Rimuovi dai profili e continua") : qsTr("Elimina")
        acceptDanger: true
        onAccepted: controller.deleteTelescopeModel(root.deleteModel.id, controller.equipmentUsage("telescope", root.deleteModel.catalog_id || "") > 0)

        Text {
            Layout.fillWidth: true
            text: controller.equipmentUsage("telescope", root.deleteModel.catalog_id || "") > 0
                ? qsTr("Questo elemento è utilizzato da uno o più profili.")
                : qsTr("Eliminare il modello dal catalogo?")
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }
}

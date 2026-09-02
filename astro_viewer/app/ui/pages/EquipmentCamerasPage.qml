// Purpose: Present astronomy-camera and camera-body catalogue CRUD workflows.
// Contract: Collects sensor metadata while canonicalization and persistence stay behind controller slots.

pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var editAstronomyCamera: ({})
    property var editCameraBody: ({})
    property var deleteAstronomyCamera: ({})
    property var deleteCameraBody: ({})
    property string cameraSearch: ""

    function numberValue(value) {
        return Number(String(value).trim().replace(",", "."))
    }

    function localizedNumber(value) {
        if (value === undefined || value === null || value === "")
            return ""
        var number = Number(value)
        return isFinite(number) ? number.toLocaleString(Qt.locale()) : String(value)
    }

    function isPositiveNumber(value) {
        var number = root.numberValue(value)
        return isFinite(number) && number > 0
    }

    function isPositiveInteger(value) {
        var number = root.numberValue(value)
        return isFinite(number) && number > 0 && Math.floor(number) === number
    }

    function optionalPositiveNumber(value) {
        return String(value).trim().length === 0 || root.isPositiveNumber(value)
    }

    function optionalPositiveInteger(value) {
        return String(value).trim().length === 0 || root.isPositiveInteger(value)
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

    function astronomyCameraFormValid() {
        return astronomyBrand.text.trim().length > 0
            && astronomyModel.text.trim().length > 0
            && astronomySensorModel.text.trim().length > 0
            && root.isPositiveNumber(astronomySensorWidth.text)
            && root.isPositiveNumber(astronomySensorHeight.text)
            && root.isPositiveInteger(astronomyResolutionWidth.text)
            && root.isPositiveInteger(astronomyResolutionHeight.text)
            && root.isPositiveNumber(astronomyPixelSize.text)
            && root.isPositiveInteger(astronomyBitDepth.text)
            && root.optionalPositiveNumber(astronomyMaxFps.text)
            && root.optionalPositiveNumber(astronomyCoolingDelta.text)
            && root.optionalPositiveNumber(astronomyBackfocus.text)
    }

    function cameraBodyFormValid() {
        var videoFields = [
            cameraVideoWidth.text.trim(),
            cameraVideoHeight.text.trim(),
            cameraVideoFps.text.trim()
        ]
        var videoCount = 0
        for (var index = 0; index < videoFields.length; index += 1) {
            if (videoFields[index].length > 0)
                videoCount += 1
        }
        return cameraBodyBrand.text.trim().length > 0
            && cameraBodyModel.text.trim().length > 0
            && cameraLensMount.text.trim().length > 0
            && root.isPositiveNumber(cameraSensorWidth.text)
            && root.isPositiveNumber(cameraSensorHeight.text)
            && root.isPositiveInteger(cameraResolutionWidth.text)
            && root.isPositiveInteger(cameraResolutionHeight.text)
            && root.isPositiveInteger(cameraRawBitDepth.text)
            && (videoCount === 0 || (
                videoCount === 3
                && root.optionalPositiveInteger(cameraVideoWidth.text)
                && root.optionalPositiveInteger(cameraVideoHeight.text)
                && root.optionalPositiveNumber(cameraVideoFps.text)
            ))
    }

    function openAstronomyCameraDialog(item) {
        editAstronomyCamera = item || ({})
        astronomyBrand.text = item ? item.brand : ""
        astronomyModel.text = item ? item.model : ""
        astronomyClass.currentIndex = root.optionIndex(
            controller.astronomyCameraClassOptions,
            item ? item.camera_class : "",
            "DEEP_SKY"
        )
        astronomySensorModel.text = item ? item.sensor_model : ""
        astronomyTechnology.currentIndex = root.optionIndex(
            controller.sensorTechnologyOptions,
            item ? item.sensor_technology : "",
            "CMOS"
        )
        astronomyColorMode.currentIndex = root.optionIndex(
            controller.sensorColorModeOptions,
            item ? item.color_mode : "",
            "COLOR"
        )
        astronomySensorWidth.text = item ? root.localizedNumber(item.sensor_width_mm) : ""
        astronomySensorHeight.text = item ? root.localizedNumber(item.sensor_height_mm) : ""
        astronomyResolutionWidth.text = item ? String(item.resolution_width_px) : ""
        astronomyResolutionHeight.text = item ? String(item.resolution_height_px) : ""
        astronomyPixelSize.text = item ? root.localizedNumber(item.pixel_size_um) : ""
        astronomyBitDepth.text = item ? String(item.bit_depth) : ""
        astronomyMaxFps.text = item ? root.localizedNumber(item.max_fps) : ""
        astronomyCooled.checked = item ? Boolean(item.cooled) : false
        astronomyCoolingDelta.text = item
            ? root.localizedNumber(item.cooling_delta_c) : ""
        astronomyShutter.currentIndex = root.optionIndex(
            controller.sensorShutterOptions,
            item ? item.shutter_type : "",
            "ROLLING"
        )
        astronomyBackfocus.text = item ? root.localizedNumber(item.backfocus_mm) : ""
        astronomySource.text = item ? (item.source_url || "") : ""
        astronomyCameraDialog.title = item
            ? qsTr("Modifica camera astronomica")
            : qsTr("Aggiungi camera astronomica")
        astronomyCameraDialog.open()
    }

    function openCameraBodyDialog(item) {
        editCameraBody = item || ({})
        cameraBodyBrand.text = item ? item.brand : ""
        cameraBodyModel.text = item ? item.model : ""
        cameraBodyType.currentIndex = root.optionIndex(
            controller.cameraBodyTypeOptions,
            item ? item.body_type : "",
            "MIRRORLESS"
        )
        cameraSensorFormat.currentIndex = root.optionIndex(
            controller.cameraSensorFormatOptions,
            item ? item.sensor_format : "",
            "FULL_FRAME"
        )
        cameraLensMount.text = item ? item.lens_mount : ""
        cameraSensorWidth.text = item ? root.localizedNumber(item.sensor_width_mm) : ""
        cameraSensorHeight.text = item ? root.localizedNumber(item.sensor_height_mm) : ""
        cameraResolutionWidth.text = item ? String(item.resolution_width_px) : ""
        cameraResolutionHeight.text = item ? String(item.resolution_height_px) : ""
        cameraRawBitDepth.text = item ? String(item.raw_bit_depth) : ""
        cameraVideoWidth.text = item && item.max_video_width_px
            ? String(item.max_video_width_px) : ""
        cameraVideoHeight.text = item && item.max_video_height_px
            ? String(item.max_video_height_px) : ""
        cameraVideoFps.text = item ? root.localizedNumber(item.max_video_fps) : ""
        cameraLiveView.checked = item ? Boolean(item.live_view) : true
        cameraBulbMode.checked = item ? Boolean(item.bulb_mode) : true
        cameraBodySource.text = item ? (item.source_url || "") : ""
        cameraBodyDialog.title = item
            ? qsTr("Modifica corpo macchina")
            : qsTr("Aggiungi corpo macchina")
        cameraBodyDialog.open()
    }

    function astronomyCameraPayload() {
        return {
            "brand": astronomyBrand.text,
            "model": astronomyModel.text,
            "camera_class": String(astronomyClass.currentValue || ""),
            "sensor_model": astronomySensorModel.text,
            "sensor_technology": String(astronomyTechnology.currentValue || ""),
            "color_mode": String(astronomyColorMode.currentValue || ""),
            "sensor_width_mm": astronomySensorWidth.text,
            "sensor_height_mm": astronomySensorHeight.text,
            "resolution_width_px": astronomyResolutionWidth.text,
            "resolution_height_px": astronomyResolutionHeight.text,
            "pixel_size_um": astronomyPixelSize.text,
            "bit_depth": astronomyBitDepth.text,
            "max_fps": astronomyMaxFps.text,
            "cooled": astronomyCooled.checked,
            "cooling_delta_c": astronomyCoolingDelta.text,
            "shutter_type": String(astronomyShutter.currentValue || ""),
            "backfocus_mm": astronomyBackfocus.text,
            "source_url": astronomySource.text
        }
    }

    function cameraBodyPayload() {
        return {
            "brand": cameraBodyBrand.text,
            "model": cameraBodyModel.text,
            "body_type": String(cameraBodyType.currentValue || ""),
            "sensor_format": String(cameraSensorFormat.currentValue || ""),
            "lens_mount": cameraLensMount.text,
            "sensor_width_mm": cameraSensorWidth.text,
            "sensor_height_mm": cameraSensorHeight.text,
            "resolution_width_px": cameraResolutionWidth.text,
            "resolution_height_px": cameraResolutionHeight.text,
            "raw_bit_depth": cameraRawBitDepth.text,
            "max_video_width_px": cameraVideoWidth.text,
            "max_video_height_px": cameraVideoHeight.text,
            "max_video_fps": cameraVideoFps.text,
            "live_view": cameraLiveView.checked,
            "bulb_mode": cameraBulbMode.checked,
            "source_url": cameraBodySource.text
        }
    }

    function searchText() {
        return root.cameraSearch.toLowerCase().trim()
    }

    function filteredAstronomyCameras() {
        var query = root.searchText()
        return controller.astronomyCameraCatalog.filter(function(item) {
            if (query.length === 0)
                return true
            var text = (
                item.brand + " " + item.model + " " + item.sensor_model + " "
                + item.camera_class_label + " " + item.color_mode_label
            ).toLowerCase()
            return text.indexOf(query) >= 0
        })
    }

    function filteredCameraBodies() {
        var query = root.searchText()
        return controller.cameraBodyCatalog.filter(function(item) {
            if (query.length === 0)
                return true
            var text = (
                item.brand + " " + item.model + " " + item.body_type_label + " "
                + item.sensor_format_label + " " + item.lens_mount
            ).toLowerCase()
            return text.indexOf(query) >= 0
        })
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
                    text: qsTr("Catalogo Cameras")
                    color: theme.textPrimary
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Camere assegnabili ai profili, predisposte per il futuro motore fotografico")
                    color: theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }

            DarkTextField {
                Layout.preferredWidth: 330
                placeholderText: qsTr("Cerca camera, sensore o formato...")
                onTextChanged: root.cameraSearch = text
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

            CameraColumn {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("Camere astronomiche")
                countText: qsTr("%1 di %2 camere")
                    .arg(root.filteredAstronomyCameras().length)
                    .arg(root.controller.astronomyCameraCatalog.length)
                addText: qsTr("Aggiungi camera")
                accent: theme.cyan
                items: root.filteredAstronomyCameras()
                astronomyCamera: true
                emptyText: qsTr("Nessuna camera astronomica trovata.")
                onAddRequested: root.openAstronomyCameraDialog(null)
                onEditRequested: function(item) {
                    root.openAstronomyCameraDialog(item)
                }
                onDeleteRequested: function(item) {
                    root.deleteAstronomyCamera = item
                    deleteAstronomyCameraDialog.open()
                }
            }

            CameraColumn {
                Layout.fillWidth: true
                Layout.fillHeight: true
                title: qsTr("Corpi macchina")
                countText: qsTr("%1 di %2 corpi")
                    .arg(root.filteredCameraBodies().length)
                    .arg(root.controller.cameraBodyCatalog.length)
                addText: qsTr("Aggiungi corpo")
                accent: theme.amber
                items: root.filteredCameraBodies()
                astronomyCamera: false
                emptyText: qsTr("Nessun corpo macchina trovato.")
                onAddRequested: root.openCameraBodyDialog(null)
                onEditRequested: function(item) {
                    root.openCameraBodyDialog(item)
                }
                onDeleteRequested: function(item) {
                    root.deleteCameraBody = item
                    deleteCameraBodyDialog.open()
                }
            }
        }
    }

    component CameraColumn: Rectangle {
        id: cameraColumn
        property string title: ""
        property string countText: ""
        property string addText: ""
        property string emptyText: ""
        property color accent: theme.cyan
        property var items: []
        property bool astronomyCamera: false
        signal addRequested()
        signal editRequested(var item)
        signal deleteRequested(var item)

        radius: 8
        color: theme.surface
        border.color: theme.border
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
                    opacity: 0.7
                }

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 2

                    Text {
                        Layout.fillWidth: true
                        text: cameraColumn.title
                        color: theme.textPrimary
                        font.pixelSize: 16
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: cameraColumn.countText
                        color: theme.textSecondary
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }
                }

                DarkButton {
                    text: cameraColumn.addText
                    accentColor: cameraColumn.accent
                    onClicked: cameraColumn.addRequested()
                }
            }

            ScrollView {
                id: cameraScroll
                Layout.fillWidth: true
                Layout.fillHeight: true
                clip: true
                contentWidth: Math.max(0, availableWidth - 14)

                ColumnLayout {
                    width: Math.max(0, cameraScroll.availableWidth - 14)
                    spacing: 10

                    Repeater {
                        model: cameraColumn.items

                        delegate: CameraCard {
                            required property var modelData
                            itemData: modelData
                            astronomyCamera: cameraColumn.astronomyCamera
                            accent: cameraColumn.accent
                            onEdit: cameraColumn.editRequested(modelData)
                            onDeleteRequested: cameraColumn.deleteRequested(modelData)
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        visible: cameraColumn.items.length === 0
                        text: cameraColumn.emptyText
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    component CameraCard: Rectangle {
        id: cameraCard
        property var itemData
        property bool astronomyCamera: false
        property color accent: theme.cyan
        signal edit()
        signal deleteRequested()

        Layout.fillWidth: true
        implicitHeight: cardContent.implicitHeight + 22
        radius: 8
        color: theme.surfaceRaised
        border.color: theme.border
        border.width: 1

        ColumnLayout {
            id: cardContent
            anchors.fill: parent
            anchors.margins: 11
            spacing: 7

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: cameraCard.itemData.display_name
                    color: theme.textPrimary
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    wrapMode: Text.WordWrap
                    elide: Text.ElideRight
                    maximumLineCount: 2
                }

                DarkButton {
                    visible: String(cameraCard.itemData.source_url || "").length > 0
                    text: qsTr("Scheda")
                    onClicked: Qt.openUrlExternally(cameraCard.itemData.source_url)
                }

                DarkButton {
                    text: qsTr("Modifica")
                    onClicked: cameraCard.edit()
                }

                DarkButton {
                    visible: !cameraCard.itemData.is_builtin
                    text: qsTr("Elimina")
                    danger: true
                    onClicked: cameraCard.deleteRequested()
                }
            }

            Text {
                Layout.fillWidth: true
                text: cameraCard.astronomyCamera
                    ? cameraCard.itemData.sensor_model + "  -  "
                        + cameraCard.itemData.camera_class_label
                    : cameraCard.itemData.body_type_label + "  -  "
                        + cameraCard.itemData.lens_mount
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8

                StatusPill {
                    text: cameraCard.itemData.sensor_format_label
                        || cameraCard.itemData.sensor_size_label
                    accentColor: cameraCard.accent
                }
                StatusPill {
                    text: cameraCard.itemData.resolution_label
                    accentColor: theme.teal
                }
                StatusPill {
                    text: cameraCard.itemData.pixel_size_label
                    accentColor: theme.violet
                }
                StatusPill {
                    visible: cameraCard.astronomyCamera
                    text: cameraCard.astronomyCamera
                        ? cameraCard.itemData.color_mode_label : ""
                    accentColor: theme.amber
                }
                StatusPill {
                    visible: cameraCard.astronomyCamera
                    text: cameraCard.astronomyCamera
                        ? cameraCard.itemData.cooling_label : ""
                    accentColor: cameraCard.itemData.cooled
                        ? theme.cyan : theme.textMuted
                }
                StatusPill {
                    visible: !cameraCard.astronomyCamera
                    text: cameraCard.astronomyCamera
                        ? "" : cameraCard.itemData.raw_bit_depth_label
                    accentColor: theme.amber
                }
                StatusPill {
                    visible: !cameraCard.astronomyCamera
                        && String(
                            cameraCard.itemData.max_video_label || ""
                        ).length > 0
                    text: cameraCard.astronomyCamera
                        ? "" : cameraCard.itemData.max_video_label
                    accentColor: theme.cyan
                }
            }
        }
    }

    DarkDialog {
        id: astronomyCameraDialog
        preferredWidth: 900
        title: qsTr("Aggiungi camera astronomica")
        acceptText: qsTr("Salva")
        closeOnAccept: false
        acceptEnabled: root.astronomyCameraFormValid()
        onOpened: root.controller.clearCameraCatalogMessage()
        onAccepted: {
            var saved
            var payload = root.astronomyCameraPayload()
            if (root.editAstronomyCamera.id !== undefined)
                saved = root.controller.updateAstronomyCameraModel(
                    root.editAstronomyCamera.id,
                    payload
                )
            else
                saved = root.controller.addAstronomyCameraModel(payload)
            if (saved)
                astronomyCameraDialog.close()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 3
            uniformCellWidths: true
            columnSpacing: 8
            rowSpacing: 8

            DarkTextField { id: astronomyBrand; Layout.fillWidth: true; labelText: qsTr("Marca *") }
            DarkTextField { id: astronomyModel; Layout.fillWidth: true; labelText: qsTr("Modello *") }
            DarkComboBox {
                id: astronomyClass
                Layout.fillWidth: true
                labelText: qsTr("Impiego *")
                model: root.controller.astronomyCameraClassOptions
                textRole: "label"
                valueRole: "code"
            }

            DarkTextField { id: astronomySensorModel; Layout.fillWidth: true; labelText: qsTr("Modello sensore *") }
            DarkComboBox {
                id: astronomyTechnology
                Layout.fillWidth: true
                labelText: qsTr("Tecnologia sensore *")
                model: root.controller.sensorTechnologyOptions
                textRole: "label"
                valueRole: "code"
            }
            DarkComboBox {
                id: astronomyColorMode
                Layout.fillWidth: true
                labelText: qsTr("Modalità colore *")
                model: root.controller.sensorColorModeOptions
                textRole: "label"
                valueRole: "code"
            }

            DarkTextField { id: astronomySensorWidth; Layout.fillWidth: true; labelText: qsTr("Larghezza sensore (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: astronomySensorHeight; Layout.fillWidth: true; labelText: qsTr("Altezza sensore (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: astronomyPixelSize; Layout.fillWidth: true; labelText: qsTr("Passo pixel (µm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }

            DarkTextField { id: astronomyResolutionWidth; Layout.fillWidth: true; labelText: qsTr("Risoluzione orizzontale (px) *"); inputMethodHints: Qt.ImhDigitsOnly }
            DarkTextField { id: astronomyResolutionHeight; Layout.fillWidth: true; labelText: qsTr("Risoluzione verticale (px) *"); inputMethodHints: Qt.ImhDigitsOnly }
            DarkTextField { id: astronomyBitDepth; Layout.fillWidth: true; labelText: qsTr("Profondità (bit) *"); inputMethodHints: Qt.ImhDigitsOnly }

            DarkTextField { id: astronomyMaxFps; Layout.fillWidth: true; labelText: qsTr("FPS a piena risoluzione (facoltativo)"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkComboBox {
                id: astronomyShutter
                Layout.fillWidth: true
                labelText: qsTr("Otturatore *")
                model: root.controller.sensorShutterOptions
                textRole: "label"
                valueRole: "code"
            }
            DarkTextField { id: astronomyBackfocus; Layout.fillWidth: true; labelText: qsTr("Backfocus (mm; facoltativo)"); inputMethodHints: Qt.ImhFormattedNumbersOnly }

            DarkCheckBox { id: astronomyCooled; Layout.fillWidth: true; text: qsTr("Raffreddata") }
            DarkTextField {
                id: astronomyCoolingDelta
                Layout.fillWidth: true
                enabled: astronomyCooled.checked
                labelText: qsTr("ΔT massimo sotto ambiente (°C)")
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }

            DarkTextField {
                id: astronomySource
                Layout.columnSpan: 3
                Layout.fillWidth: true
                labelText: qsTr("Scheda tecnica URL (facoltativa)")
            }
        }

        Text {
            Layout.fillWidth: true
            visible: root.controller.cameraCatalogMessage.length > 0
            text: root.controller.cameraCatalogMessage
            color: theme.red
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: cameraBodyDialog
        preferredWidth: 900
        title: qsTr("Aggiungi corpo macchina")
        acceptText: qsTr("Salva")
        closeOnAccept: false
        acceptEnabled: root.cameraBodyFormValid()
        onOpened: root.controller.clearCameraCatalogMessage()
        onAccepted: {
            var saved
            var payload = root.cameraBodyPayload()
            if (root.editCameraBody.id !== undefined)
                saved = root.controller.updateCameraBodyModel(
                    root.editCameraBody.id,
                    payload
                )
            else
                saved = root.controller.addCameraBodyModel(payload)
            if (saved)
                cameraBodyDialog.close()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 3
            uniformCellWidths: true
            columnSpacing: 8
            rowSpacing: 8

            DarkTextField { id: cameraBodyBrand; Layout.fillWidth: true; labelText: qsTr("Marca *") }
            DarkTextField { id: cameraBodyModel; Layout.fillWidth: true; labelText: qsTr("Modello *") }
            DarkComboBox {
                id: cameraBodyType
                Layout.fillWidth: true
                labelText: qsTr("Tipo corpo *")
                model: root.controller.cameraBodyTypeOptions
                textRole: "label"
                valueRole: "code"
            }

            DarkComboBox {
                id: cameraSensorFormat
                Layout.fillWidth: true
                labelText: qsTr("Formato sensore *")
                model: root.controller.cameraSensorFormatOptions
                textRole: "label"
                valueRole: "code"
            }
            DarkTextField { id: cameraLensMount; Layout.fillWidth: true; labelText: qsTr("Baionetta *") }
            DarkTextField { id: cameraRawBitDepth; Layout.fillWidth: true; labelText: qsTr("Profondità RAW (bit) *"); inputMethodHints: Qt.ImhDigitsOnly }

            DarkTextField { id: cameraSensorWidth; Layout.fillWidth: true; labelText: qsTr("Larghezza sensore (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: cameraSensorHeight; Layout.fillWidth: true; labelText: qsTr("Altezza sensore (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }

            DarkTextField { id: cameraResolutionWidth; Layout.fillWidth: true; labelText: qsTr("Risoluzione orizzontale (px) *"); inputMethodHints: Qt.ImhDigitsOnly }
            DarkTextField { id: cameraResolutionHeight; Layout.fillWidth: true; labelText: qsTr("Risoluzione verticale (px) *"); inputMethodHints: Qt.ImhDigitsOnly }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }

            DarkTextField { id: cameraVideoWidth; Layout.fillWidth: true; labelText: qsTr("Risoluzione video orizzontale (px)"); inputMethodHints: Qt.ImhDigitsOnly }
            DarkTextField { id: cameraVideoHeight; Layout.fillWidth: true; labelText: qsTr("Risoluzione video verticale (px)"); inputMethodHints: Qt.ImhDigitsOnly }
            DarkTextField { id: cameraVideoFps; Layout.fillWidth: true; labelText: qsTr("FPS alla risoluzione video indicata"); inputMethodHints: Qt.ImhFormattedNumbersOnly }

            DarkCheckBox { id: cameraLiveView; Layout.fillWidth: true; text: qsTr("Live View") }
            DarkCheckBox { id: cameraBulbMode; Layout.fillWidth: true; text: qsTr("Modalità Bulb") }
            Item { Layout.fillWidth: true; Layout.preferredHeight: 1 }

            DarkTextField {
                id: cameraBodySource
                Layout.columnSpan: 3
                Layout.fillWidth: true
                labelText: qsTr("Scheda tecnica URL (facoltativa)")
            }
        }

        Text {
            Layout.fillWidth: true
            visible: root.controller.cameraCatalogMessage.length > 0
            text: root.controller.cameraCatalogMessage
            color: theme.red
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: deleteAstronomyCameraDialog
        title: qsTr("Elimina camera astronomica")
        acceptText: root.controller.equipmentUsage(
            "astronomy_camera",
            root.deleteAstronomyCamera.catalog_id || ""
        ) > 0 ? qsTr("Rimuovi dai profili e continua") : qsTr("Elimina")
        acceptDanger: true
        onAccepted: root.controller.deleteAstronomyCameraModel(
            root.deleteAstronomyCamera.id,
            root.controller.equipmentUsage(
                "astronomy_camera",
                root.deleteAstronomyCamera.catalog_id || ""
            ) > 0
        )

        Text {
            Layout.fillWidth: true
            text: root.controller.equipmentUsage(
                "astronomy_camera",
                root.deleteAstronomyCamera.catalog_id || ""
            ) > 0
                ? qsTr("Questo elemento è utilizzato da uno o più profili.")
                : qsTr("Eliminare la camera astronomica dal catalogo?")
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: deleteCameraBodyDialog
        title: qsTr("Elimina corpo macchina")
        acceptText: root.controller.equipmentUsage(
            "camera_body",
            root.deleteCameraBody.catalog_id || ""
        ) > 0 ? qsTr("Rimuovi dai profili e continua") : qsTr("Elimina")
        acceptDanger: true
        onAccepted: root.controller.deleteCameraBodyModel(
            root.deleteCameraBody.id,
            root.controller.equipmentUsage(
                "camera_body",
                root.deleteCameraBody.catalog_id || ""
            ) > 0
        )

        Text {
            Layout.fillWidth: true
            text: root.controller.equipmentUsage(
                "camera_body",
                root.deleteCameraBody.catalog_id || ""
            ) > 0
                ? qsTr("Questo elemento è utilizzato da uno o più profili.")
                : qsTr("Eliminare il corpo macchina dal catalogo?")
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }
}

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

    function isPositiveInteger(value) {
        var number = Number(String(value).trim().replace(",", "."))
        return isFinite(number) && number > 0 && Math.floor(number) === number
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
        implicitHeight: 116
        radius: 8
                        color: theme.surfaceRaised
                        border.color: theme.border
        border.width: 1

        ColumnLayout {
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
                    String(telescopeCategory.currentValue || "")
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
                    String(telescopeCategory.currentValue || "")
                )
            }
            if (saved)
                telescopeDialog.close()
        }

        GridLayout {
            id: telescopeForm
            objectName: "telescopeForm"
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
                visible: String(telescopeType.currentValue || "") === "OTHER"
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

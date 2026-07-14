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

    function openEditDialog(item) {
        editModel = item
        telescopeBrand.text = item.brand || ""
        telescopeName.text = item.name || ""
        telescopeType.text = item.optical_type || ""
        telescopeAperture.text = String(item.aperture_mm || "")
        telescopeFocal.text = String(item.focal_length_mm || "")
        telescopeMount.text = item.mount_type || ""
        telescopeNotes.text = item.notes || ""
        telescopeDialog.title = qsTr("Modifica modello")
        telescopeDialog.open()
    }

    function openAddDialog() {
        editModel = ({})
        telescopeBrand.text = ""
        telescopeName.text = ""
        telescopeType.text = ""
        telescopeAperture.text = ""
        telescopeFocal.text = ""
        telescopeMount.text = ""
        telescopeNotes.text = ""
        telescopeDialog.title = qsTr("Aggiungi modello")
        telescopeDialog.open()
    }

    function matchesTelescope(item) {
        var query = root.telescopeSearch.toLowerCase().trim()
        if (query.length === 0)
            return true
        var text = (item.brand + " " + item.name + " " + item.optical_type).toLowerCase()
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
        color: "#20242b"
        border.color: "#303641"
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
                text: itemData.optical_type + "  -  " + itemData.mount_type
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8
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
        title: qsTr("Aggiungi modello")
        acceptText: qsTr("Salva")
        closeOnAccept: false
        acceptEnabled: telescopeBrand.text.trim().length > 0
            && telescopeName.text.trim().length > 0
            && telescopeType.text.trim().length > 0
            && root.isPositiveInteger(telescopeAperture.text)
            && root.isPositiveInteger(telescopeFocal.text)
            && telescopeMount.text.trim().length > 0
        onOpened: controller.clearEquipmentMessage()
        onAccepted: {
            var saved
            if (root.editModel.id !== undefined) {
                saved = controller.updateTelescopeModel(root.editModel.id, telescopeBrand.text, telescopeName.text, telescopeType.text, telescopeAperture.text, telescopeFocal.text, telescopeMount.text, telescopeNotes.text)
            } else {
                saved = controller.addTelescopeModel(telescopeBrand.text, telescopeName.text, telescopeType.text, telescopeAperture.text, telescopeFocal.text, telescopeMount.text, telescopeNotes.text)
            }
            if (saved)
                telescopeDialog.close()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            DarkTextField { id: telescopeBrand; Layout.fillWidth: true; placeholderText: qsTr("Marca *") }
            DarkTextField { id: telescopeName; Layout.fillWidth: true; placeholderText: qsTr("Modello *") }
            DarkTextField { id: telescopeType; Layout.fillWidth: true; placeholderText: qsTr("Tipo ottico *") }
            DarkTextField { id: telescopeAperture; Layout.fillWidth: true; placeholderText: qsTr("Apertura (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: telescopeFocal; Layout.fillWidth: true; placeholderText: qsTr("Focale (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: telescopeMount; Layout.fillWidth: true; placeholderText: qsTr("Montatura *") }
            DarkTextField { id: telescopeNotes; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: qsTr("Note (facoltative)") }
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

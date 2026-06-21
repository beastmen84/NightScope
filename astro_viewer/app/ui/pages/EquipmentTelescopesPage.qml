import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var editModel: ({})
    property var deleteModel: ({})

    function openEditDialog(item) {
        editModel = item
        telescopeBrand.text = item.brand || ""
        telescopeName.text = item.name || ""
        telescopeType.text = item.optical_type || ""
        telescopeAperture.text = String(item.aperture_mm || "")
        telescopeFocal.text = String(item.focal_length_mm || "")
        telescopeMount.text = item.mount_type || ""
        telescopeNotes.text = item.notes || ""
        telescopeDialog.title = "Modifica modello"
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
        telescopeDialog.title = "Aggiungi modello"
        telescopeDialog.open()
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

            ColumnLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                spacing: 6

                Text {
                    Layout.fillWidth: true
                    text: "Catalogo telescopi"
                    color: theme.textPrimary
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: "Modelli disponibili per i profili osservativi"
                    color: theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Catalogo telescopi"
                subtitle: controller.telescopeCatalogModels.length + " modelli"
                accentColor: theme.cyan

                Repeater {
                    model: controller.telescopeCatalogModels

                    delegate: Rectangle {
                        Layout.fillWidth: true
                        implicitHeight: 76
                        radius: 8
                        color: "#20242b"
                        border.color: "#303641"
                        border.width: 1

                        RowLayout {
                            anchors.fill: parent
                            anchors.margins: 12
                            spacing: 10

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.brand + " " + modelData.name
                                    color: theme.textPrimary
                                    font.pixelSize: 15
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.optical_type + "  -  " + modelData.mount_type
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }

                            StatusPill { text: modelData.aperture_mm + " mm"; accentColor: theme.cyan }
                            StatusPill { text: modelData.focal_length_mm + " mm"; accentColor: theme.teal }

                            Button {
                                text: "Modifica"
                                onClicked: root.openEditDialog(modelData)
                            }

                            Button {
                                text: "Elimina"
                                onClicked: {
                                    root.deleteModel = modelData
                                    deleteTelescopeDialog.open()
                                }
                            }
                        }
                    }
                }

                Button {
                    Layout.fillWidth: true
                    text: "Aggiungi modello"
                    onClicked: root.openAddDialog()
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    DarkDialog {
        id: telescopeDialog
        title: "Aggiungi modello"
        acceptText: "Salva"
        onAccepted: {
            if (root.editModel.id !== undefined) {
                controller.updateTelescopeModel(root.editModel.id, telescopeBrand.text, telescopeName.text, telescopeType.text, telescopeAperture.text, telescopeFocal.text, telescopeMount.text, telescopeNotes.text)
            } else {
                controller.addTelescopeModel(telescopeBrand.text, telescopeName.text, telescopeType.text, telescopeAperture.text, telescopeFocal.text, telescopeMount.text, telescopeNotes.text)
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: telescopeBrand; Layout.fillWidth: true; placeholderText: "Brand" }
            TextField { id: telescopeName; Layout.fillWidth: true; placeholderText: "Modello" }
            TextField { id: telescopeType; Layout.fillWidth: true; placeholderText: "Tipo ottico" }
            TextField { id: telescopeAperture; Layout.fillWidth: true; placeholderText: "Apertura mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: telescopeFocal; Layout.fillWidth: true; placeholderText: "Focale mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: telescopeMount; Layout.fillWidth: true; placeholderText: "Montatura" }
            TextField { id: telescopeNotes; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: "Note" }
        }
    }

    DarkDialog {
        id: deleteTelescopeDialog
        title: "Elimina modello"
        showAccept: false

        Text {
            Layout.fillWidth: true
            text: controller.equipmentUsage("telescope", root.deleteModel.catalog_id || "") > 0
                ? "Questo elemento e utilizzato da uno o piu profili."
                : "Eliminare il modello dal catalogo?"
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10

            Button {
                Layout.fillWidth: true
                text: "Annulla"
                onClicked: deleteTelescopeDialog.close()
            }

            Button {
                Layout.fillWidth: true
                text: controller.equipmentUsage("telescope", root.deleteModel.catalog_id || "") > 0 ? "Rimuovi dai profili e continua" : "Elimina"
                onClicked: {
                    controller.deleteTelescopeModel(root.deleteModel.id, controller.equipmentUsage("telescope", root.deleteModel.catalog_id || "") > 0)
                    deleteTelescopeDialog.close()
                }
            }
        }
    }
}

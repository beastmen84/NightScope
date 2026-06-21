import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var selectedCatalogModel: controller.telescopeCatalogModels.length > 0 && catalogModelCombo.currentIndex >= 0 ? controller.telescopeCatalogModels[catalogModelCombo.currentIndex] : ({})
    property var editTelescopeData: ({})

    function openEditDialog(telescope) {
        editTelescopeData = telescope
        editTelescopeName.text = telescope.name
        editTelescopeAperture.text = String(telescope.apertureMm)
        editTelescopeFocal.text = String(telescope.focalLengthMm)
        editTelescopeType.text = telescope.type
        editTelescopeMount.text = telescope.mount
        editTelescopeDialog.open()
    }

    AppTheme {
        id: theme
    }

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
                    text: "Telescopi"
                    color: theme.textPrimary
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: "Gestisci solo gli strumenti che possiedi. I cataloghi sono disponibili quando aggiungi un telescopio."
                    color: theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "My Telescopes"
                subtitle: controller.equipmentSetups.length + " telescopi posseduti"
                accentColor: theme.cyan

                Text {
                    Layout.fillWidth: true
                    visible: controller.equipmentSetups.length === 0
                    text: "Nessun telescopio configurato. NightScope usera automaticamente Occhio nudo."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }

                Repeater {
                    model: controller.equipmentSetups

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
                            spacing: 12

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: theme.textPrimary
                                    font.pixelSize: 16
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.type + "  -  " + modelData.mount
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    elide: Text.ElideRight
                                }
                            }

                            StatusPill { text: modelData.apertureMm + " mm"; accentColor: theme.cyan }
                            StatusPill { text: modelData.focalLengthMm + " mm"; accentColor: theme.teal }

                            Button {
                                text: "Edit"
                                onClicked: root.openEditDialog(modelData)
                            }

                            Button {
                                text: "Delete"
                                onClicked: controller.removeTelescope(modelData.id)
                            }
                        }
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Button {
                        Layout.fillWidth: true
                        text: "Add from Catalog"
                        onClicked: addCatalogTelescopeDialog.open()
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Add Custom"
                        onClicked: addCustomTelescopeDialog.open()
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Uso nei profili"
                subtitle: "Assegna i telescopi dalla pagina Profili"
                accentColor: theme.green

                Text {
                    Layout.fillWidth: true
                    text: "Aggiungere un telescopio lo rende disponibile. Per decidere quali strumenti usa il planner, apri Strumenti > Profili e assegnali al profilo attivo."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    Dialog {
        id: addCatalogTelescopeDialog
        title: "Add from Catalog"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (root.selectedCatalogModel.catalog_id) {
                controller.addCatalogTelescope(root.selectedCatalogModel.catalog_id)
            }
        }

        ColumnLayout {
            width: 520
            spacing: 10

            ComboBox {
                id: catalogModelCombo
                Layout.fillWidth: true
                model: controller.telescopeCatalogModels
                textRole: "name"
            }

            Text {
                Layout.fillWidth: true
                text: (root.selectedCatalogModel.brand || "") + "  -  " + (root.selectedCatalogModel.optical_type || "") + "  -  " + (root.selectedCatalogModel.mount_type || "")
                color: theme.textSecondary
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
        }
    }

    Dialog {
        id: addCustomTelescopeDialog
        title: "Add Custom Telescope"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: controller.addTelescope(telescopeName.text, telescopeAperture.text, telescopeFocal.text, telescopeType.currentText, telescopeMount.text)

        GridLayout {
            width: 520
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: telescopeName; Layout.fillWidth: true; placeholderText: "Nome" }
            TextField { id: telescopeAperture; Layout.fillWidth: true; placeholderText: "Apertura mm"; inputMethodHints: Qt.ImhDigitsOnly }
            TextField { id: telescopeFocal; Layout.fillWidth: true; placeholderText: "Focale mm"; inputMethodHints: Qt.ImhDigitsOnly }
            ComboBox {
                id: telescopeType
                Layout.fillWidth: true
                model: ["rifrattore", "Newton", "Schmidt-Cassegrain", "Maksutov"]
            }
            TextField { id: telescopeMount; Layout.fillWidth: true; placeholderText: "Montatura" }
        }
    }

    Dialog {
        id: editTelescopeDialog
        title: "Edit Telescope"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: controller.updateTelescope(root.editTelescopeData.id, editTelescopeName.text, editTelescopeAperture.text, editTelescopeFocal.text, editTelescopeType.text, editTelescopeMount.text)

        GridLayout {
            width: 520
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: editTelescopeName; Layout.fillWidth: true; placeholderText: "Nome" }
            TextField { id: editTelescopeAperture; Layout.fillWidth: true; placeholderText: "Apertura mm"; inputMethodHints: Qt.ImhDigitsOnly }
            TextField { id: editTelescopeFocal; Layout.fillWidth: true; placeholderText: "Focale mm"; inputMethodHints: Qt.ImhDigitsOnly }
            TextField { id: editTelescopeType; Layout.fillWidth: true; placeholderText: "Tipo ottico" }
            TextField { id: editTelescopeMount; Layout.fillWidth: true; placeholderText: "Montatura" }
        }
    }
}

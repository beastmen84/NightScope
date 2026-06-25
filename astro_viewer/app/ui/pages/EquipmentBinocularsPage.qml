import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var editModel: ({})
    property var deleteModel: ({})
    property string binocularSearch: ""

    function openEditDialog(item) {
        editModel = item
        binocularBrand.text = item.brand || ""
        binocularModel.text = item.model || ""
        binocularMagnification.text = String(item.magnification || "")
        binocularObjective.text = String(item.objective_diameter_mm || "")
        binocularFov.text = item.true_fov_deg ? String(item.true_fov_deg) : ""
        binocularWeight.text = item.weight_g ? String(item.weight_g) : ""
        binocularStabilized.checked = item.image_stabilized || false
        binocularNotes.text = item.notes || ""
        binocularDialog.title = "Modifica modello"
        binocularDialog.open()
    }

    function openAddDialog() {
        editModel = ({})
        binocularBrand.text = ""
        binocularModel.text = ""
        binocularMagnification.text = ""
        binocularObjective.text = ""
        binocularFov.text = ""
        binocularWeight.text = ""
        binocularStabilized.checked = false
        binocularNotes.text = ""
        binocularDialog.title = "Aggiungi modello"
        binocularDialog.open()
    }

    function matchesBinocular(item) {
        var query = root.binocularSearch.toLowerCase().trim()
        if (query.length === 0)
            return true
        var text = (item.brand + " " + item.model + " " + item.spec_label).toLowerCase()
        return text.indexOf(query) >= 0
    }

    function filteredBinocularModels() {
        return controller.binocularCatalog.filter(function(item) {
            return root.matchesBinocular(item)
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
                        text: "Binocoli"
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

                DarkTextField {
                    Layout.preferredWidth: 300
                    placeholderText: "Cerca binocolo..."
                    onTextChanged: root.binocularSearch = text
                }

                DarkButton {
                    text: "Aggiungi modello"
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
                    text: root.filteredBinocularModels().length + " di " + controller.binocularCatalog.length + " modelli"
                    color: theme.textSecondary
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                GridLayout {
                    id: binocularCatalogGrid
                    Layout.fillWidth: true
                    columns: root.width > 1060 ? 2 : 1
                    columnSpacing: 12
                    rowSpacing: 12

                    Repeater {
                        model: root.filteredBinocularModels()

                        delegate: BinocularCatalogCard {
                            itemData: modelData
                            onEdit: root.openEditDialog(modelData)
                            onDeleteRequested: {
                                root.deleteModel = modelData
                                deleteBinocularDialog.open()
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: root.filteredBinocularModels().length === 0
                    text: "Nessun binocolo trovato."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    component BinocularCatalogCard: Rectangle {
        id: binocularCard
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
                    text: itemData.brand + " " + itemData.model
                    color: theme.textPrimary
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                DarkButton {
                    text: "Modifica"
                    implicitHeight: 32
                    leftPadding: 10
                    rightPadding: 10
                    onClicked: binocularCard.edit()
                }

                DarkButton {
                    text: "Elimina"
                    implicitHeight: 32
                    leftPadding: 10
                    rightPadding: 10
                    danger: true
                    onClicked: binocularCard.deleteRequested()
                }
            }

            Text {
                Layout.fillWidth: true
                text: itemData.spec_label
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8
                StatusPill { text: itemData.spec_label; accentColor: theme.cyan }
                StatusPill { visible: itemData.fov_label.length > 0; text: itemData.fov_label; accentColor: theme.teal }
                StatusPill { visible: itemData.weight_label.length > 0; text: itemData.weight_label; accentColor: theme.amber }
                StatusPill { visible: itemData.image_stabilized; text: "IS"; accentColor: theme.violet }
            }
        }
    }

    DarkDialog {
        id: binocularDialog
        title: "Aggiungi modello"
        acceptText: "Salva"
        onAccepted: {
            if (root.editModel.id !== undefined) {
                controller.updateBinocularModel(root.editModel.id, binocularBrand.text, binocularModel.text, binocularMagnification.text, binocularObjective.text, binocularFov.text, binocularWeight.text, binocularStabilized.checked, binocularNotes.text)
            } else {
                controller.addBinocularModel(binocularBrand.text, binocularModel.text, binocularMagnification.text, binocularObjective.text, binocularFov.text, binocularWeight.text, binocularStabilized.checked, binocularNotes.text)
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            DarkTextField { id: binocularBrand; Layout.fillWidth: true; placeholderText: "Marca" }
            DarkTextField { id: binocularModel; Layout.fillWidth: true; placeholderText: "Modello" }
            DarkTextField { id: binocularMagnification; Layout.fillWidth: true; placeholderText: "Ingrandimento"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: binocularObjective; Layout.fillWidth: true; placeholderText: "Diametro obiettivo mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: binocularFov; Layout.fillWidth: true; placeholderText: "Campo reale °"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: binocularWeight; Layout.fillWidth: true; placeholderText: "Peso g"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            CheckBox { id: binocularStabilized; Layout.fillWidth: true; text: "Stabilizzato" }
            DarkTextField { id: binocularNotes; Layout.fillWidth: true; placeholderText: "Note" }
        }
    }

    DarkDialog {
        id: deleteBinocularDialog
        title: "Elimina modello"
        acceptText: "Elimina"
        acceptDanger: true
        onAccepted: controller.deleteBinocularModel(root.deleteModel.id)

        Text {
            Layout.fillWidth: true
            text: "Eliminare il modello dal catalogo?"
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }
}

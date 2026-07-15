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

    function isPositiveInteger(value) {
        var number = Number(String(value).trim().replace(",", "."))
        return isFinite(number) && number > 0 && Math.floor(number) === number
    }

    function openEditDialog(item) {
        editModel = item
        binocularBrand.text = item.brand || ""
        binocularModel.text = item.model || ""
        binocularMagnification.text = String(item.magnification || "")
        binocularObjective.text = String(item.objective_diameter_mm || "")
        binocularStabilized.checked = item.image_stabilized || false
        binocularDialog.title = qsTr("Modifica modello")
        binocularDialog.open()
    }

    function openAddDialog() {
        editModel = ({})
        binocularBrand.text = ""
        binocularModel.text = ""
        binocularMagnification.text = ""
        binocularObjective.text = ""
        binocularStabilized.checked = false
        binocularDialog.title = qsTr("Aggiungi modello")
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
                        text: qsTr("Catalogo binocoli")
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
                    placeholderText: qsTr("Cerca binocolo...")
                    onTextChanged: root.binocularSearch = text
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
                        .arg(root.filteredBinocularModels().length)
                        .arg(controller.binocularCatalog.length)
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
                    text: qsTr("Nessun binocolo trovato.")
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
                    text: qsTr("Modifica")
                    implicitHeight: 32
                    leftPadding: 10
                    rightPadding: 10
                    onClicked: binocularCard.edit()
                }

                DarkButton {
                    visible: !itemData.is_builtin
                    text: qsTr("Elimina")
                    implicitHeight: 32
                    leftPadding: 10
                    rightPadding: 10
                    danger: true
                    onClicked: binocularCard.deleteRequested()
                }
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8
                StatusPill { text: itemData.spec_label; accentColor: theme.cyan }
                StatusPill { visible: itemData.image_stabilized; text: qsTr("IS"); accentColor: theme.violet }
            }
        }
    }

    DarkDialog {
        id: binocularDialog
        title: qsTr("Aggiungi modello")
        acceptText: qsTr("Salva")
        closeOnAccept: false
        acceptEnabled: binocularBrand.text.trim().length > 0
            && binocularModel.text.trim().length > 0
            && root.isPositiveInteger(binocularMagnification.text)
            && root.isPositiveInteger(binocularObjective.text)
        onOpened: controller.clearEquipmentMessage()
        onAccepted: {
            var saved
            if (root.editModel.id !== undefined) {
                saved = controller.updateBinocularModel(root.editModel.id, binocularBrand.text, binocularModel.text, binocularMagnification.text, binocularObjective.text, binocularStabilized.checked)
            } else {
                saved = controller.addBinocularModel(binocularBrand.text, binocularModel.text, binocularMagnification.text, binocularObjective.text, binocularStabilized.checked)
            }
            if (saved)
                binocularDialog.close()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            DarkTextField { id: binocularBrand; Layout.fillWidth: true; labelText: qsTr("Marca *") }
            DarkTextField { id: binocularModel; Layout.fillWidth: true; labelText: qsTr("Modello *") }
            DarkTextField { id: binocularMagnification; Layout.fillWidth: true; labelText: qsTr("Ingrandimento (x) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: binocularObjective; Layout.fillWidth: true; labelText: qsTr("Diametro obiettivo (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            CheckBox { id: binocularStabilized; Layout.fillWidth: true; text: qsTr("Stabilizzato") }
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
        id: deleteBinocularDialog
        title: qsTr("Elimina modello")
        acceptText: controller.equipmentUsage("binocular", root.deleteModel.catalog_id || "") > 0 ? qsTr("Rimuovi dai profili e continua") : qsTr("Elimina")
        acceptDanger: true
        onAccepted: controller.deleteBinocularModel(root.deleteModel.id, controller.equipmentUsage("binocular", root.deleteModel.catalog_id || "") > 0)

        Text {
            Layout.fillWidth: true
            text: controller.equipmentUsage("binocular", root.deleteModel.catalog_id || "") > 0
                ? qsTr("Questo elemento è utilizzato da uno o più profili.")
                : qsTr("Eliminare il modello dal catalogo?")
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }
}

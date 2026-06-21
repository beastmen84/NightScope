import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var editEyepiece: ({})
    property var editBarlow: ({})
    property var deleteEyepiece: ({})
    property var deleteBarlow: ({})

    function openEyepieceDialog(item) {
        editEyepiece = item || ({})
        eyepieceBrand.text = item ? item.brand : ""
        eyepieceModel.text = item ? item.model : ""
        eyepieceType.currentIndex = item && item.type === "Zoom" ? 1 : 0
        eyepieceFocal.text = item ? String(item.focal_length_mm || "") : ""
        eyepieceMinFocal.text = item ? String(item.min_focal_length_mm || "") : ""
        eyepieceMaxFocal.text = item ? String(item.max_focal_length_mm || "") : ""
        eyepieceAfov.text = item ? String(item.apparent_field_deg || "") : ""
        eyepieceAfovRange.text = item && item.afov_min && item.afov_max ? item.afov_min + "-" + item.afov_max : ""
        eyepieceBarrel.text = item ? (item.barrel_size || "") : ""
        eyepieceNotes.text = item ? (item.notes || "") : ""
        eyepieceDialog.title = item ? "Modifica oculare" : "Aggiungi oculare"
        eyepieceDialog.open()
    }

    function openBarlowDialog(item) {
        editBarlow = item || ({})
        barlowBrand.text = item ? item.brand : ""
        barlowModel.text = item ? item.model : ""
        barlowMultiplier.text = item ? String(item.multiplier || "") : ""
        barlowBarrel.text = item ? (item.barrel_size || "") : ""
        barlowNotes.text = item ? (item.notes || "") : ""
        barlowDialog.title = item ? "Modifica Barlow" : "Aggiungi Barlow"
        barlowDialog.open()
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
                    text: "Catalogo oculari e Barlow"
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

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    title: "Catalogo oculari"
                    subtitle: controller.eyepieceCatalog.length + " oculari"
                    accentColor: theme.teal

                    Repeater {
                        model: controller.eyepieceCatalog

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 74
                            radius: 8
                            color: "#20242b"
                            border.color: "#303641"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.brand + " " + modelData.model
                                        color: theme.textPrimary
                                        font.pixelSize: 14
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: (modelData.barrel_size || "barilotto n/d") + "  -  " + (modelData.notes || "")
                                        color: theme.textSecondary
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                    }
                                }

                                StatusPill { text: modelData.type; accentColor: modelData.type === "Zoom" ? theme.violet : theme.teal }
                                StatusPill { text: modelData.focalRangeLabel; accentColor: theme.cyan }
                                StatusPill { text: modelData.apparent_field_deg + " gradi"; accentColor: theme.amber }

                                Button { text: "Modifica"; onClicked: root.openEyepieceDialog(modelData) }
                                Button {
                                    text: "Elimina"
                                    onClicked: {
                                        root.deleteEyepiece = modelData
                                        deleteEyepieceDialog.open()
                                    }
                                }
                            }
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Aggiungi oculare"
                        onClicked: root.openEyepieceDialog(null)
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Catalogo Barlow"
                    subtitle: controller.barlowCatalog.length + " Barlow"
                    accentColor: theme.amber

                    Repeater {
                        model: controller.barlowCatalog

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 70
                            radius: 8
                            color: "#20242b"
                            border.color: "#303641"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.margins: 10
                                spacing: 10

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.brand + " " + modelData.model
                                        color: theme.textPrimary
                                        font.pixelSize: 14
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: (modelData.barrel_size || "barilotto n/d") + "  -  " + (modelData.notes || "")
                                        color: theme.textSecondary
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                    }
                                }

                                StatusPill { text: modelData.multiplier + "x"; accentColor: theme.amber }

                                Button { text: "Modifica"; onClicked: root.openBarlowDialog(modelData) }
                                Button {
                                    text: "Elimina"
                                    onClicked: {
                                        root.deleteBarlow = modelData
                                        deleteBarlowDialog.open()
                                    }
                                }
                            }
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Aggiungi Barlow"
                        onClicked: root.openBarlowDialog(null)
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    DarkDialog {
        id: eyepieceDialog
        title: "Aggiungi oculare"
        acceptText: "Salva"
        onAccepted: {
            if (root.editEyepiece.id !== undefined) {
                controller.updateEyepieceModel(root.editEyepiece.id, eyepieceBrand.text, eyepieceModel.text, eyepieceType.currentText, eyepieceFocal.text, eyepieceMinFocal.text, eyepieceMaxFocal.text, eyepieceAfov.text, eyepieceBarrel.text, eyepieceAfovRange.text, eyepieceNotes.text)
            } else {
                controller.addEyepieceModel(eyepieceBrand.text, eyepieceModel.text, eyepieceType.currentText, eyepieceFocal.text, eyepieceMinFocal.text, eyepieceMaxFocal.text, eyepieceAfov.text, eyepieceBarrel.text, eyepieceAfovRange.text, eyepieceNotes.text)
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: eyepieceBrand; Layout.fillWidth: true; placeholderText: "Brand" }
            TextField { id: eyepieceModel; Layout.fillWidth: true; placeholderText: "Modello" }
            ComboBox { id: eyepieceType; Layout.fillWidth: true; model: ["Fixed", "Zoom"] }
            TextField { id: eyepieceFocal; Layout.fillWidth: true; placeholderText: eyepieceType.currentText === "Zoom" ? "Focale max mm" : "Focale mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: eyepieceMinFocal; Layout.fillWidth: true; visible: eyepieceType.currentText === "Zoom"; placeholderText: "Focale min mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: eyepieceMaxFocal; Layout.fillWidth: true; visible: eyepieceType.currentText === "Zoom"; placeholderText: "Focale max mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: eyepieceAfov; Layout.fillWidth: true; placeholderText: "AFOV medio"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: eyepieceAfovRange; Layout.fillWidth: true; placeholderText: "AFOV min-max opzionale" }
            TextField { id: eyepieceBarrel; Layout.fillWidth: true; placeholderText: "Barilotto" }
            TextField { id: eyepieceNotes; Layout.fillWidth: true; placeholderText: "Note" }
        }
    }

    DarkDialog {
        id: barlowDialog
        title: "Aggiungi Barlow"
        acceptText: "Salva"
        onAccepted: {
            if (root.editBarlow.id !== undefined) {
                controller.updateBarlowModel(root.editBarlow.id, barlowBrand.text, barlowModel.text, barlowMultiplier.text, barlowBarrel.text, barlowNotes.text)
            } else {
                controller.addBarlowModel(barlowBrand.text, barlowModel.text, barlowMultiplier.text, barlowBarrel.text, barlowNotes.text)
            }
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: barlowBrand; Layout.fillWidth: true; placeholderText: "Brand" }
            TextField { id: barlowModel; Layout.fillWidth: true; placeholderText: "Modello" }
            TextField { id: barlowMultiplier; Layout.fillWidth: true; placeholderText: "Moltiplicatore"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: barlowBarrel; Layout.fillWidth: true; placeholderText: "Barilotto" }
            TextField { id: barlowNotes; Layout.columnSpan: 2; Layout.fillWidth: true; placeholderText: "Note" }
        }
    }

    DarkDialog {
        id: deleteEyepieceDialog
        title: "Elimina oculare"
        showAccept: false

        Text {
            Layout.fillWidth: true
            text: controller.equipmentUsage("eyepiece", root.deleteEyepiece.catalog_id || "") > 0
                ? "Questo elemento e utilizzato da uno o piu profili."
                : "Eliminare l'oculare dal catalogo?"
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Button { Layout.fillWidth: true; text: "Annulla"; onClicked: deleteEyepieceDialog.close() }
            Button {
                Layout.fillWidth: true
                text: controller.equipmentUsage("eyepiece", root.deleteEyepiece.catalog_id || "") > 0 ? "Rimuovi dai profili e continua" : "Elimina"
                onClicked: {
                    controller.deleteEyepieceModel(root.deleteEyepiece.id, controller.equipmentUsage("eyepiece", root.deleteEyepiece.catalog_id || "") > 0)
                    deleteEyepieceDialog.close()
                }
            }
        }
    }

    DarkDialog {
        id: deleteBarlowDialog
        title: "Elimina Barlow"
        showAccept: false

        Text {
            Layout.fillWidth: true
            text: controller.equipmentUsage("barlow", root.deleteBarlow.catalog_id || "") > 0
                ? "Questo elemento e utilizzato da uno o piu profili."
                : "Eliminare la Barlow dal catalogo?"
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Button { Layout.fillWidth: true; text: "Annulla"; onClicked: deleteBarlowDialog.close() }
            Button {
                Layout.fillWidth: true
                text: controller.equipmentUsage("barlow", root.deleteBarlow.catalog_id || "") > 0 ? "Rimuovi dai profili e continua" : "Elimina"
                onClicked: {
                    controller.deleteBarlowModel(root.deleteBarlow.id, controller.equipmentUsage("barlow", root.deleteBarlow.catalog_id || "") > 0)
                    deleteBarlowDialog.close()
                }
            }
        }
    }
}

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var selectedCatalogEyepiece: controller.eyepieceCatalog.length > 0 && eyepieceCatalogCombo.currentIndex >= 0 ? controller.eyepieceCatalog[eyepieceCatalogCombo.currentIndex] : ({})
    property var selectedCatalogBarlow: controller.barlowCatalog.length > 0 && barlowCatalogCombo.currentIndex >= 0 ? controller.barlowCatalog[barlowCatalogCombo.currentIndex] : ({})
    property var editEyepieceData: ({})
    property var editBarlowData: ({})

    function openEyepieceEdit(eyepiece) {
        editEyepieceData = eyepiece
        editEyepieceName.text = eyepiece.name
        editEyepieceType.currentIndex = eyepiece.type === "Zoom" ? 1 : 0
        editEyepieceFocal.text = String(eyepiece.focalLengthMm)
        editEyepieceMinFocal.text = String(eyepiece.minFocalLengthMm)
        editEyepieceMaxFocal.text = String(eyepiece.maxFocalLengthMm)
        editEyepieceField.text = String(eyepiece.apparentFieldDeg)
        editEyepieceBarrel.text = eyepiece.barrelSize || ""
        editEyepieceDialog.open()
    }

    function openBarlowEdit(barlow) {
        editBarlowData = barlow
        editBarlowName.text = barlow.name
        editBarlowMultiplier.text = String(barlow.multiplier)
        editBarlowBarrel.text = barlow.barrelSize || ""
        editBarlowDialog.open()
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
                    text: "Oculari e Barlow"
                    color: theme.textPrimary
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: controller.canUseEyepieces ? "Gestisci gli accessori realmente posseduti." : "Crea o seleziona un telescopio prima di aggiungere oculari o Barlow."
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
                    title: "Eyepieces"
                    subtitle: controller.ownedEyepieces.length + " oculari posseduti"
                    accentColor: theme.teal

                    Text {
                        Layout.fillWidth: true
                        visible: controller.ownedEyepieces.length === 0
                        text: controller.canUseEyepieces ? "Nessun oculare configurato." : controller.equipmentMessage
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.ownedEyepieces

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 72
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
                                        text: modelData.name
                                        color: theme.textPrimary
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.type + "  -  " + (modelData.barrelSize || "barilotto n/d")
                                        color: theme.textSecondary
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                    }
                                }

                                StatusPill { text: modelData.focalRangeLabel; accentColor: theme.teal }
                                StatusPill { text: modelData.apparentFieldDeg + " gradi"; accentColor: theme.cyan }

                                Button {
                                    text: "Edit"
                                    onClicked: root.openEyepieceEdit(modelData)
                                }

                                Button {
                                    text: "Delete"
                                    onClicked: controller.removeEyepiece(modelData.id)
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Button {
                            Layout.fillWidth: true
                            enabled: controller.canUseEyepieces
                            text: "Add from Catalog"
                            onClicked: addCatalogEyepieceDialog.open()
                        }

                        Button {
                            Layout.fillWidth: true
                            enabled: controller.canUseEyepieces
                            text: "Add Custom"
                            onClicked: addCustomEyepieceDialog.open()
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Barlows"
                    subtitle: controller.ownedBarlows.length + " Barlow possedute"
                    accentColor: theme.amber

                    Text {
                        Layout.fillWidth: true
                        visible: controller.ownedBarlows.length === 0
                        text: controller.canUseEyepieces ? "Nessuna Barlow configurata." : controller.equipmentMessage
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.ownedBarlows

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 72
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
                                        text: modelData.name
                                        color: theme.textPrimary
                                        font.pixelSize: 15
                                        font.weight: Font.DemiBold
                                        elide: Text.ElideRight
                                    }

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.barrelSize || "barilotto n/d"
                                        color: theme.textSecondary
                                        font.pixelSize: 12
                                        elide: Text.ElideRight
                                    }
                                }

                                StatusPill { text: modelData.multiplier + "x"; accentColor: theme.amber }

                                Button {
                                    text: "Edit"
                                    onClicked: root.openBarlowEdit(modelData)
                                }

                                Button {
                                    text: "Delete"
                                    onClicked: controller.removeBarlow(modelData.id)
                                }
                            }
                        }
                    }

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 10

                        Button {
                            Layout.fillWidth: true
                            enabled: controller.canUseEyepieces
                            text: "Add from Catalog"
                            onClicked: addCatalogBarlowDialog.open()
                        }

                        Button {
                            Layout.fillWidth: true
                            enabled: controller.canUseEyepieces
                            text: "Add Custom"
                            onClicked: addCustomBarlowDialog.open()
                        }
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Uso nelle raccomandazioni"
                subtitle: "Solo gli accessori assegnati al profilo attivo vengono proposti"
                accentColor: theme.green

                Text {
                    Layout.fillWidth: true
                    text: "Dopo aver aggiunto oculari o Barlow, assegna quelli da usare nella pagina Profili. NightScope non propone accessori non posseduti o non assegnati."
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    Dialog {
        id: addCatalogEyepieceDialog
        title: "Add Eyepiece from Catalog"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (root.selectedCatalogEyepiece.id !== undefined) {
                controller.addCatalogEyepiece(root.selectedCatalogEyepiece.id)
            }
        }

        ColumnLayout {
            width: 520
            spacing: 10

            ComboBox {
                id: eyepieceCatalogCombo
                Layout.fillWidth: true
                model: controller.eyepieceCatalog
                textRole: "model"
            }

            Text {
                Layout.fillWidth: true
                text: (root.selectedCatalogEyepiece.brand || "") + "  -  " + (root.selectedCatalogEyepiece.focalRangeLabel || root.selectedCatalogEyepiece.focal_length_mm + " mm") + "  -  " + (root.selectedCatalogEyepiece.apparent_field_deg || "") + " gradi"
                color: theme.textSecondary
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
        }
    }

    Dialog {
        id: addCustomEyepieceDialog
        title: "Add Custom Eyepiece"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (customEyepieceType.currentText === "Zoom") {
                controller.addZoomEyepiece(customEyepieceName.text, customEyepieceMinFocal.text, customEyepieceMaxFocal.text, customEyepieceField.text, customEyepieceBarrel.text)
            } else {
                controller.addCustomEyepiece(customEyepieceName.text, customEyepieceFocal.text, customEyepieceField.text, customEyepieceBarrel.text)
            }
        }

        GridLayout {
            width: 520
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: customEyepieceName; Layout.fillWidth: true; placeholderText: "Nome" }
            ComboBox { id: customEyepieceType; Layout.fillWidth: true; model: ["Fixed", "Zoom"] }
            TextField { id: customEyepieceFocal; Layout.fillWidth: true; visible: customEyepieceType.currentText === "Fixed"; placeholderText: "Focale mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: customEyepieceMinFocal; Layout.fillWidth: true; visible: customEyepieceType.currentText === "Zoom"; placeholderText: "Focale min mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: customEyepieceMaxFocal; Layout.fillWidth: true; visible: customEyepieceType.currentText === "Zoom"; placeholderText: "Focale max mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: customEyepieceField; Layout.fillWidth: true; placeholderText: "Campo apparente"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: customEyepieceBarrel; Layout.fillWidth: true; placeholderText: "Barilotto" }
        }
    }

    Dialog {
        id: editEyepieceDialog
        title: "Edit Eyepiece"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (editEyepieceType.currentText === "Zoom") {
                controller.updateZoomEyepiece(root.editEyepieceData.id, editEyepieceName.text, editEyepieceMinFocal.text, editEyepieceMaxFocal.text, editEyepieceField.text, editEyepieceBarrel.text)
            } else {
                controller.updateEyepiece(root.editEyepieceData.id, editEyepieceName.text, editEyepieceFocal.text, editEyepieceField.text, editEyepieceBarrel.text, "Fixed")
            }
        }

        GridLayout {
            width: 520
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: editEyepieceName; Layout.fillWidth: true; placeholderText: "Nome" }
            ComboBox { id: editEyepieceType; Layout.fillWidth: true; model: ["Fixed", "Zoom"] }
            TextField { id: editEyepieceFocal; Layout.fillWidth: true; visible: editEyepieceType.currentText === "Fixed"; placeholderText: "Focale mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: editEyepieceMinFocal; Layout.fillWidth: true; visible: editEyepieceType.currentText === "Zoom"; placeholderText: "Focale min mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: editEyepieceMaxFocal; Layout.fillWidth: true; visible: editEyepieceType.currentText === "Zoom"; placeholderText: "Focale max mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: editEyepieceField; Layout.fillWidth: true; placeholderText: "Campo apparente"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: editEyepieceBarrel; Layout.fillWidth: true; placeholderText: "Barilotto" }
        }
    }

    Dialog {
        id: addCatalogBarlowDialog
        title: "Add Barlow from Catalog"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (root.selectedCatalogBarlow.id !== undefined) {
                controller.addCatalogBarlow(root.selectedCatalogBarlow.id)
            }
        }

        ColumnLayout {
            width: 520
            spacing: 10

            ComboBox {
                id: barlowCatalogCombo
                Layout.fillWidth: true
                model: controller.barlowCatalog
                textRole: "model"
            }

            Text {
                Layout.fillWidth: true
                text: (root.selectedCatalogBarlow.brand || "") + "  -  " + (root.selectedCatalogBarlow.multiplier || "") + "x"
                color: theme.textSecondary
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
        }
    }

    Dialog {
        id: addCustomBarlowDialog
        title: "Add Custom Barlow"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: controller.addBarlow(customBarlowName.text, customBarlowMultiplier.text, customBarlowBarrel.text)

        GridLayout {
            width: 520
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: customBarlowName; Layout.fillWidth: true; placeholderText: "Nome" }
            TextField { id: customBarlowMultiplier; Layout.fillWidth: true; placeholderText: "Moltiplicatore"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: customBarlowBarrel; Layout.fillWidth: true; placeholderText: "Barilotto" }
        }
    }

    Dialog {
        id: editBarlowDialog
        title: "Edit Barlow"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: controller.updateBarlow(root.editBarlowData.id, editBarlowName.text, editBarlowMultiplier.text, editBarlowBarrel.text)

        GridLayout {
            width: 520
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            TextField { id: editBarlowName; Layout.fillWidth: true; placeholderText: "Nome" }
            TextField { id: editBarlowMultiplier; Layout.fillWidth: true; placeholderText: "Moltiplicatore"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
            TextField { id: editBarlowBarrel; Layout.fillWidth: true; placeholderText: "Barilotto" }
        }
    }
}

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
    property string opticsSearch: ""

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

    function eyepieceFormValid() {
        if (eyepieceBrand.text.trim().length === 0
                || eyepieceModel.text.trim().length === 0
                || !root.isPositiveNumber(eyepieceAfov.text)
                || root.numberValue(eyepieceAfov.text) > 180)
            return false
        if (eyepieceType.currentIndex === 0)
            return root.isPositiveNumber(eyepieceFocal.text)
        return root.isPositiveNumber(eyepieceMinFocal.text)
            && root.isPositiveNumber(eyepieceMaxFocal.text)
            && root.numberValue(eyepieceMinFocal.text) < root.numberValue(eyepieceMaxFocal.text)
    }

    function openEyepieceDialog(item) {
        editEyepiece = item || ({})
        eyepieceBrand.text = item ? item.brand : ""
        eyepieceModel.text = item ? item.model : ""
        eyepieceType.currentIndex = item && item.type === "Zoom" ? 1 : 0
        eyepieceFocal.text = item ? root.localizedNumber(item.focal_length_mm) : ""
        eyepieceMinFocal.text = item ? root.localizedNumber(item.min_focal_length_mm) : ""
        eyepieceMaxFocal.text = item ? root.localizedNumber(item.max_focal_length_mm) : ""
        eyepieceAfov.text = item ? root.localizedNumber(item.apparent_field_deg) : ""
        eyepieceAfovRange.text = item && item.afov_min && item.afov_max
            ? root.localizedNumber(item.afov_min) + "-" + root.localizedNumber(item.afov_max) : ""
        eyepieceNotes.text = item ? (item.notes || "") : ""
        eyepieceDialog.title = item ? qsTr("Modifica oculare") : qsTr("Aggiungi oculare")
        eyepieceDialog.open()
    }

    function openBarlowDialog(item) {
        editBarlow = item || ({})
        barlowBrand.text = item ? item.brand : ""
        barlowModel.text = item ? item.model : ""
        barlowMultiplier.text = item ? root.localizedNumber(item.multiplier) : ""
        barlowNotes.text = item ? (item.notes || "") : ""
        barlowDialog.title = item ? qsTr("Modifica Barlow") : qsTr("Aggiungi Barlow")
        barlowDialog.open()
    }

    function searchText() {
        return root.opticsSearch.toLowerCase().trim()
    }

    function matchesEyepiece(item) {
        var query = root.searchText()
        if (query.length === 0)
            return true
        var text = (
            item.brand + " " + item.model + " " + item.type + " " +
            item.focalRangeLabel + " " + item.focal_length_mm + " " +
            (item.min_focal_length_mm || "") + " " + (item.max_focal_length_mm || "")
        ).toLowerCase()
        return text.indexOf(query) >= 0
    }

    function matchesBarlow(item) {
        var query = root.searchText()
        if (query.length === 0)
            return true
        var text = (
            item.brand + " " + item.model + " Barlow " + item.multiplier + "x " +
            item.multiplier
        ).toLowerCase()
        return text.indexOf(query) >= 0
    }

    function filteredEyepieces() {
        return controller.eyepieceCatalog.filter(function(item) {
            return root.matchesEyepiece(item)
        })
    }

    function filteredBarlows() {
        return controller.barlowCatalog.filter(function(item) {
            return root.matchesBarlow(item)
        })
    }

    function eyepieceAccent(item) {
        return item.type === "Zoom" ? theme.violet : theme.teal
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
                    text: qsTr("Catalogo oculari e Barlow")
                    color: theme.textPrimary
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Accessori ottici disponibili per i profili osservativi")
                    color: theme.textSecondary
                    font.pixelSize: 14
                    wrapMode: Text.WordWrap
                }
            }

            DarkTextField {
                Layout.preferredWidth: 330
                placeholderText: qsTr("Cerca oculare o Barlow...")
                onTextChanged: root.opticsSearch = text
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

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
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
                                text: qsTr("Catalogo oculari")
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("%1 di %2 oculari")
                                    .arg(root.filteredEyepieces().length)
                                    .arg(controller.eyepieceCatalog.length)
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }

                        DarkButton {
                            text: qsTr("Aggiungi oculare")
                            accentColor: theme.teal
                            onClicked: root.openEyepieceDialog(null)
                        }
                    }

                    ScrollView {
                        id: eyepieceScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: Math.max(0, availableWidth - 14)

                        ColumnLayout {
                            width: Math.max(0, eyepieceScroll.availableWidth - 14)
                            spacing: 10

                            Repeater {
                                model: root.filteredEyepieces()

                                delegate: OpticRow {
                                    itemData: modelData
                                    accent: root.eyepieceAccent(modelData)
                                    onEdit: root.openEyepieceDialog(modelData)
                                    onDeleteRequested: {
                                        root.deleteEyepiece = modelData
                                        deleteEyepieceDialog.open()
                                    }
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: root.filteredEyepieces().length === 0
                                text: qsTr("Nessun oculare trovato.")
                                color: theme.textSecondary
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }

            Rectangle {
                Layout.fillWidth: true
                Layout.fillHeight: true
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
                                text: qsTr("Catalogo Barlow")
                                color: theme.textPrimary
                                font.pixelSize: 18
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: qsTr("%1 di %2 Barlow")
                                    .arg(root.filteredBarlows().length)
                                    .arg(controller.barlowCatalog.length)
                                color: theme.textSecondary
                                font.pixelSize: 12
                                elide: Text.ElideRight
                            }
                        }

                        DarkButton {
                            text: qsTr("Aggiungi Barlow")
                            accentColor: theme.amber
                            onClicked: root.openBarlowDialog(null)
                        }
                    }

                    ScrollView {
                        id: barlowScroll
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        contentWidth: Math.max(0, availableWidth - 14)

                        ColumnLayout {
                            width: Math.max(0, barlowScroll.availableWidth - 14)
                            spacing: 10

                            Repeater {
                                model: root.filteredBarlows()

                                delegate: OpticRow {
                                    itemData: modelData
                                    isBarlow: true
                                    accent: theme.amber
                                    onEdit: root.openBarlowDialog(modelData)
                                    onDeleteRequested: {
                                        root.deleteBarlow = modelData
                                        deleteBarlowDialog.open()
                                    }
                                }
                            }

                            Text {
                                Layout.fillWidth: true
                                visible: root.filteredBarlows().length === 0
                                text: qsTr("Nessuna Barlow trovata.")
                                color: theme.textSecondary
                                font.pixelSize: 13
                                wrapMode: Text.WordWrap
                            }
                        }
                    }
                }
            }
        }
    }

    component OpticRow: Rectangle {
        id: opticRow
        property var itemData
        property bool isBarlow: false
                                property color accent: theme.cyan
        signal edit()
        signal deleteRequested()

        Layout.fillWidth: true
        implicitHeight: rowContent.implicitHeight + 22
        radius: 8
                                color: theme.surfaceRaised
                                border.color: theme.border
        border.width: 1

        ColumnLayout {
            id: rowContent
            anchors.fill: parent
            anchors.margins: 11
            spacing: 7

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: itemData.brand + " " + itemData.model
                    color: theme.textPrimary
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                DarkButton {
                    text: qsTr("Modifica")
                    onClicked: opticRow.edit()
                }

                DarkButton {
                    visible: !itemData.is_builtin
                    text: qsTr("Elimina")
                    danger: true
                    onClicked: opticRow.deleteRequested()
                }
            }

            Text {
                Layout.fillWidth: true
                visible: String(itemData.notes || "").trim().length > 0
                text: itemData.notes || ""
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            Flow {
                Layout.fillWidth: true
                spacing: 8

                StatusPill {
                    visible: !opticRow.isBarlow
                    text: opticRow.isBarlow ? "" : (itemData.type_label || itemData.type || "")
                    accentColor: opticRow.accent
                }

                StatusPill {
                    visible: !opticRow.isBarlow
                    text: opticRow.isBarlow ? "" : (itemData.focalRangeLabel || "")
                    accentColor: theme.cyan
                }

                StatusPill {
                    visible: !opticRow.isBarlow
                    text: opticRow.isBarlow ? "" : (itemData.apparent_field_label || "")
                    accentColor: theme.amber
                }

                StatusPill {
                    visible: opticRow.isBarlow
                    text: opticRow.isBarlow ? itemData.multiplier_label : ""
                    accentColor: theme.amber
                }
            }
        }
    }

    DarkDialog {
        id: eyepieceDialog
        title: qsTr("Aggiungi oculare")
        acceptText: qsTr("Salva")
        closeOnAccept: false
        acceptEnabled: root.eyepieceFormValid()
        onOpened: controller.clearEquipmentMessage()
        onAccepted: {
            var saved
            if (root.editEyepiece.id !== undefined) {
                saved = controller.updateEyepieceModel(root.editEyepiece.id, eyepieceBrand.text, eyepieceModel.text, eyepieceType.currentIndex === 1 ? "Zoom" : "Fixed", eyepieceFocal.text, eyepieceMinFocal.text, eyepieceMaxFocal.text, eyepieceAfov.text, eyepieceAfovRange.text, eyepieceNotes.text)
            } else {
                saved = controller.addEyepieceModel(eyepieceBrand.text, eyepieceModel.text, eyepieceType.currentIndex === 1 ? "Zoom" : "Fixed", eyepieceFocal.text, eyepieceMinFocal.text, eyepieceMaxFocal.text, eyepieceAfov.text, eyepieceAfovRange.text, eyepieceNotes.text)
            }
            if (saved)
                eyepieceDialog.close()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            DarkTextField { id: eyepieceBrand; Layout.fillWidth: true; labelText: qsTr("Marca *") }
            DarkTextField { id: eyepieceModel; Layout.fillWidth: true; labelText: qsTr("Modello *") }
            DarkComboBox { id: eyepieceType; Layout.fillWidth: true; labelText: qsTr("Tipo *"); model: [qsTr("Fisso"), "Zoom"] }
            DarkTextField { id: eyepieceFocal; Layout.fillWidth: true; visible: eyepieceType.currentIndex === 0; labelText: qsTr("Focale (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: eyepieceMinFocal; Layout.fillWidth: true; visible: eyepieceType.currentIndex === 1; labelText: qsTr("Focale minima (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: eyepieceMaxFocal; Layout.fillWidth: true; visible: eyepieceType.currentIndex === 1; labelText: qsTr("Focale massima (mm) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField {
                id: eyepieceAfov
                Layout.fillWidth: true
                labelText: eyepieceType.currentIndex === 0 ? qsTr("AFOV (°) *") : qsTr("AFOV medio (°) *")
                inputMethodHints: Qt.ImhFormattedNumbersOnly
            }
            DarkTextField {
                id: eyepieceAfovRange
                Layout.fillWidth: true
                visible: eyepieceType.currentIndex === 1
                labelText: qsTr("Intervallo AFOV (°; facoltativo)")
                placeholderText: qsTr("48-68")
            }
            DarkTextField { id: eyepieceNotes; Layout.columnSpan: 2; Layout.fillWidth: true; labelText: qsTr("Note (facoltative)") }
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
        id: barlowDialog
        title: qsTr("Aggiungi Barlow")
        acceptText: qsTr("Salva")
        closeOnAccept: false
        acceptEnabled: barlowBrand.text.trim().length > 0
            && barlowModel.text.trim().length > 0
            && root.isPositiveNumber(barlowMultiplier.text)
            && root.numberValue(barlowMultiplier.text) > 1
        onOpened: controller.clearEquipmentMessage()
        onAccepted: {
            var saved
            if (root.editBarlow.id !== undefined) {
                saved = controller.updateBarlowModel(root.editBarlow.id, barlowBrand.text, barlowModel.text, barlowMultiplier.text, barlowNotes.text)
            } else {
                saved = controller.addBarlowModel(barlowBrand.text, barlowModel.text, barlowMultiplier.text, barlowNotes.text)
            }
            if (saved)
                barlowDialog.close()
        }

        GridLayout {
            Layout.fillWidth: true
            columns: 2
            columnSpacing: 8
            rowSpacing: 8

            DarkTextField { id: barlowBrand; Layout.fillWidth: true; labelText: qsTr("Marca *") }
            DarkTextField { id: barlowModel; Layout.fillWidth: true; labelText: qsTr("Modello *") }
            DarkTextField { id: barlowMultiplier; Layout.fillWidth: true; labelText: qsTr("Moltiplicatore (x) *"); inputMethodHints: Qt.ImhFormattedNumbersOnly }
            DarkTextField { id: barlowNotes; Layout.fillWidth: true; labelText: qsTr("Note (facoltative)") }
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
        id: deleteEyepieceDialog
        title: qsTr("Elimina oculare")
        acceptText: controller.equipmentUsage("eyepiece", root.deleteEyepiece.catalog_id || "") > 0 ? qsTr("Rimuovi dai profili e continua") : qsTr("Elimina")
        acceptDanger: true
        onAccepted: controller.deleteEyepieceModel(root.deleteEyepiece.id, controller.equipmentUsage("eyepiece", root.deleteEyepiece.catalog_id || "") > 0)

        Text {
            Layout.fillWidth: true
            text: controller.equipmentUsage("eyepiece", root.deleteEyepiece.catalog_id || "") > 0
                ? qsTr("Questo elemento è utilizzato da uno o più profili.")
                : qsTr("Eliminare l'oculare dal catalogo?")
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: deleteBarlowDialog
        title: qsTr("Elimina Barlow")
        acceptText: controller.equipmentUsage("barlow", root.deleteBarlow.catalog_id || "") > 0 ? qsTr("Rimuovi dai profili e continua") : qsTr("Elimina")
        acceptDanger: true
        onAccepted: controller.deleteBarlowModel(root.deleteBarlow.id, controller.equipmentUsage("barlow", root.deleteBarlow.catalog_id || "") > 0)

        Text {
            Layout.fillWidth: true
            text: controller.equipmentUsage("barlow", root.deleteBarlow.catalog_id || "") > 0
                ? qsTr("Questo elemento è utilizzato da uno o più profili.")
                : qsTr("Eliminare la Barlow dal catalogo?")
            color: theme.textPrimary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }
}

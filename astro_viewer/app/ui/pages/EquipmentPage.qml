import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property var selectedCatalogModel: controller.telescopeCatalogModels.length > 0 && catalogModelCombo.currentIndex >= 0 ? controller.telescopeCatalogModels[catalogModelCombo.currentIndex] : ({})
    property var selectedCatalogEyepiece: controller.eyepieceCatalog.length > 0 && eyepieceCatalogCombo.currentIndex >= 0 ? controller.eyepieceCatalog[eyepieceCatalogCombo.currentIndex] : ({})
    property var selectedCatalogBarlow: controller.barlowCatalog.length > 0 && barlowCatalogCombo.currentIndex >= 0 ? controller.barlowCatalog[barlowCatalogCombo.currentIndex] : ({})

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

            RowLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28

                ColumnLayout {
                    Layout.fillWidth: true
                    spacing: 6

                    Text {
                        Layout.fillWidth: true
                        text: "La mia attrezzatura"
                        color: theme.textPrimary
                        font.pixelSize: 34
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: controller.equipmentMessage
                        color: theme.textSecondary
                        font.pixelSize: 14
                        wrapMode: Text.WordWrap
                    }
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
                    title: "Profilo attivo"
                    subtitle: "Setup usato da planner e raccomandazioni"
                    accentColor: theme.green

                    RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        StatusPill { text: "Attivo"; accentColor: theme.green }

                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2

                            Text {
                                Layout.fillWidth: true
                                text: controller.currentSetup.name
                                color: theme.textPrimary
                                font.pixelSize: 20
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.fillWidth: true
                                text: controller.currentSetup.type + "  -  " + controller.currentSetup.mount
                                color: theme.textSecondary
                                font.pixelSize: 13
                                elide: Text.ElideRight
                            }
                        }
                    }

                    Repeater {
                        model: controller.equipmentProfiles

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatusPill {
                                text: modelData.active === 1 ? "Attivo" : "Profilo"
                                accentColor: modelData.active === 1 ? theme.green : theme.textMuted
                            }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.profile_name
                                color: theme.textSecondary
                                font.pixelSize: 13
                                elide: Text.ElideRight
                            }

                            Button {
                                text: "Usa"
                                enabled: modelData.active !== 1
                                onClicked: controller.setActiveEquipmentProfile(modelData.id)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Capacita calcolate"
                    subtitle: controller.telescopeCapabilities.name
                    accentColor: theme.cyan

                    GridLayout {
                        Layout.fillWidth: true
                        columns: 2
                        columnSpacing: 10
                        rowSpacing: 10

                        MetricTile { label: "Apertura"; value: controller.telescopeCapabilities.aperture; accentColor: theme.cyan }
                        MetricTile { label: "Focale"; value: controller.telescopeCapabilities.focalLength; accentColor: theme.teal }
                        MetricTile { label: "Ingrandimento pratico"; value: controller.telescopeCapabilities.practicalMagnification; accentColor: theme.amber }
                        MetricTile { label: "Raccolta luce"; value: controller.telescopeCapabilities.lightGathering; accentColor: theme.violet }
                        MetricTile { label: "Magnitudine limite"; value: controller.telescopeCapabilities.limitingMagnitude; accentColor: theme.green }
                        MetricTile { label: "Risoluzione"; value: controller.telescopeCapabilities.resolution; accentColor: theme.coral }
                    }
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
                    title: "I miei telescopi"
                    subtitle: "Seleziona il tubo ottico usato stasera"
                    accentColor: theme.cyan

                    Repeater {
                        model: controller.equipmentSetups

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            implicitHeight: 58
                            radius: 8
                            color: setupMouse.containsMouse ? "#20242b" : "transparent"
                            border.color: setupMouse.containsMouse ? "#303641" : "transparent"
                            border.width: 1

                            RowLayout {
                                anchors.fill: parent
                                anchors.leftMargin: 10
                                anchors.rightMargin: 10
                                spacing: 12

                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 2

                                    Text {
                                        Layout.fillWidth: true
                                        text: modelData.name
                                        color: theme.textPrimary
                                        font.pixelSize: 14
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

                                StatusPill {
                                    text: modelData.apertureMm + "/" + modelData.focalLengthMm + " mm"
                                    accentColor: theme.cyan
                                }
                            }

                            MouseArea {
                                id: setupMouse
                                anchors.fill: parent
                                hoverEnabled: true
                                cursorShape: Qt.PointingHandCursor
                                onClicked: controller.selectEquipmentSetup(index)
                            }
                        }
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Aggiungi telescopio"
                    subtitle: "Inserimento manuale sempre disponibile"
                    accentColor: theme.amber

                    TextField { id: telescopeName; Layout.fillWidth: true; placeholderText: "Nome" }
                    TextField { id: telescopeAperture; Layout.fillWidth: true; placeholderText: "Apertura mm"; inputMethodHints: Qt.ImhDigitsOnly }
                    TextField { id: telescopeFocal; Layout.fillWidth: true; placeholderText: "Focale mm"; inputMethodHints: Qt.ImhDigitsOnly }

                    ComboBox {
                        id: telescopeType
                        Layout.fillWidth: true
                        model: ["rifrattore", "Newton", "Schmidt-Cassegrain", "Maksutov"]
                    }

                    TextField { id: telescopeMount; Layout.fillWidth: true; placeholderText: "Montatura" }

                    Button {
                        Layout.fillWidth: true
                        text: "Aggiungi telescopio"
                        onClicked: controller.addTelescope(telescopeName.text, telescopeAperture.text, telescopeFocal.text, telescopeType.currentText, telescopeMount.text)
                    }
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
                    title: "I miei oculari"
                    subtitle: controller.canUseEyepieces ? "Solo questi vengono usati dalle raccomandazioni" : "Crea o seleziona un telescopio per aggiungere oculari"
                    accentColor: theme.teal

                    Text {
                        Layout.fillWidth: true
                        visible: controller.eyepieces.length === 0
                        text: controller.canUseEyepieces ? "Nessun oculare configurato. I suggerimenti resteranno limitati finche non aggiungi oculari." : controller.equipmentMessage
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.eyepieces

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                color: theme.textPrimary
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            StatusPill { text: modelData.focalLengthMm + " mm"; accentColor: theme.teal }
                            StatusPill { text: modelData.apparentFieldDeg + " gradi"; accentColor: theme.cyan }
                            StatusPill { text: modelData.barrelSize || "barilotto n/d"; accentColor: theme.textMuted }

                            Button {
                                text: "Rimuovi"
                                onClicked: controller.removeEyepiece(modelData.id)
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 900 ? 4 : 2
                        columnSpacing: 8
                        rowSpacing: 8

                        TextField { id: eyepieceName; Layout.fillWidth: true; placeholderText: "Nome" }
                        TextField { id: eyepieceFocal; Layout.fillWidth: true; placeholderText: "Focale mm"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                        TextField { id: eyepieceField; Layout.fillWidth: true; placeholderText: "Campo apparente"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                        TextField { id: eyepieceBarrel; Layout.fillWidth: true; placeholderText: "Barilotto" }
                    }

                    Button {
                        Layout.fillWidth: true
                        enabled: controller.canUseEyepieces
                        text: "Aggiungi oculare custom"
                        onClicked: controller.addCustomEyepiece(eyepieceName.text, eyepieceFocal.text, eyepieceField.text, eyepieceBarrel.text)
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Le mie Barlow"
                    subtitle: "Usate solo se migliorano davvero la combinazione"
                    accentColor: theme.amber

                    Text {
                        Layout.fillWidth: true
                        visible: controller.ownedBarlows.length === 0
                        text: controller.canUseEyepieces ? "Nessuna Barlow configurata. Le raccomandazioni useranno solo oculari diretti." : controller.equipmentMessage
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.ownedBarlows

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                color: theme.textPrimary
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            StatusPill { text: modelData.multiplier + "x"; accentColor: theme.amber }
                            StatusPill { text: modelData.barrelSize || "barilotto n/d"; accentColor: theme.textMuted }

                            Button {
                                text: "Rimuovi"
                                onClicked: controller.removeBarlow(modelData.id)
                            }
                        }
                    }

                    GridLayout {
                        Layout.fillWidth: true
                        columns: root.width > 900 ? 3 : 1
                        columnSpacing: 8
                        rowSpacing: 8

                        TextField { id: barlowName; Layout.fillWidth: true; placeholderText: "Nome" }
                        TextField { id: barlowMultiplier; Layout.fillWidth: true; placeholderText: "Moltiplicatore"; inputMethodHints: Qt.ImhFormattedNumbersOnly }
                        TextField { id: barlowBarrel; Layout.fillWidth: true; placeholderText: "Barilotto" }
                    }

                    Button {
                        Layout.fillWidth: true
                        enabled: controller.canUseEyepieces
                        text: "Aggiungi Barlow custom"
                        onClicked: controller.addBarlow(barlowName.text, barlowMultiplier.text, barlowBarrel.text)
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Calcoli oculari"
                subtitle: controller.canUseEyepieces ? "Anteprima con moltiplicatore selezionato" : "Non disponibili in modalita Occhio nudo"
                accentColor: theme.violet

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    StatusPill { text: controller.currentSetup.name; accentColor: theme.violet }

                    Button {
                        text: "1x"
                        enabled: controller.canUseEyepieces
                        onClicked: controller.setBarlow(1.0)
                    }

                    Button {
                        text: "2x"
                        enabled: controller.canUseEyepieces
                        onClicked: controller.setBarlow(2.0)
                    }

                    Button {
                        text: "3x"
                        enabled: controller.canUseEyepieces
                        onClicked: controller.setBarlow(3.0)
                    }
                }

                Repeater {
                    model: controller.telescopeCalculations

                    delegate: RowLayout {
                        Layout.fillWidth: true
                        spacing: 12

                        Text {
                            Layout.fillWidth: true
                            text: modelData.eyepiece
                            color: theme.textPrimary
                            font.pixelSize: 14
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                        }

                        StatusPill { text: modelData.magnification; accentColor: theme.cyan }
                        StatusPill { text: modelData.trueField; accentColor: theme.teal }
                        StatusPill { text: modelData.exitPupil; accentColor: theme.amber }
                    }
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                text: "Cataloghi"
                color: theme.textPrimary
                font.pixelSize: 18
                font.weight: Font.DemiBold
            }

            GridLayout {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1180 ? 3 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    Layout.fillWidth: true
                    title: "Catalogo telescopi"
                    subtitle: "Secondario: crea profili reali da marca e modello"
                    accentColor: theme.cyan

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
                        elide: Text.ElideRight
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Crea profilo da catalogo"
                        onClicked: controller.addCatalogProfile(root.selectedCatalogModel.catalog_id, root.selectedCatalogModel.brand + " " + root.selectedCatalogModel.name)
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Catalogo oculari"
                    subtitle: "Aggiungi al tuo set"
                    accentColor: theme.teal

                    ComboBox {
                        id: eyepieceCatalogCombo
                        Layout.fillWidth: true
                        model: controller.eyepieceCatalog
                        textRole: "model"
                    }

                    Text {
                        Layout.fillWidth: true
                        text: (root.selectedCatalogEyepiece.brand || "") + "  -  " + (root.selectedCatalogEyepiece.focal_length_mm || "") + " mm  -  " + (root.selectedCatalogEyepiece.apparent_field_deg || "") + " gradi"
                        color: theme.textSecondary
                        font.pixelSize: 12
                        elide: Text.ElideRight
                    }

                    Button {
                        Layout.fillWidth: true
                        enabled: controller.canUseEyepieces
                        text: "Aggiungi oculare da catalogo"
                        onClicked: controller.addCatalogEyepiece(root.selectedCatalogEyepiece.id)
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Catalogo Barlow"
                    subtitle: "Aggiungi solo se posseduta"
                    accentColor: theme.amber

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
                        elide: Text.ElideRight
                    }

                    Button {
                        Layout.fillWidth: true
                        enabled: controller.canUseEyepieces
                        text: "Aggiungi Barlow da catalogo"
                        onClicked: controller.addCatalogBarlow(root.selectedCatalogBarlow.id)
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Modalita principianti"
                subtitle: "Preset immediatamente utilizzabili"
                accentColor: theme.teal

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1080 ? 5 : 3
                    columnSpacing: 10
                    rowSpacing: 10

                    Repeater {
                        model: controller.beginnerPresets

                        delegate: Rectangle {
                            Layout.fillWidth: true
                            Layout.preferredHeight: 108
                            radius: 8
                            color: "#20242b"
                            border.color: "#303641"
                            border.width: 1

                            ColumnLayout {
                                anchors.fill: parent
                                anchors.margins: 12
                                spacing: 6

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.name
                                    color: theme.textPrimary
                                    font.pixelSize: 14
                                    font.weight: Font.DemiBold
                                    elide: Text.ElideRight
                                }

                                Text {
                                    Layout.fillWidth: true
                                    text: modelData.target
                                    color: theme.textSecondary
                                    font.pixelSize: 12
                                    wrapMode: Text.WordWrap
                                    maximumLineCount: 2
                                    elide: Text.ElideRight
                                }
                            }
                        }
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }
}

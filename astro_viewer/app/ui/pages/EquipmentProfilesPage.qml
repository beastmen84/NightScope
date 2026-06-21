import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property int renameProfileId: -1
    property string addFilter: "Tutti"
    property string removeFilter: "Tutti"
    property string addSearch: ""
    property string removeSearch: ""

    function matchesFilter(item, filter, searchText) {
        var typeOk = filter === "Tutti"
            || (filter === "Telescopi" && item.kind === "telescope")
            || (filter === "Oculari" && item.kind === "eyepiece")
            || (filter === "Barlow" && item.kind === "barlow")
        var text = (item.name + " " + item.badge + " " + item.details).toLowerCase()
        return typeOk && text.indexOf(searchText.toLowerCase()) >= 0
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
                    text: "Profili"
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
                    subtitle: "Setup usato dalle raccomandazioni"
                    accentColor: theme.green

                    Text {
                        Layout.fillWidth: true
                        text: controller.activeEquipmentProfile.profile_name || "Occhio nudo"
                        color: theme.textPrimary
                        font.pixelSize: 26
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    StatusPill { text: "Attivo"; accentColor: theme.green }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Lista profili"
                    subtitle: "Profili osservativi salvati"
                    accentColor: theme.cyan

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
                                color: theme.textPrimary
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            Button {
                                text: "Imposta attivo"
                                enabled: modelData.active !== 1
                                onClicked: controller.setActiveEquipmentProfile(modelData.id)
                            }

                            Button {
                                text: "Rinomina"
                                onClicked: {
                                    root.renameProfileId = modelData.id
                                    renameProfileName.text = modelData.profile_name
                                    renameProfileDialog.open()
                                }
                            }

                            Button {
                                text: "Elimina"
                                onClicked: controller.deleteEquipmentProfile(modelData.id)
                            }
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Aggiungi profilo"
                        onClicked: addProfileDialog.open()
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Equipaggiamento assegnato"
                subtitle: "Elementi catalogo assegnati al profilo attivo"
                accentColor: theme.amber

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1180 ? 3 : 1
                    columnSpacing: 16
                    rowSpacing: 16

                    EquipmentGroup {
                        title: "Telescopi"
                        emptyText: "Nessun telescopio assegnato. Il profilo usa Occhio nudo."
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "telescope" })
                        accent: theme.cyan
                    }

                    EquipmentGroup {
                        title: "Oculari"
                        emptyText: "Nessun oculare assegnato."
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "eyepiece" })
                        accent: theme.teal
                    }

                    EquipmentGroup {
                        title: "Barlow"
                        emptyText: "Nessuna Barlow assegnata."
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "barlow" })
                        accent: theme.violet
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    Button {
                        Layout.fillWidth: true
                        text: "Aggiungi equipaggiamento"
                        onClicked: addEquipmentDialog.open()
                    }

                    Button {
                        Layout.fillWidth: true
                        enabled: controller.profileAssignedEquipment.length > 0
                        text: "Rimuovi equipaggiamento"
                        onClicked: removeEquipmentDialog.open()
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Capacita del profilo"
                subtitle: controller.telescopeCapabilities.name
                accentColor: theme.violet

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1180 ? 4 : 2
                    columnSpacing: 10
                    rowSpacing: 10

                    MetricTile { label: "Apertura"; value: controller.telescopeCapabilities.aperture; accentColor: theme.cyan }
                    MetricTile { label: "Focale"; value: controller.telescopeCapabilities.focalLength; accentColor: theme.teal }
                    MetricTile { label: "Magnificazione minima"; value: controller.telescopeCapabilities.availableMagnificationMin; accentColor: theme.green }
                    MetricTile { label: "Magnificazione massima"; value: controller.telescopeCapabilities.availableMagnificationMax; accentColor: theme.amber }
                    MetricTile { label: "Pupilla minima"; value: controller.telescopeCapabilities.exitPupilMin; accentColor: theme.coral }
                    MetricTile { label: "Pupilla massima"; value: controller.telescopeCapabilities.exitPupilMax; accentColor: theme.violet }
                    MetricTile { label: "Campo reale minimo"; value: controller.telescopeCapabilities.trueFieldMin; accentColor: theme.cyan }
                    MetricTile { label: "Campo reale massimo"; value: controller.telescopeCapabilities.trueFieldMax; accentColor: theme.teal }
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: controller.telescopeCapabilities.availableConfigurations || []
                        delegate: StatusPill { text: modelData.magnification; accentColor: theme.cyan }
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    component EquipmentGroup: ColumnLayout {
        id: group
        property string title: ""
        property string emptyText: ""
        property var items: []
        property color accent: "#65d6e8"

        Layout.fillWidth: true
        spacing: 8

        Text {
            Layout.fillWidth: true
            text: title
            color: theme.textPrimary
            font.pixelSize: 16
            font.weight: Font.DemiBold
        }

        Text {
            Layout.fillWidth: true
            visible: items.length === 0
            text: emptyText
            color: theme.textSecondary
            font.pixelSize: 13
            wrapMode: Text.WordWrap
        }

        Repeater {
            model: items
            delegate: RowLayout {
                Layout.fillWidth: true
                spacing: 8
                StatusPill { text: "✓"; accentColor: theme.green }
                Text {
                    Layout.fillWidth: true
                    text: modelData.name
                    color: theme.textPrimary
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                StatusPill { text: modelData.details; accentColor: group.accent }
            }
        }
    }

    component EquipmentRow: Rectangle {
        id: equipmentRow
        property var itemData
        property string actionText: ""
        property color accent: "#65d6e8"
        signal action()

        Layout.fillWidth: true
        implicitHeight: 64
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
                    text: itemData.name
                    color: theme.textPrimary
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: itemData.details
                    color: theme.textSecondary
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }
            }

            StatusPill { text: itemData.badge; accentColor: equipmentRow.accent }

            Button {
                text: actionText
                enabled: actionText.indexOf("Assegna") < 0 || !itemData.assigned
                onClicked: equipmentRow.action()
            }
        }
    }

    DarkDialog {
        id: addProfileDialog
        title: "Aggiungi profilo"
        acceptText: "Aggiungi"
        onAccepted: controller.addEquipmentProfile(addProfileName.text)

        TextField {
            id: addProfileName
            Layout.fillWidth: true
            placeholderText: "Nome profilo"
        }
    }

    DarkDialog {
        id: renameProfileDialog
        title: "Rinomina profilo"
        acceptText: "Rinomina"
        onAccepted: controller.renameEquipmentProfile(root.renameProfileId, renameProfileName.text)

        TextField {
            id: renameProfileName
            Layout.fillWidth: true
            placeholderText: "Nome profilo"
        }
    }

    DarkDialog {
        id: addEquipmentDialog
        title: "Aggiungi equipaggiamento"
        showAccept: false

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            ComboBox {
                Layout.preferredWidth: 160
                model: ["Tutti", "Telescopi", "Oculari", "Barlow"]
                onCurrentTextChanged: root.addFilter = currentText
            }
            TextField {
                Layout.fillWidth: true
                placeholderText: "Cerca..."
                onTextChanged: root.addSearch = text
            }
        }

        Repeater {
            model: controller.profileEquipmentCatalog.filter(function(item) { return root.matchesFilter(item, root.addFilter, root.addSearch) })
            delegate: EquipmentRow {
                itemData: modelData
                actionText: modelData.assigned ? "Gia assegnato" : "Assegna al profilo"
                accent: modelData.kind === "telescope" ? theme.cyan : modelData.kind === "eyepiece" ? theme.teal : theme.violet
                onAction: controller.assignEquipmentToActiveProfile(modelData.kind, modelData.id)
            }
        }
    }

    DarkDialog {
        id: removeEquipmentDialog
        title: "Rimuovi equipaggiamento"
        showAccept: false

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            ComboBox {
                Layout.preferredWidth: 160
                model: ["Tutti", "Telescopi", "Oculari", "Barlow"]
                onCurrentTextChanged: root.removeFilter = currentText
            }
            TextField {
                Layout.fillWidth: true
                placeholderText: "Cerca..."
                onTextChanged: root.removeSearch = text
            }
        }

        Repeater {
            model: controller.profileAssignedEquipment.filter(function(item) { return root.matchesFilter(item, root.removeFilter, root.removeSearch) })
            delegate: EquipmentRow {
                itemData: modelData
                actionText: "Rimuovi dal profilo"
                accent: modelData.kind === "telescope" ? theme.cyan : modelData.kind === "eyepiece" ? theme.teal : theme.violet
                onAction: controller.removeEquipmentFromActiveProfile(modelData.kind, modelData.id)
            }
        }
    }
}

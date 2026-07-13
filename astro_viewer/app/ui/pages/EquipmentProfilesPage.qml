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
    readonly property var equipmentFilterOptions: [
        { "label": qsTr("Tutti"), "value": "Tutti" },
        { "label": qsTr("Telescopi"), "value": "Telescopi" },
        { "label": qsTr("Oculari"), "value": "Oculari" },
        { "label": "Barlow", "value": "Barlow" },
        { "label": qsTr("Binocoli"), "value": "Binocoli" },
        { "label": qsTr("Filtri"), "value": "Filtri" },
        { "label": qsTr("Riduttori"), "value": "Riduttori" }
    ]

    function matchesFilter(item, filter, searchText) {
        var typeOk = filter === "Tutti"
            || (filter === "Telescopi" && item.kind === "telescope")
            || (filter === "Oculari" && item.kind === "eyepiece")
            || (filter === "Barlow" && item.kind === "barlow")
            || (filter === "Binocoli" && item.kind === "binocular")
            || (filter === "Filtri" && item.kind === "filter")
            || (filter === "Riduttori" && item.kind === "reducer")
        var text = (item.name + " " + item.badge + " " + item.details + " " + (item.type || "")).toLowerCase()
        return typeOk && text.indexOf((searchText || "").toLowerCase()) >= 0
    }

    function filteredAddEquipment() {
        return controller.profileEquipmentCatalog.filter(function(item) {
            return root.matchesFilter(item, root.addFilter, root.addSearch)
        })
    }

    function filteredAssignedEquipment() {
        return controller.profileAssignedEquipment.filter(function(item) {
            return root.matchesFilter(item, root.removeFilter, root.removeSearch)
        })
    }

    function equipmentAccent(item) {
        if (item.kind === "telescope")
            return theme.cyan
        if (item.kind === "eyepiece")
            return item.badge === "Zoom" ? theme.violet : theme.teal
        if (item.kind === "binocular")
            return theme.cyan
        if (item.kind === "filter")
            return theme.green
        if (item.kind === "reducer")
            return theme.coral
        return theme.amber
    }

    function binocularExitPupil(binocular) {
        var magnification = Number(binocular.magnification || 0)
        var objective = Number(binocular.objectiveDiameterMm || binocular.objective_diameter_mm || 0)
        if (magnification <= 0 || objective <= 0)
            return "n/d"
        return (objective / magnification).toFixed(1) + " mm"
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
                    text: qsTr("Profili")
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
                id: profileGrid
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                columns: root.width > 1180 ? 2 : 1
                columnSpacing: 16
                rowSpacing: 16

                GlassCard {
                    id: activeProfileCard
                    visible: controller.equipmentProfiles.length !== 1
                    Layout.fillWidth: true
                    title: qsTr("Profilo attivo")
                    subtitle: qsTr("Configurazione usata dalle raccomandazioni")
                    accentColor: theme.green

                    Text {
                        Layout.fillWidth: true
                        text: controller.activeEquipmentProfile.profile_name || qsTr("Occhio nudo")
                        color: theme.textPrimary
                        font.pixelSize: 26
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    StatusPill { text: qsTr("Attivo"); accentColor: theme.green }
                }

                GlassCard {
                    Layout.fillWidth: true
                    Layout.columnSpan: activeProfileCard.visible ? 1 : profileGrid.columns
                    title: controller.equipmentProfiles.length === 1 ? qsTr("Profilo") : qsTr("Lista profili")
                    subtitle: qsTr("Profili osservativi salvati")
                    accentColor: theme.cyan

                    Repeater {
                        model: controller.equipmentProfiles

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatusPill {
                                text: modelData.active === 1 ? qsTr("Attivo") : qsTr("Profilo")
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

                            DarkButton {
                                text: qsTr("Imposta attivo")
                                enabled: modelData.active !== 1
                                onClicked: controller.setActiveEquipmentProfile(modelData.id)
                            }

                            DarkButton {
                                text: qsTr("Rinomina")
                                onClicked: {
                                    root.renameProfileId = modelData.id
                                    renameProfileName.text = modelData.profile_name
                                    renameProfileDialog.open()
                                }
                            }

                            DarkButton {
                                text: qsTr("Elimina")
                                danger: true
                                onClicked: controller.deleteEquipmentProfile(modelData.id)
                            }
                        }
                    }

                    DarkButton {
                        Layout.fillWidth: true
                        text: qsTr("Aggiungi profilo")
                        onClicked: addProfileDialog.open()
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Equipaggiamento assegnato")
                subtitle: qsTr("Elementi catalogo assegnati al profilo attivo")
                accentColor: theme.amber

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1180 ? 3 : 1
                    columnSpacing: 16
                    rowSpacing: 16

                    EquipmentGroup {
                        Layout.preferredWidth: 1
                        title: qsTr("Telescopi")
                        emptyText: qsTr("Nessun telescopio assegnato. Il profilo usa Occhio nudo.")
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "telescope" })
                        accent: theme.cyan
                    }

                    EquipmentGroup {
                        Layout.preferredWidth: 1
                        title: qsTr("Oculari")
                        emptyText: qsTr("Nessun oculare assegnato.")
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "eyepiece" })
                        accent: theme.teal
                    }

                    EquipmentGroup {
                        Layout.preferredWidth: 1
                        title: qsTr("Barlow")
                        emptyText: qsTr("Nessuna Barlow assegnata.")
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "barlow" })
                        accent: theme.violet
                    }

                    EquipmentGroup {
                        Layout.preferredWidth: 1
                        title: qsTr("Binocoli")
                        emptyText: qsTr("Nessun binocolo assegnato.")
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "binocular" })
                        accent: theme.cyan
                    }

                    EquipmentGroup {
                        Layout.preferredWidth: 1
                        title: qsTr("Filtri")
                        emptyText: qsTr("Nessun filtro assegnato.")
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "filter" })
                        accent: theme.green
                    }

                    EquipmentGroup {
                        Layout.preferredWidth: 1
                        title: qsTr("Riduttori")
                        emptyText: qsTr("Nessun riduttore assegnato.")
                        items: controller.profileAssignedEquipment.filter(function(item) { return item.kind === "reducer" })
                        accent: theme.coral
                    }
                }

                RowLayout {
                    Layout.fillWidth: true
                    spacing: 10

                    DarkButton {
                        Layout.fillWidth: true
                        text: qsTr("Aggiungi equipaggiamento")
                        onClicked: addEquipmentDialog.open()
                    }

                    DarkButton {
                        Layout.fillWidth: true
                        enabled: controller.profileAssignedEquipment.length > 0
                        text: qsTr("Rimuovi equipaggiamento")
                        onClicked: removeEquipmentDialog.open()
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Capacità del profilo")
                subtitle: controller.telescopeCapabilities.name
                accentColor: theme.violet

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1180 ? 4 : 2
                    columnSpacing: 10
                    rowSpacing: 10

                    MetricTile { label: qsTr("Apertura"); value: controller.telescopeCapabilities.aperture; accentColor: theme.cyan }
                    MetricTile { label: qsTr("Focale"); value: controller.telescopeCapabilities.focalLength; accentColor: theme.teal }
                    MetricTile { label: qsTr("Magnificazione minima"); value: controller.telescopeCapabilities.availableMagnificationMin; accentColor: theme.green }
                    MetricTile { label: qsTr("Magnificazione massima"); value: controller.telescopeCapabilities.availableMagnificationMax; accentColor: theme.amber }
                    MetricTile { label: qsTr("Pupilla minima"); value: controller.telescopeCapabilities.exitPupilMin; accentColor: theme.coral }
                    MetricTile { label: qsTr("Pupilla massima"); value: controller.telescopeCapabilities.exitPupilMax; accentColor: theme.violet }
                    MetricTile { label: qsTr("Campo reale minimo"); value: controller.telescopeCapabilities.trueFieldMin; accentColor: theme.cyan }
                    MetricTile { label: qsTr("Campo reale massimo"); value: controller.telescopeCapabilities.trueFieldMax; accentColor: theme.teal }
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

            GlassCard {
                visible: controller.profileBinoculars.length > 0
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: qsTr("Binocoli del profilo")
                subtitle: qsTr("Capacità derivate dai binocoli assegnati")
                accentColor: theme.cyan

                Flow {
                    Layout.fillWidth: true
                    spacing: 10

                    Repeater {
                        model: controller.profileBinoculars
                        delegate: BinocularCapabilityCard { itemData: modelData }
                    }
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    component BinocularCapabilityCard: Rectangle {
        id: binocularCard
        property var itemData

        width: Math.min(260, Math.max(190, root.width > 900 ? (root.width - 112) / 3 : root.width - 88))
        height: 132
        radius: 8
        color: "#20242b"
        border.color: "#303641"
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 12
            spacing: 8

            Text {
                Layout.fillWidth: true
                text: itemData.name
                color: theme.textPrimary
                font.pixelSize: 14
                font.weight: Font.DemiBold
                elide: Text.ElideRight
                maximumLineCount: 1
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                StatusPill { text: itemData.specLabel || ""; accentColor: theme.cyan }
                StatusPill {
                    visible: itemData.imageStabilized === true
                    text: qsTr("IS")
                    accentColor: theme.violet
                }
                Item { Layout.fillWidth: true }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 2

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Pupilla d’uscita")
                    color: theme.textSecondary
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: root.binocularExitPupil(itemData)
                    color: theme.textPrimary
                    font.pixelSize: 20
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
            }
        }
    }

    component EquipmentGroup: ColumnLayout {
        id: group
        property string title: ""
        property string emptyText: ""
        property var items: []
        property color accent: "#65d6e8"

        Layout.fillWidth: true
        Layout.minimumWidth: 0
        Layout.preferredWidth: 1
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
                StatusPill { text: qsTr("✓"); accentColor: theme.green }
                Text {
                    Layout.fillWidth: true
                    text: modelData.name
                    color: theme.textPrimary
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }
                StatusPill { text: modelData.details; accentColor: group.accent }
                StatusPill {
                    visible: (modelData.secondaryBadge || "").length > 0
                    text: modelData.secondaryBadge || ""
                    accentColor: theme.violet
                }
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

            DarkButton {
                text: actionText
                enabled: actionText.indexOf("Assegna") < 0 || !itemData.assigned
                onClicked: equipmentRow.action()
            }
        }
    }

    component EquipmentCatalogCard: Rectangle {
        id: equipmentCard
        property var itemData
        signal action()

        width: addEquipmentGrid.cellWidth - 10
        height: 96
        radius: 8
        color: cardMouse.containsMouse ? "#252b34" : "#20242b"
        border.color: itemData.assigned ? Qt.rgba(theme.green.r, theme.green.g, theme.green.b, 0.52) : "#303641"
        border.width: 1

        ColumnLayout {
            anchors.fill: parent
            anchors.margins: 10
            spacing: 8

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    text: itemData.name
                    color: theme.textPrimary
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                StatusPill {
                    text: itemData.badge
                    accentColor: root.equipmentAccent(itemData)
                }
            }

            RowLayout {
                Layout.fillWidth: true
                spacing: 10

                Text {
                    Layout.fillWidth: true
                    text: itemData.details
                    color: theme.textSecondary
                    font.pixelSize: 13
                    elide: Text.ElideRight
                    maximumLineCount: 1
                }

                DarkButton {
                    text: itemData.assigned ? qsTr("Già assegnato") : qsTr("Assegna")
                    implicitHeight: 32
                    leftPadding: 10
                    rightPadding: 10
                    enabled: !itemData.assigned
                    accentColor: root.equipmentAccent(itemData)
                    onClicked: equipmentCard.action()
                }
            }
        }

        MouseArea {
            id: cardMouse
            anchors.fill: parent
            hoverEnabled: true
            cursorShape: itemData.assigned ? Qt.ArrowCursor : Qt.PointingHandCursor
            onClicked: {
                if (!itemData.assigned)
                    equipmentCard.action()
            }
        }
    }

    DarkDialog {
        id: addProfileDialog
        title: qsTr("Aggiungi profilo")
        acceptText: qsTr("Aggiungi")
        onAccepted: controller.addEquipmentProfile(addProfileName.text)

        DarkTextField {
            id: addProfileName
            Layout.fillWidth: true
            placeholderText: qsTr("Nome profilo")
        }
    }

    DarkDialog {
        id: renameProfileDialog
        title: qsTr("Rinomina profilo")
        acceptText: qsTr("Rinomina")
        onAccepted: controller.renameEquipmentProfile(root.renameProfileId, renameProfileName.text)

        DarkTextField {
            id: renameProfileName
            Layout.fillWidth: true
            placeholderText: qsTr("Nome profilo")
        }
    }

    DarkDialog {
        id: addEquipmentDialog
        title: qsTr("Aggiungi equipaggiamento")
        preferredWidth: 960
        showAccept: false
        cancelText: qsTr("Chiudi")

        DarkTextField {
            Layout.fillWidth: true
            placeholderText: qsTr("Cerca equipaggiamento...")
            onTextChanged: root.addSearch = text
        }

        Flow {
            Layout.fillWidth: true
            spacing: 8

            Repeater {
                model: root.equipmentFilterOptions

                delegate: DarkButton {
                    text: modelData.label
                    checkable: false
                    checked: root.addFilter === modelData.value
                    accentColor: modelData.value === "Telescopi" ? theme.cyan : modelData.value === "Oculari" ? theme.teal : modelData.value === "Barlow" ? theme.amber : modelData.value === "Binocoli" ? theme.cyan : modelData.value === "Filtri" ? theme.green : modelData.value === "Riduttori" ? theme.coral : theme.violet
                    onClicked: {
                        if (root.addFilter !== modelData.value)
                            root.addFilter = modelData.value
                    }
                }
            }
        }

        Text {
            Layout.fillWidth: true
            text: root.filteredAddEquipment().length + qsTr(" risultati")
            color: theme.textMuted
            font.pixelSize: 12
            elide: Text.ElideRight
        }

        GridView {
            id: addEquipmentGrid
            Layout.fillWidth: true
            Layout.preferredHeight: Math.max(240, Math.min(480, root.height - 340))
            clip: true
            cellWidth: width > 700 ? Math.floor(width / 2) : width
            cellHeight: 106
            boundsBehavior: Flickable.StopAtBounds
            model: root.filteredAddEquipment()
            ScrollBar.vertical: ScrollBar { }

            delegate: EquipmentCatalogCard {
                itemData: modelData
                onAction: {
                    controller.assignEquipmentToActiveProfile(modelData.kind, modelData.id)
                    addEquipmentDialog.close()
                }
            }

            Text {
                anchors.centerIn: parent
                visible: addEquipmentGrid.count === 0
                text: qsTr("Nessun elemento trovato.")
                color: theme.textSecondary
                font.pixelSize: 13
            }
        }
    }

    DarkDialog {
        id: removeEquipmentDialog
        title: qsTr("Rimuovi equipaggiamento")
        showAccept: false
        cancelText: qsTr("Chiudi")

        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            DarkComboBox {
                Layout.preferredWidth: 160
                model: root.equipmentFilterOptions
                textRole: "label"
                onActivated: function(index) { root.removeFilter = model[index].value }
            }
            DarkTextField {
                Layout.fillWidth: true
                placeholderText: qsTr("Cerca...")
                onTextChanged: root.removeSearch = text
            }
        }

        Repeater {
            model: root.filteredAssignedEquipment()
            delegate: EquipmentRow {
                itemData: modelData
                actionText: qsTr("Rimuovi dal profilo")
                accent: root.equipmentAccent(modelData)
                onAction: controller.removeEquipmentFromActiveProfile(modelData.kind, modelData.id)
            }
        }
    }
}

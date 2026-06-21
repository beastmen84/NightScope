import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property int renameProfileId: -1

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
                    text: "Strumenti"
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
                    subtitle: "Usato da raccomandazioni, planner e schede oggetto"
                    accentColor: theme.green

                    Text {
                        Layout.fillWidth: true
                        text: controller.activeEquipmentProfile.profile_name || "Occhio nudo"
                        color: theme.textPrimary
                        font.pixelSize: 26
                        font.weight: Font.DemiBold
                        elide: Text.ElideRight
                    }

                    StatusPill {
                        text: controller.currentSetup.name
                        accentColor: theme.green
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Lista profili"
                    subtitle: "Nessuna duplicazione automatica"
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
                                text: "Set Active"
                                enabled: modelData.active !== 1
                                onClicked: controller.setActiveEquipmentProfile(modelData.id)
                            }

                            Button {
                                text: "Rename"
                                onClicked: {
                                    root.renameProfileId = modelData.id
                                    renameProfileName.text = modelData.profile_name
                                    renameProfileDialog.open()
                                }
                            }

                            Button {
                                text: "Delete"
                                onClicked: controller.deleteEquipmentProfile(modelData.id)
                            }
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Add Profile"
                        onClicked: addProfileDialog.open()
                    }
                }
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
                    title: "Telescopes assigned"
                    subtitle: "Tubi ottici disponibili in questo profilo"
                    accentColor: theme.cyan

                    Text {
                        Layout.fillWidth: true
                        visible: controller.profileTelescopes.length === 0
                        text: "Nessun telescopio assegnato. Il profilo usera Occhio nudo."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.profileTelescopes

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatusPill { text: "✓"; accentColor: theme.green }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                color: theme.textPrimary
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            StatusPill { text: modelData.apertureMm + "/" + modelData.focalLengthMm + " mm"; accentColor: theme.cyan }

                            Button {
                                text: "Remove"
                                onClicked: controller.removeTelescopeFromActiveProfile(modelData.id)
                            }
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Add Telescope"
                        enabled: controller.availableProfileTelescopes.length > 0
                        onClicked: addProfileTelescopeDialog.open()
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Eyepieces assigned"
                    subtitle: "Solo questi sono usati dai suggerimenti"
                    accentColor: theme.teal

                    Text {
                        Layout.fillWidth: true
                        visible: controller.eyepieces.length === 0
                        text: controller.canUseEyepieces ? "Nessun oculare assegnato al profilo." : "Seleziona un telescopio prima di usare oculari."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.eyepieces

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatusPill { text: "✓"; accentColor: theme.green }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                color: theme.textPrimary
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            StatusPill { text: modelData.focalRangeLabel; accentColor: theme.teal }

                            Button {
                                text: "Remove"
                                onClicked: controller.removeEyepieceFromActiveProfile(modelData.id)
                            }
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Add Eyepiece"
                        enabled: controller.canUseEyepieces && controller.availableProfileEyepieces.length > 0
                        onClicked: addProfileEyepieceDialog.open()
                    }
                }

                GlassCard {
                    Layout.fillWidth: true
                    title: "Barlows assigned"
                    subtitle: "Usate solo quando migliorano la combinazione"
                    accentColor: theme.amber

                    Text {
                        Layout.fillWidth: true
                        visible: controller.profileBarlows.length === 0
                        text: controller.canUseEyepieces ? "Nessuna Barlow assegnata." : "Seleziona un telescopio prima di usare Barlow."
                        color: theme.textSecondary
                        font.pixelSize: 13
                        wrapMode: Text.WordWrap
                    }

                    Repeater {
                        model: controller.profileBarlows

                        delegate: RowLayout {
                            Layout.fillWidth: true
                            spacing: 10

                            StatusPill { text: "✓"; accentColor: theme.green }

                            Text {
                                Layout.fillWidth: true
                                text: modelData.name
                                color: theme.textPrimary
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                elide: Text.ElideRight
                            }

                            StatusPill { text: modelData.multiplier + "x"; accentColor: theme.amber }

                            Button {
                                text: "Remove"
                                onClicked: controller.removeBarlowFromActiveProfile(modelData.id)
                            }
                        }
                    }

                    Button {
                        Layout.fillWidth: true
                        text: "Add Barlow"
                        enabled: controller.canUseEyepieces && controller.availableProfileBarlows.length > 0
                        onClicked: addProfileBarlowDialog.open()
                    }
                }
            }

            GlassCard {
                Layout.fillWidth: true
                Layout.leftMargin: 28
                Layout.rightMargin: 28
                title: "Profile Capabilities"
                subtitle: controller.telescopeCapabilities.name
                accentColor: theme.violet

                GridLayout {
                    Layout.fillWidth: true
                    columns: root.width > 1180 ? 3 : 2
                    columnSpacing: 10
                    rowSpacing: 10

                    MetricTile { label: "Aperture"; value: controller.telescopeCapabilities.aperture; accentColor: theme.cyan }
                    MetricTile { label: "Focal Length"; value: controller.telescopeCapabilities.focalLength; accentColor: theme.teal }
                    MetricTile { label: "Available Magnification Range"; value: controller.telescopeCapabilities.practicalMagnification; accentColor: theme.amber }
                    MetricTile { label: "Light gathering"; value: controller.telescopeCapabilities.lightGathering; accentColor: theme.violet }
                    MetricTile { label: "Limiting magnitude"; value: controller.telescopeCapabilities.limitingMagnitude; accentColor: theme.green }
                    MetricTile { label: "Resolution"; value: controller.telescopeCapabilities.resolution; accentColor: theme.coral }
                }

                Text {
                    Layout.fillWidth: true
                    text: "Available Configurations"
                    color: theme.textPrimary
                    font.pixelSize: 16
                    font.weight: Font.DemiBold
                }

                Flow {
                    Layout.fillWidth: true
                    spacing: 8

                    Repeater {
                        model: controller.telescopeCapabilities.availableConfigurations || []

                        delegate: StatusPill {
                            text: modelData.magnification
                            accentColor: theme.cyan
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    visible: (controller.telescopeCapabilities.availableConfigurations || []).length === 0
                    text: controller.telescopeCapabilities.availableConfigurationsText
                    color: theme.textSecondary
                    font.pixelSize: 13
                    wrapMode: Text.WordWrap
                }
            }

            Item { Layout.fillWidth: true; Layout.preferredHeight: 28 }
        }
    }

    Dialog {
        id: addProfileDialog
        title: "Add Profile"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: controller.addEquipmentProfile(addProfileName.text)

        TextField {
            id: addProfileName
            width: 360
            placeholderText: "Nome profilo"
        }
    }

    Dialog {
        id: renameProfileDialog
        title: "Rename Profile"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: controller.renameEquipmentProfile(root.renameProfileId, renameProfileName.text)

        TextField {
            id: renameProfileName
            width: 360
            placeholderText: "Nome profilo"
        }
    }

    Dialog {
        id: addProfileTelescopeDialog
        title: "Add Telescope"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (profileTelescopeCombo.currentIndex >= 0) {
                controller.assignTelescopeToActiveProfile(controller.availableProfileTelescopes[profileTelescopeCombo.currentIndex].id)
            }
        }

        ComboBox {
            id: profileTelescopeCombo
            width: 420
            model: controller.availableProfileTelescopes
            textRole: "name"
        }
    }

    Dialog {
        id: addProfileEyepieceDialog
        title: "Add Eyepiece"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (profileEyepieceCombo.currentIndex >= 0) {
                controller.assignEyepieceToActiveProfile(controller.availableProfileEyepieces[profileEyepieceCombo.currentIndex].id)
            }
        }

        ComboBox {
            id: profileEyepieceCombo
            width: 420
            model: controller.availableProfileEyepieces
            textRole: "name"
        }
    }

    Dialog {
        id: addProfileBarlowDialog
        title: "Add Barlow"
        modal: true
        standardButtons: Dialog.Ok | Dialog.Cancel
        onAccepted: {
            if (profileBarlowCombo.currentIndex >= 0) {
                controller.assignBarlowToActiveProfile(controller.availableProfileBarlows[profileBarlowCombo.currentIndex].id)
            }
        }

        ComboBox {
            id: profileBarlowCombo
            width: 420
            model: controller.availableProfileBarlows
            textRole: "name"
        }
    }
}

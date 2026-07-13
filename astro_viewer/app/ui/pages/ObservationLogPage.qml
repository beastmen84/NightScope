pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import "../components"

Item {
    id: root

    property var controller
    property string searchQuery: ""
    property int ratingFilter: 0
    property var editedObservation: ({})
    property var pendingDeletion: ({})
    readonly property var summary: controller ? (controller.observationLogSummary || ({})) : ({})

    function filteredObservations() {
        if (!root.controller)
            return []
        var query = root.searchQuery.toLowerCase().trim()
        return root.controller.observationLog.filter(function(item) {
            var ratingMatches = root.ratingFilter === 0 || item.rating === root.ratingFilter
            var searchMatches = query.length === 0 || item.searchText.indexOf(query) >= 0
            return ratingMatches && searchMatches
        })
    }

    function openEditor(item) {
        root.controller.clearObservationMessage()
        root.editedObservation = item || ({})
        var values = item || root.controller.observationLogDefaults
        observationDate.text = values.dateValue || ""
        observationTime.text = values.timeValue || ""
        objectName.text = item ? item.objectName : ""
        locationName.text = values.location || ""
        telescopeName.text = values.telescope || ""
        eyepieceName.text = values.eyepiece || ""
        ratingInput.currentIndex = item ? Math.max(0, Math.min(4, 5 - item.rating)) : 1
        observationNotes.text = item ? item.notes : ""
        editorDialog.title = item ? qsTr("Modifica osservazione") : qsTr("Nuova osservazione")
        editorDialog.open()
    }

    function saveEditor() {
        var rating = 5 - ratingInput.currentIndex
        var saved = false
        if (root.editedObservation.id !== undefined) {
            saved = root.controller.updateObservation(
                root.editedObservation.id,
                observationDate.text,
                observationTime.text,
                objectName.text,
                locationName.text,
                telescopeName.text,
                eyepieceName.text,
                rating,
                observationNotes.text
            )
        } else {
            saved = root.controller.addObservation(
                observationDate.text,
                observationTime.text,
                objectName.text,
                locationName.text,
                telescopeName.text,
                eyepieceName.text,
                rating,
                observationNotes.text
            )
        }
        if (saved)
            editorDialog.close()
    }

    AppTheme { id: theme }

    ColumnLayout {
        anchors.fill: parent
        spacing: 14

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
                    text: qsTr("Log Osservazioni")
                    color: theme.textPrimary
                    font.pixelSize: 34
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: qsTr("Archivio delle sessioni e delle configurazioni utilizzate")
                    color: theme.textSecondary
                    font.pixelSize: 14
                    elide: Text.ElideRight
                }
            }

            DarkButton {
                text: qsTr("Aggiungi osservazione")
                accentColor: theme.teal
                onClicked: root.openEditor(null)
            }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            Layout.rightMargin: 28
            spacing: 8

            StatusPill {
                text: qsTr("Sessioni: ") + (root.summary.total || 0)
                accentColor: theme.cyan
            }
            StatusPill {
                text: qsTr("Oggetti distinti: ") + (root.summary.uniqueObjects || 0)
                accentColor: theme.violet
            }
            StatusPill {
                text: qsTr("Valutazione media: ") + (root.summary.averageRating > 0 ? root.summary.averageRating + "/5" : "-")
                accentColor: theme.amber
            }
            StatusPill {
                text: qsTr("Ultima: ") + (root.summary.latestLabel || "-")
                accentColor: theme.teal
            }
            Item { Layout.fillWidth: true }
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            Layout.rightMargin: 28
            spacing: 10

            DarkTextField {
                Layout.preferredWidth: 340
                placeholderText: qsTr("Cerca oggetto, luogo, setup o note...")
                onTextChanged: root.searchQuery = text
            }

            DarkComboBox {
                Layout.preferredWidth: 190
                model: [qsTr("Tutte le valutazioni"), "5/5", "4/5", "3/5", "2/5", "1/5"]
                onCurrentIndexChanged: root.ratingFilter = currentIndex === 0 ? 0 : 6 - currentIndex
            }

            Text {
                Layout.fillWidth: true
                text: root.filteredObservations().length === 1
                      ? qsTr("1 risultato")
                      : root.filteredObservations().length + qsTr(" risultati")
                color: theme.textSecondary
                font.pixelSize: 12
                horizontalAlignment: Text.AlignRight
                elide: Text.ElideRight
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 28
            Layout.rightMargin: 28
            visible: text.length > 0
            text: root.controller ? root.controller.observationMessage : ""
            color: theme.teal
            font.pixelSize: 12
            elide: Text.ElideRight
        }

        Rectangle {
            Layout.fillWidth: true
            Layout.fillHeight: true
            Layout.leftMargin: 28
            Layout.rightMargin: 28
            Layout.bottomMargin: 28
            radius: 8
            color: "#171a20"
            border.color: "#303641"
            border.width: 1

            ColumnLayout {
                anchors.fill: parent
                spacing: 0

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 42
                    color: "#20242b"
                    radius: 8

                    RowLayout {
                        anchors.fill: parent
                        anchors.leftMargin: 14
                        anchors.rightMargin: 14
                        spacing: 12

                        Text { Layout.preferredWidth: 126; text: qsTr("Data e ora"); color: theme.textSecondary; font.pixelSize: 11; font.weight: Font.DemiBold }
                        Text { Layout.preferredWidth: 138; text: qsTr("Oggetto"); color: theme.textSecondary; font.pixelSize: 11; font.weight: Font.DemiBold }
                        Text { Layout.fillWidth: true; text: qsTr("Dettagli"); color: theme.textSecondary; font.pixelSize: 11; font.weight: Font.DemiBold }
                        Text { Layout.preferredWidth: 54; text: qsTr("Voto"); color: theme.textSecondary; font.pixelSize: 11; font.weight: Font.DemiBold; horizontalAlignment: Text.AlignHCenter }
                        Item { Layout.preferredWidth: 142 }
                    }
                }

                ListView {
                    id: observationList
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    clip: true
                    model: root.filteredObservations()
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: ScrollBar { policy: ScrollBar.AsNeeded }

                    delegate: Rectangle {
                        id: observationRow
                        required property var modelData
                        required property int index
                        width: observationList.width
                        height: 88
                        color: index % 2 === 0 ? "#171a20" : "#1a1e25"

                        Rectangle {
                            anchors.left: parent.left
                            anchors.right: parent.right
                            anchors.bottom: parent.bottom
                            height: 1
                            color: "#252b34"
                        }

                        RowLayout {
                            anchors.fill: parent
                            anchors.leftMargin: 14
                            anchors.rightMargin: 14
                            spacing: 12

                            Text {
                                Layout.preferredWidth: 126
                                text: observationRow.modelData.dateLabel
                                color: theme.textSecondary
                                font.pixelSize: 12
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }

                            Text {
                                Layout.preferredWidth: 138
                                text: observationRow.modelData.objectName
                                color: theme.textPrimary
                                font.pixelSize: 14
                                font.weight: Font.DemiBold
                                wrapMode: Text.WordWrap
                                maximumLineCount: 2
                                elide: Text.ElideRight
                            }

                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 3

                                Text { Layout.fillWidth: true; text: observationRow.modelData.locationLabel; color: theme.textSecondary; font.pixelSize: 12; elide: Text.ElideRight }
                                Text { Layout.fillWidth: true; text: observationRow.modelData.setupLabel; color: theme.cyan; font.pixelSize: 12; elide: Text.ElideRight }
                                Text { Layout.fillWidth: true; text: observationRow.modelData.notesLabel; color: theme.textMuted; font.pixelSize: 11; elide: Text.ElideRight }
                            }

                            Text {
                                Layout.preferredWidth: 54
                                text: observationRow.modelData.ratingLabel
                                color: theme.amber
                                font.pixelSize: 13
                                font.weight: Font.DemiBold
                                horizontalAlignment: Text.AlignHCenter
                            }

                            RowLayout {
                                Layout.preferredWidth: 142
                                spacing: 6

                                DarkButton {
                                    Layout.fillWidth: true
                                    text: qsTr("Modifica")
                                    onClicked: root.openEditor(observationRow.modelData)
                                }
                                DarkButton {
                                    Layout.fillWidth: true
                                    text: qsTr("Elimina")
                                    danger: true
                                    onClicked: {
                                        root.pendingDeletion = observationRow.modelData
                                        deleteDialog.open()
                                    }
                                }
                            }
                        }
                    }

                    Text {
                        anchors.centerIn: parent
                        visible: observationList.count === 0
                        width: Math.min(440, parent.width - 40)
                        text: root.controller && root.controller.observationLog.length > 0
                              ? qsTr("Nessuna osservazione corrisponde ai filtri.")
                              : qsTr("Il log è vuoto. Aggiungi la prima osservazione.")
                        color: theme.textSecondary
                        font.pixelSize: 14
                        horizontalAlignment: Text.AlignHCenter
                        wrapMode: Text.WordWrap
                    }
                }
            }
        }
    }

    DarkDialog {
        id: editorDialog
        parent: root
        preferredWidth: 760
        acceptText: root.editedObservation.id !== undefined ? qsTr("Salva modifiche") : qsTr("Aggiungi")
        closeOnAccept: false
        onAccepted: root.saveEditor()

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Text { text: qsTr("Data"); color: theme.textSecondary; font.pixelSize: 12 }
                DarkTextField {
                    id: observationDate
                    Layout.fillWidth: true
                    placeholderText: qsTr("AAAA-MM-GG")
                    validator: RegularExpressionValidator { regularExpression: /\d{4}-\d{2}-\d{2}/ }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 150
                spacing: 6
                Text { text: qsTr("Ora"); color: theme.textSecondary; font.pixelSize: 12 }
                DarkTextField {
                    id: observationTime
                    Layout.fillWidth: true
                    placeholderText: qsTr("HH:MM")
                    validator: RegularExpressionValidator { regularExpression: /\d{2}:\d{2}/ }
                }
            }

            ColumnLayout {
                Layout.preferredWidth: 120
                spacing: 6
                Text { text: qsTr("Valutazione"); color: theme.textSecondary; font.pixelSize: 12 }
                DarkComboBox { id: ratingInput; Layout.fillWidth: true; model: ["5/5", "4/5", "3/5", "2/5", "1/5"] }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text { text: qsTr("Oggetto osservato"); color: theme.textSecondary; font.pixelSize: 12 }
            DarkTextField { id: objectName; Layout.fillWidth: true; placeholderText: qsTr("Es. M42, Giove, Luna") }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text { text: qsTr("Luogo"); color: theme.textSecondary; font.pixelSize: 12 }
            DarkTextField { id: locationName; Layout.fillWidth: true; placeholderText: qsTr("Località di osservazione") }
        }

        RowLayout {
            Layout.fillWidth: true
            spacing: 12

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Text { text: qsTr("Telescopio"); color: theme.textSecondary; font.pixelSize: 12 }
                DarkTextField { id: telescopeName; Layout.fillWidth: true; placeholderText: qsTr("Telescopio utilizzato") }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: 6
                Text { text: qsTr("Oculare"); color: theme.textSecondary; font.pixelSize: 12 }
                DarkTextField { id: eyepieceName; Layout.fillWidth: true; placeholderText: qsTr("Oculare utilizzato") }
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 6
            Text { text: qsTr("Note"); color: theme.textSecondary; font.pixelSize: 12 }
            DarkTextArea { id: observationNotes; Layout.fillWidth: true; placeholderText: qsTr("Condizioni, dettagli visibili e impressioni") }
        }

        Text {
            Layout.fillWidth: true
            visible: text.length > 0
            text: root.controller ? root.controller.observationMessage : ""
            color: theme.coral
            font.pixelSize: 12
            wrapMode: Text.WordWrap
        }
    }

    DarkDialog {
        id: deleteDialog
        parent: root
        title: qsTr("Elimina osservazione")
        acceptText: qsTr("Elimina")
        acceptDanger: true
        preferredWidth: 480
        onAccepted: {
            if (root.pendingDeletion.id !== undefined)
                root.controller.deleteObservation(root.pendingDeletion.id)
        }

        Text {
            Layout.fillWidth: true
            text: qsTr("L'osservazione di ") + (root.pendingDeletion.objectName || qsTr("questo oggetto")) + qsTr(" verrà eliminata definitivamente.")
            color: theme.textSecondary
            font.pixelSize: 14
            wrapMode: Text.WordWrap
        }
    }
}

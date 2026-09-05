// Purpose: Preview and confirm a personal object image, or restore the default.
// Contract: Delegates persistence to the image manager; red mode opens no file picker or image source.

import QtQuick
import QtQuick.Layouts
import QtQuick.Dialogs as NativeDialogs

DarkDialog {
    id: root
    objectName: "objectImageEditor"
    property var manager
    property var objectData: ({})
    property bool imageUnavailable: false
    readonly property var imageState: manager ? manager.state : ({})
    title: qsTr("Immagine personale")
    preferredWidth: 620
    dialogPadding: 22
    acceptText: qsTr("Usa questa immagine")
    cancelText: qsTr("Chiudi")
    acceptEnabled: imageState.ready === true && !imageState.busy && !theme.redNightVision
    closeOnAccept: false
    onAccepted: { if (manager.save()) root.close() }
    onClosed: { picker.close(); resetConfirmation.close(); if (manager) manager.cancel() }

    function openForObject() {
        if (manager && manager.setTarget(objectData.id || "")) {
            manager.setNightVision(theme.redNightVision)
            root.open()
        }
    }

    function errorText(code) {
        switch (code) {
        case "local_file": return qsTr("Scegli un file locale JPEG o PNG.")
        case "format": return qsTr("Formato non supportato. Usa JPEG o PNG; FITS, TIFF e immagini animate non sono supportati.")
        case "size": return qsTr("Il file supera il limite di 20 MB.")
        case "dimensions": return qsTr("L'immagine supera 32 megapixel o 12.000 pixel per lato, oppure ha dimensioni non valide.")
        case "decode": return qsTr("L'immagine non può essere decodificata: il file potrebbe essere danneggiato.")
        case "read": return qsTr("Impossibile leggere il file selezionato.")
        case "storage": return qsTr("Impossibile salvare l'immagine. Controlla spazio disponibile e permessi; l'associazione precedente non è stata cambiata.")
        default: return ""
        }
    }

    AppTheme {
        id: theme
        onRedNightVisionChanged: {
            if (root.manager) root.manager.setNightVision(redNightVision)
            if (redNightVision) picker.close()
        }
    }

    Text {
        Layout.fillWidth: true
        text: root.objectData.name || ""
        color: theme.textPrimary
        font.pixelSize: 16
        wrapMode: Text.WordWrap
    }
    Text {
        Layout.fillWidth: true
        text: qsTr("La foto resta sul tuo computer ed è condivisa dagli alias dello stesso oggetto. L'originale non viene modificato.")
        color: theme.textSecondary
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Text {
        Layout.fillWidth: true
        text: qsTr("JPEG o PNG, massimo 20 MB e 32 megapixel. Copia ottimizzata fino a 1600 pixel, senza ritaglio e senza metadati personali.")
        color: theme.textMuted
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Rectangle {
        Layout.fillWidth: true
        Layout.preferredHeight: visible ? 180 : 0
        visible: root.imageState.ready === true && !theme.redNightVision
        color: theme.imageWell
        radius: 8
        Image {
            objectName: "personalImagePreview"
            anchors.fill: parent
            anchors.margins: 8
            source: root.visible && !theme.redNightVision ? (root.imageState.previewUrl || "") : ""
            asynchronous: true
            fillMode: Image.PreserveAspectFit
            sourceSize.width: 560
            sourceSize.height: 360
        }
    }
    Text {
        Layout.fillWidth: true
        visible: theme.redNightVision
        text: qsTr("Disattiva la visione rossa per scegliere e visualizzare una foto. Puoi comunque ripristinare l'immagine predefinita.")
        color: theme.textSecondary
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Text {
        Layout.fillWidth: true
        visible: root.imageUnavailable || root.objectData.personalImageMissing === true
        text: qsTr("La foto personale non è disponibile. Viene mostrata l'immagine predefinita; puoi sostituire la foto o ripristinare il predefinito.")
        color: theme.amber
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    Text {
        Layout.fillWidth: true
        visible: root.imageState.busy === true || (root.imageState.errorCode || "").length > 0
        text: root.imageState.busy ? qsTr("Preparazione anteprima...") : root.errorText(root.imageState.errorCode)
        color: root.imageState.busy ? theme.textSecondary : theme.amber
        font.pixelSize: 12
        wrapMode: Text.WordWrap
    }
    RowLayout {
        Layout.fillWidth: true
        spacing: 10
        DarkButton {
            objectName: "choosePersonalImage"
            text: qsTr("Scegli una foto...")
            enabled: !root.imageState.busy && !theme.redNightVision
            onClicked: picker.open()
        }
        DarkButton {
            objectName: "resetPersonalImage"
            text: qsTr("Ripristina predefinita")
            enabled: root.imageState.hasPersonalImage === true && !root.imageState.busy
            onClicked: resetConfirmation.open()
        }
    }

    NativeDialogs.FileDialog {
        id: picker
        objectName: "personalPhotoPicker"
        title: qsTr("Scegli una foto personale")
        nameFilters: [qsTr("Immagini JPEG e PNG (*.jpg *.jpeg *.png)")]
        fileMode: NativeDialogs.FileDialog.OpenFile
        onAccepted: { if (!theme.redNightVision && root.visible) root.manager.choose(selectedFile) }
    }
    DarkDialog {
        id: resetConfirmation
        objectName: "resetImageConfirmation"
        parent: root.parent
        title: qsTr("Ripristinare l'immagine predefinita?")
        preferredWidth: 510
        closeOnAccept: false
        onAccepted: {
            if (root.manager.reset()) { resetConfirmation.close(); root.close() }
        }
        Text {
            Layout.fillWidth: true
            text: qsTr("Verrà rimossa l'associazione alla foto personale, non il file originale. Gli altri dati dell'oggetto resteranno invariati.")
            color: theme.textSecondary
            wrapMode: Text.WordWrap
        }
    }
}

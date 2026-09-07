// Purpose: Hold a detached equipment sequence for page-local filtering without repeated Python conversions.
// Contract: Refreshes from the existing inventory and translation notifications; never mutates canonical data.

import QtQuick

QtObject {
    id: root

    property var controller
    property string catalogue: ""
    property var items: []

    function reload() {
        items = controller && catalogue.length > 0
            ? controller.equipmentCatalogueSnapshot(catalogue) : []
    }

    onControllerChanged: reload()
    onCatalogueChanged: reload()
    Component.onCompleted: reload()

    readonly property bool cameraCatalogue: catalogue === "astronomyCameraCatalog" || catalogue === "cameraBodyCatalog"
    readonly property bool profileCatalogue: catalogue === "profileEquipmentCatalog" || catalogue === "profileAssignedEquipment"
    property Connections refreshConnections: Connections {
        target: root.controller
        function onEquipmentChanged() {
            if (!root.cameraCatalogue && !root.profileCatalogue)
                root.reload()
        }
        function onCameraCatalogChanged() {
            if (root.cameraCatalogue)
                root.reload()
        }
        function onProfileInventoryChanged() {
            if (root.profileCatalogue)
                root.reload()
        }
    }
}

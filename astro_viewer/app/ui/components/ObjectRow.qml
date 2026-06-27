import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var itemData
    property string assetBaseUrl: ""
    property string typeText: ""
    property string visibilityText: ""
    property string recommendedSetup: ""
    property string reasonText: ""
    property string difficultyText: ""
    property string scoreText: ""
    signal openRequested(string objectId)

    function valueOrFallback(value, fallbackText) {
        if (value === undefined || value === null || value === "")
            return fallbackText
        return value
    }

    function objectId() {
        return root.valueOrFallback(root.itemData.id, root.valueOrFallback(root.itemData.objectId, ""))
    }

    function objectType() {
        return root.valueOrFallback(root.typeText, root.valueOrFallback(root.itemData.type, "Oggetto"))
    }

    function objectTime() {
        if (root.visibilityText.length > 0)
            return root.visibilityText
        if (root.itemData.timeLabel !== undefined)
            return root.itemData.timeLabel + "  -  " + root.valueOrFallback(root.itemData.direction, "")
        return (root.itemData.homeTimeLabel ? root.itemData.homeTimeLabel : "Meglio alle " + root.itemData.best_time) + "  -  " + root.itemData.direction
    }

    function setupText() {
        return root.valueOrFallback(root.recommendedSetup, root.valueOrFallback(root.itemData.recommended_setup, root.valueOrFallback(root.itemData.setup, "")))
    }

    function scoreLabel() {
        if (root.scoreText.length > 0)
            return root.scoreText
        if (root.itemData.score !== undefined && root.itemData.score !== null)
            return root.itemData.score + "/100"
        return root.valueOrFallback(root.itemData.magnitude, "")
    }

    AppTheme {
        id: theme
    }

    Layout.fillWidth: true
    implicitHeight: Math.max(118, rowLayout.implicitHeight + 20)
    color: mouseArea.containsMouse ? "#20242b" : "transparent"
    radius: 8
    border.color: mouseArea.containsMouse ? "#303641" : "transparent"
    border.width: 1

    RowLayout {
        id: rowLayout
        anchors.fill: parent
        anchors.margins: 10
        spacing: 12

        Rectangle {
            Layout.preferredWidth: 56
            Layout.preferredHeight: 56
            radius: 8
            color: "#111319"
            border.color: "#303641"
            border.width: 1

            Image {
                anchors.fill: parent
                anchors.margins: 8
                source: root.assetBaseUrl + "/" + root.itemData.image
                fillMode: Image.PreserveAspectFit
                sourceSize.width: 96
                sourceSize.height: 96
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            spacing: 3

            Text {
                Layout.fillWidth: true
                text: root.itemData.name
                color: theme.textPrimary
                font.pixelSize: 15
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: root.difficultyText.length > 0 ? root.objectType() + "  -  " + root.difficultyText : root.objectType()
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: root.objectTime()
                color: theme.textMuted
                font.pixelSize: 12
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                visible: root.setupText().length > 0
                text: "Osservazione consigliata: " + root.setupText()
                color: theme.textSecondary
                font.pixelSize: 12
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                visible: root.reasonText.length > 0
                text: "Motivo: " + root.reasonText
                color: theme.textMuted
                font.pixelSize: 11
                elide: Text.ElideRight
            }
        }

        Text {
            Layout.preferredWidth: 96
            text: root.scoreLabel()
            horizontalAlignment: Text.AlignRight
            color: theme.cyan
            font.pixelSize: 14
            font.weight: Font.DemiBold
            elide: Text.ElideRight
        }
    }

    MouseArea {
        id: mouseArea
        anchors.fill: parent
        hoverEnabled: true
        cursorShape: Qt.PointingHandCursor
        onClicked: root.openRequested(root.objectId())
    }
}

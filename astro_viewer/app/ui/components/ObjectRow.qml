import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var itemData
    property string assetBaseUrl: ""
    signal openRequested(string objectId)

    Layout.fillWidth: true
    implicitHeight: 84
    color: mouseArea.containsMouse ? "#20242b" : "transparent"
    radius: 8
    border.color: mouseArea.containsMouse ? "#303641" : "transparent"
    border.width: 1

    RowLayout {
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
            spacing: 4

            Text {
                Layout.fillWidth: true
                text: root.itemData.name
                color: "#f4f7fb"
                font.pixelSize: 15
                font.weight: Font.DemiBold
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: root.itemData.type + "  -  " + root.itemData.visibility_class
                color: "#aeb7c4"
                font.pixelSize: 12
                elide: Text.ElideRight
            }

            Text {
                Layout.fillWidth: true
                text: (root.itemData.homeTimeLabel ? root.itemData.homeTimeLabel : "Meglio alle " + root.itemData.best_time) + "  -  " + root.itemData.direction
                color: "#788391"
                font.pixelSize: 12
                elide: Text.ElideRight
            }
        }

        Text {
            Layout.preferredWidth: 64
            text: root.itemData.magnitude
            horizontalAlignment: Text.AlignRight
            color: "#65d6e8"
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
        onClicked: root.openRequested(root.itemData.id)
    }
}

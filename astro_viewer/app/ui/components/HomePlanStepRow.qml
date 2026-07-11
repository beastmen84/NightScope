import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var itemData: ({})
    property string assetBaseUrl: ""
    property color accentColor: "#8bd17c"

    signal openRequested(string objectId)

    function value(key, fallbackText) {
        if (!root.itemData || root.itemData[key] === undefined || root.itemData[key] === null || root.itemData[key] === "")
            return fallbackText
        return root.itemData[key]
    }

    function objectId() {
        return root.value("objectId", "")
    }

    function imageSource() {
        var image = root.value("image", "")
        return image.length > 0 ? root.assetBaseUrl + "/" + image : ""
    }

    function timeDirectionLabel() {
        var parts = []
        var time = root.value("timeLabel", "")
        var direction = root.value("direction", "")
        if (time.length > 0)
            parts.push(time)
        if (direction.length > 0)
            parts.push(direction)
        return parts.join("  -  ")
    }

    AppTheme {
        id: theme
    }

    Layout.fillWidth: true
    implicitHeight: Math.max(108, stepLayout.implicitHeight + 18)
    radius: 8
    color: mouseArea.containsMouse ? "#20242b" : "transparent"
    border.color: mouseArea.containsMouse ? theme.border : "#29313b"
    border.width: 1

    RowLayout {
        id: stepLayout
        anchors.fill: parent
        anchors.margins: 9
        spacing: 10

        Rectangle {
            Layout.preferredWidth: 34
            Layout.preferredHeight: 34
            Layout.alignment: Qt.AlignTop
            radius: 8
            color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.14)
            border.color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.5)
            border.width: 1

            Text {
                anchors.centerIn: parent
                text: root.value("sequence", "")
                color: root.accentColor
                font.pixelSize: 14
                font.weight: Font.DemiBold
            }
        }

        Rectangle {
            Layout.preferredWidth: 52
            Layout.preferredHeight: 52
            Layout.alignment: Qt.AlignVCenter
            radius: 8
            color: "#111319"
            border.color: theme.border
            border.width: 1

            Image {
                anchors.fill: parent
                anchors.margins: 7
                source: root.imageSource()
                fillMode: Image.PreserveAspectFit
                sourceSize.width: 92
                sourceSize.height: 92
            }
        }

        ColumnLayout {
            Layout.fillWidth: true
            Layout.minimumWidth: 0
            spacing: 4

            RowLayout {
                Layout.fillWidth: true
                spacing: 8

                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: root.value("name", "Oggetto")
                    color: theme.textPrimary
                    font.pixelSize: 15
                    font.weight: Font.DemiBold
                    maximumLineCount: 1
                    elide: Text.ElideRight
                }

                Text {
                    Layout.alignment: Qt.AlignTop
                    visible: root.value("difficulty", "").length > 0
                    text: root.value("difficulty", "")
                    color: theme.textMuted
                    font.pixelSize: 12
                    maximumLineCount: 1
                    elide: Text.ElideRight
                }
            }

            Text {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                text: root.value("typeLabel", "Oggetto") + "  -  " + root.timeDirectionLabel()
                color: theme.textSecondary
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }

            Text {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                visible: root.value("compactSetup", "").length > 0
                text: root.value("compactSetup", "")
                color: theme.textMuted
                font.pixelSize: 12
                lineHeight: 1.12
                wrapMode: Text.WordWrap
            }
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

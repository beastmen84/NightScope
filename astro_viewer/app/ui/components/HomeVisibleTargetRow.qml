import QtQuick
import QtQuick.Layouts

Rectangle {
    id: root

    property var itemData: ({})
    property bool compact: false

    signal openRequested(string objectId)

    function value(key, fallbackText) {
        if (!root.itemData || root.itemData[key] === undefined || root.itemData[key] === null || root.itemData[key] === "")
            return fallbackText
        return root.itemData[key]
    }

    function objectId() {
        return root.value("objectId", "")
    }

    function accent() {
        return root.value("category", "") === "planet" ? theme.teal : theme.violet
    }

    AppTheme {
        id: theme
    }

    width: parent ? parent.width : implicitWidth
    implicitHeight: root.compact ? Math.max(82, compactLayout.implicitHeight + 16) : 46
    radius: 8
    color: mouseArea.containsMouse ? "#20242b" : "transparent"
    border.color: mouseArea.containsMouse ? theme.border : "transparent"
    border.width: 1

    RowLayout {
        id: tableLayout
        anchors.fill: parent
        anchors.leftMargin: 10
        anchors.rightMargin: 10
        anchors.topMargin: 6
        anchors.bottomMargin: 6
        spacing: 12
        visible: !root.compact

        Rectangle {
            Layout.preferredWidth: 4
            Layout.fillHeight: true
            radius: 2
            color: root.accent()
        }

        Text {
            Layout.fillWidth: true
            Layout.minimumWidth: 140
            text: root.value("name", qsTr("Oggetto"))
            color: theme.textPrimary
            font.pixelSize: 13
            font.weight: Font.DemiBold
            maximumLineCount: 1
            elide: Text.ElideRight
        }

        Text {
            Layout.preferredWidth: 170
            text: root.value("typeLabel", qsTr("Oggetto"))
            color: theme.textSecondary
            font.pixelSize: 12
            maximumLineCount: 1
            elide: Text.ElideRight
        }

        Text {
            Layout.preferredWidth: 145
            text: root.value("windowLabel", qsTr("n/d"))
            color: theme.textSecondary
            font.pixelSize: 12
            maximumLineCount: 1
            elide: Text.ElideRight
        }

        Text {
            Layout.preferredWidth: 105
            text: root.value("direction", qsTr("n/d"))
            color: theme.textMuted
            font.pixelSize: 12
            maximumLineCount: 1
            elide: Text.ElideRight
        }

        Text {
            Layout.preferredWidth: 90
            horizontalAlignment: Text.AlignRight
            text: root.value("difficulty", qsTr("n/d"))
            color: theme.textMuted
            font.pixelSize: 12
            maximumLineCount: 1
            elide: Text.ElideRight
        }
    }

    ColumnLayout {
        id: compactLayout
        anchors.fill: parent
        anchors.margins: 9
        spacing: 4
        visible: root.compact

        RowLayout {
            Layout.fillWidth: true
            spacing: 8

            Rectangle {
                Layout.preferredWidth: 4
                Layout.preferredHeight: 30
                radius: 2
                color: root.accent()
            }

            ColumnLayout {
                Layout.fillWidth: true
                Layout.minimumWidth: 0
                spacing: 1

                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: root.value("name", qsTr("Oggetto"))
                    color: theme.textPrimary
                    font.pixelSize: 14
                    font.weight: Font.DemiBold
                    maximumLineCount: 1
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    Layout.minimumWidth: 0
                    text: qsTr("%1  -  %2")
                        .arg(root.value("typeLabel", qsTr("Oggetto")))
                        .arg(root.value("categoryLabel", ""))
                    color: theme.textSecondary
                    font.pixelSize: 12
                    wrapMode: Text.WordWrap
                }
            }
        }

        Text {
            Layout.fillWidth: true
            Layout.leftMargin: 12
            text: qsTr("%1  -  %2  -  %3")
                .arg(root.value("windowLabel", qsTr("n/d")))
                .arg(root.value("direction", qsTr("n/d")))
                .arg(root.value("difficulty", qsTr("n/d")))
            color: theme.textMuted
            font.pixelSize: 12
            wrapMode: Text.WordWrap
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

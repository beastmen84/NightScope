import QtQuick
import QtQuick.Layouts

Item {
    id: root

    property var hourly: []
    property color barColor: "#65d6e8"

    implicitHeight: 150
    Layout.fillWidth: true

    RowLayout {
        anchors.fill: parent
        spacing: 8

        Repeater {
            model: root.hourly

            delegate: ColumnLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                spacing: 6

                Item {
                    Layout.fillWidth: true
                    Layout.fillHeight: true

                    Rectangle {
                        anchors.horizontalCenter: parent.horizontalCenter
                        anchors.bottom: parent.bottom
                        width: Math.max(10, parent.width * 0.55)
                        height: Math.max(8, parent.height * (modelData.cloudCover / 100))
                        radius: 5
                        color: root.barColor
                        opacity: 0.4 + (modelData.cloudCover / 180)
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: modelData.cloudCover + "%"
                    color: "#aeb7c4"
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: 11
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: modelData.time
                    color: "#788391"
                    horizontalAlignment: Text.AlignHCenter
                    font.pixelSize: 10
                    elide: Text.ElideRight
                }
            }
        }
    }
}


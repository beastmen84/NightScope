pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

Item {
    id: root

    property var hourly: []
    property color barColor: "#788391"
    property color nightBarColor: "#63e6be"
    property int minimumColumnWidth: 44

    implicitHeight: 160
    Layout.fillWidth: true

    Flickable {
        id: chartFlick
        anchors.fill: parent
        clip: true
        contentWidth: Math.max(width, bars.implicitWidth)
        contentHeight: height
        flickableDirection: Flickable.HorizontalFlick
        boundsBehavior: Flickable.StopAtBounds

        Row {
            id: bars
            height: chartFlick.height - 8
            spacing: 8
            property real columnWidth: root.hourly.length > 0
                                       ? Math.max(root.minimumColumnWidth,
                                                  (chartFlick.width - spacing * (root.hourly.length - 1))
                                                  / root.hourly.length)
                                       : root.minimumColumnWidth

            Repeater {
                model: root.hourly

                delegate: ColumnLayout {
                    id: weatherBarColumn

                    required property var modelData

                    width: bars.columnWidth
                    height: bars.height
                    spacing: 6
                    property bool nightHour: Boolean(modelData.isObservingNight)

                    Item {
                        Layout.fillWidth: true
                        Layout.fillHeight: true

                        Rectangle {
                            anchors.horizontalCenter: parent.horizontalCenter
                            anchors.bottom: parent.bottom
                            width: Math.max(10, parent.width * 0.55)
                            height: Math.max(8, parent.height * (weatherBarColumn.modelData.cloudCover / 100))
                            radius: 5
                            color: weatherBarColumn.nightHour ? root.nightBarColor : root.barColor
                            opacity: weatherBarColumn.nightHour
                                     ? 0.72 + (weatherBarColumn.modelData.cloudCover / 400)
                                     : 0.32 + (weatherBarColumn.modelData.cloudCover / 300)
                        }
                    }

                    Text {
                        Layout.fillWidth: true
                        text: weatherBarColumn.modelData.cloudCover + "%"
                        color: weatherBarColumn.nightHour ? root.nightBarColor : "#aeb7c4"
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 11
                        elide: Text.ElideRight
                    }

                    Text {
                        Layout.fillWidth: true
                        text: weatherBarColumn.modelData.time
                        color: weatherBarColumn.nightHour ? root.nightBarColor : "#788391"
                        horizontalAlignment: Text.AlignHCenter
                        font.pixelSize: 10
                        font.weight: weatherBarColumn.nightHour ? Font.DemiBold : Font.Normal
                        elide: Text.ElideRight
                    }
                }
            }
        }

        ScrollBar.horizontal: ScrollBar {
            policy: chartFlick.contentWidth > chartFlick.width
                    ? ScrollBar.AsNeeded
                    : ScrollBar.AlwaysOff
        }
    }
}

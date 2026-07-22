pragma ComponentBehavior: Bound

import QtQuick
import QtQuick.Effects

Item {
    id: root

    property url source
    property int fillMode: Image.PreserveAspectFit
    property color nightColor: theme.cyan

    AppTheme {
        id: theme
    }

    Image {
        anchors.fill: parent
        source: root.source
        fillMode: root.fillMode
        sourceSize.width: Math.max(1, root.width * 2)
        sourceSize.height: Math.max(1, root.height * 2)
        layer.enabled: theme.redNightVision
        layer.effect: MultiEffect {
            colorization: 1.0
            colorizationColor: root.nightColor
        }
    }
}

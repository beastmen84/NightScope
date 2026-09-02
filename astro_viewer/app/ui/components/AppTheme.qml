// Purpose: Define the shared visual palette for normal and red-night-vision modes.
// Contract: Derives colors from appearanceManager and carries no independent persistent state.

import QtQuick

QtObject {
    readonly property bool redNightVision: typeof appearanceManager !== "undefined"
                                                   && appearanceManager.redNightVisionEnabled

    readonly property color background: redNightVision ? "#050000" : "#0f1014"
    readonly property color surface: redNightVision ? "#0b0101" : "#171a20"
    readonly property color surfaceRaised: redNightVision ? "#130202" : "#20242b"
    readonly property color border: redNightVision ? "#35100c" : "#303641"
    readonly property color textPrimary: redNightVision ? "#d94a3d" : "#f4f7fb"
    readonly property color textSecondary: redNightVision ? "#a3342c" : "#aeb7c4"
    readonly property color textMuted: redNightVision ? "#70231f" : "#788391"
    readonly property color cyan: redNightVision ? "#d94a3d" : "#65d6e8"
    readonly property color teal: redNightVision ? "#c23d33" : "#6ee7b7"
    readonly property color amber: redNightVision ? "#b5362d" : "#f6c768"
    readonly property color coral: redNightVision ? "#a82f28" : "#ff8f7a"
    readonly property color violet: redNightVision ? "#bc3930" : "#b8a1ff"
    readonly property color green: redNightVision ? "#c43c32" : "#8bd17c"
    readonly property color red: redNightVision ? "#e05243" : "#ff6b6b"
    readonly property color weatherNight: redNightVision ? "#c23d33" : "#63e6be"

    readonly property color sidebar: redNightVision ? "#070000" : "#12151a"
    readonly property color sidebarBorder: redNightVision ? "#260906" : "#252b34"
    readonly property color field: redNightVision ? "#100202" : "#1c222b"
    readonly property color surfaceLow: redNightVision ? "#090101" : "#15181e"
    readonly property color surfaceDeep: redNightVision ? "#080101" : "#151a20"
    readonly property color surfaceDeepHover: redNightVision ? "#140403" : "#1b222a"
    readonly property color surfaceAlternate: redNightVision ? "#0d0202" : "#1a1e25"
    readonly property color surfaceHover: redNightVision ? "#1b0504" : "#252b34"
    readonly property color surfacePressed: redNightVision ? "#240705" : "#2a313b"
    readonly property color surfaceDisabledHover: redNightVision ? "#0d0202" : "#191d23"
    readonly property color surfaceDestructiveHover: redNightVision ? "#200504" : "#262c35"
    readonly property color imageWell: redNightVision ? "#070000" : "#111319"
    readonly property color borderSubtle: redNightVision ? "#260906" : "#29313b"
    readonly property color navSelected: redNightVision ? "#220605" : "#27313b"
    readonly property color navHover: redNightVision ? "#160403" : "#1f242c"
    readonly property color navSelectedBorder: redNightVision ? "#52150f" : "#465260"
    readonly property color compassSurface: redNightVision ? "#070101" : "#111820"
    readonly property color compassBorder: redNightVision ? "#36100c" : "#26404a"
    readonly property color compassOuter: redNightVision ? "#35100c" : "#243746"
    readonly property color compassMiddle: redNightVision ? "#4a160f" : "#1f5861"
    readonly property color compassTick: redNightVision ? "#651d14" : "#2b6570"
    readonly property color moonDarkCenter: redNightVision ? "#130202" : "#1d2430"
    readonly property color moonDarkMiddle: redNightVision ? "#070000" : "#0b0f16"
    readonly property color moonDarkEdge: redNightVision ? "#030000" : "#05070b"
    readonly property color moonLightCenter: redNightVision ? "#d94a3d" : "#fff7db"
    readonly property color moonLightMiddle: redNightVision ? "#a3342c" : "#d7dce3"
    readonly property color moonLightEdge: redNightVision ? "#70231f" : "#9ba6b4"
    readonly property color moonGlow: redNightVision ? "#a3342c" : "#cae0f4"
    readonly property color moonTerminator: redNightVision ? "#70231f" : "#75808d"
    readonly property color moonOutline: redNightVision ? "#4d1713" : "#46505f"
    readonly property color moonShadowCenter: redNightVision ? "#0b0101" : "#151b24"
    readonly property color moonShadowMiddle: redNightVision ? "#050000" : "#070a0f"
    readonly property color moonShadowEdge: redNightVision ? "#020000" : "#020305"

    function withAlpha(value, opacity) {
        return Qt.rgba(value.r, value.g, value.b, opacity)
    }

    function scoreColor(scoreValue) {
        var score = Number(scoreValue)
        if (!isFinite(score)) return red
        if (score > 85) return teal
        if (score > 70) return cyan
        if (score > 50) return amber
        if (score > 25) return coral
        return red
    }

    function booleanStateColor(value, known) {
        if (known !== true) return textMuted
        return value === true ? green : coral
    }
}

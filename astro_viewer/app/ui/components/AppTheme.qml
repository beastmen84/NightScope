import QtQuick

QtObject {
    readonly property color background: "#0f1014"
    readonly property color surface: "#171a20"
    readonly property color surfaceRaised: "#20242b"
    readonly property color border: "#303641"
    readonly property color textPrimary: "#f4f7fb"
    readonly property color textSecondary: "#aeb7c4"
    readonly property color textMuted: "#788391"
    readonly property color cyan: "#65d6e8"
    readonly property color teal: "#6ee7b7"
    readonly property color amber: "#f6c768"
    readonly property color coral: "#ff8f7a"
    readonly property color violet: "#b8a1ff"
    readonly property color green: "#8bd17c"
    readonly property color red: "#ff6b6b"

    function scoreColor(score) {
        if (score === "Ottimo") return teal
        if (score === "Ottima") return teal
        if (score === "Buono") return cyan
        if (score === "Buona") return cyan
        if (score === "Discreto") return amber
        if (score === "Scarso") return coral
        if (score === "Scarsa") return coral
        if (score === "Pessima") return red
        return red
    }
}

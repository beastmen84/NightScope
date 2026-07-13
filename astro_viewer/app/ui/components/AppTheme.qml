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

    function scoreColor(scoreValue) {
        var score = Number(scoreValue)
        if (!isFinite(score)) return red
        if (score > 85) return teal
        if (score > 70) return cyan
        if (score > 50) return amber
        if (score > 25) return coral
        return red
    }
}

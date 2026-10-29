import QtQuick

// Küçük resmin altında izlenen kısım (YouTube'daki kırmızı çizginin bizdeki rengi bebe mavisi).
Item {
    id: c
    property string videoId
    // Kapanışta kayıt nesnesi QML'den önce gidebiliyor; o anda boş sayılır.
    readonly property real oran: kayit ? (kayit.surum, kayit.oran(videoId)) : 0
    visible: oran > 0
    anchors { left: parent.left; right: parent.right; bottom: parent.bottom }
    height: 4
    Rectangle { anchors.fill: parent; color: "#99808080" }
    Rectangle { anchors.left: parent.left; width: parent.width * Math.min(1, c.oran); height: parent.height; color: Renk.videoMavi }
}

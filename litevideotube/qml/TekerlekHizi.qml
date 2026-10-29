import QtQuick

// Farenin tekerleği: bir çentik sayfayı 120 px kaydırır, kısa bir yumuşatmayla. Qt'nin kendi kaydırması
// çentik başına 72 px'ti ("kaydırma yavaş", tarayıcıya göre çok çevirmek gerekiyordu).
// Dokunmatik yüzey Qt'nin kendi kaydırmasında kalır. Kaydırılan sayfanın içine konur: TekerlekHizi { hedef: ... }
WheelHandler {
    id: t
    property Flickable hedef
    readonly property int centik: 120
    acceptedDevices: PointerDevice.Mouse
    onWheel: function(olay) {
        var f = t.hedef
        var enCok = f.originY + Math.max(0, f.contentHeight - f.height)
        var simdiki = kayma.running ? kayma.to : f.contentY
        var yeni = Math.max(f.originY, Math.min(enCok, simdiki - olay.angleDelta.y / 120 * t.centik))
        if (yeni === f.contentY) return
        kayma.to = yeni
        kayma.restart()
    }
    property NumberAnimation kayma: NumberAnimation { target: t.hedef; property: "contentY"; duration: 120; easing.type: Easing.OutCubic }
}

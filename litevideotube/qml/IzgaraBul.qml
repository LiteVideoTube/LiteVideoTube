import QtQuick

// Video ızgarasında sayfada bul (Ctrl+F): başlık ve kanal adında arar, ızgaranın verisinde (ekranda kurulmamış
// kartlar da bulunur). Bulunan kart çerçevelenir (VideoKarti, pencere.bulunanId). bastakiler: ızgaranın
// başlığında (header) duran videolar (abonelik sayfasındaki bölümler); onlar bulununca sayfa başa alınır.
BulKaynagi {
    id: b
    property GridView izgara
    property var liste: []
    property var bastakiler: []
    hedef: izgara
    function eslesmeler(sorgu) {
        var l = [], hepsi = b.bastakiler.concat(b.liste)
        for (var i = 0; i < hepsi.length; i++) {
            var v = hepsi[i]
            if (pencere.bulKucuk((v.baslik || "") + " " + (v.kanal || "")).indexOf(sorgu) >= 0)
                l.push({ y: i, i: i - b.bastakiler.length, id: v.id })
        }
        return l
    }
    // Baştaki bölümlerde bulunan kart görünür yapılır; önceden sayfa başa alınıyordu, bölümler uzunken kart aşağıda
    // görünmeden kalıyordu (28 Ekim).
    function kartBul(oge, id) {
        for (var i = 0; i < oge.children.length; i++) {
            var c = oge.children[i]
            if (c.v && c.v.id === id && c.visible) return c
            var k = kartBul(c, id)
            if (k) return k
        }
        return null
    }
    function goster(m) {
        pencere.bulunanId = m.id
        if (m.i >= 0) { b.izgara.positionViewAtIndex(m.i, GridView.Contain); return }
        var kart = b.izgara.headerItem ? kartBul(b.izgara.headerItem, m.id) : null
        if (kart) pencere.kaydirGoster(kart, 0); else b.izgara.positionViewAtBeginning()
    }
    function birak() { pencere.bulunanId = "" }
}

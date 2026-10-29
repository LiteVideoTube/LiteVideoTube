import QtQuick

// Başlıklı Shorts şeridi. tekSatir (abonelik sayfası): satıra sığdığı kadar kart, gerisi Shorts görünümünde aşağı
// kaydırarak gezilir; değilse (Keşfet) hepsi alt alta satırlarda.
Column {
    id: s
    property string baslik: qsTr("Shorts")
    property string simge: "shorts"
    property var simgeRenk: ["ff6b9a", "e8336d"]
    property var liste: []
    property string kaynak     // Shorts görünümünde listenin devamı nereden gelir (Ana.qml, shortsKaynak)
    // Sayfada bul (Ctrl+F: abonelik sayfasında Shorts başlıkları bulunmuyordu): ekrandaki kartların
    // başlığı ve kanal adı. bulSira: sayfadaki yeri (bulunanların sırası için), kaydirici: bulununca başa alınacak ızgara.
    property real bulSira: 0
    property var kaydirici: null
    // Abonelik sayfasında başlığa tıklayınca kapanır (BolumBasligi); kapalıyken yalnız başlık kalır.
    property bool kapanir: false
    property bool kapali: false
    signal degistir()
    BulKaynagi {
        hedef: s
        function eslesmeler(sorgu) {
            var l = [], n = s.kapali ? 0 : s.tekSatir ? Math.min(s.sigan, s.liste.length) : s.liste.length
            for (var i = 0; i < n; i++) {
                var v = s.liste[i]
                if (pencere.bulKucuk((v.baslik || "") + " " + (v.kanal || "")).indexOf(sorgu) >= 0)
                    l.push({ y: s.bulSira + i / 1000, id: v.id, i: i })
            }
            return l
        }
        // Bulunan kart görünür yapılır (önceden sayfa başa alınıyordu: şerit aşağıda kalınca kart görünmüyordu, 28 Ekim).
        function goster(m) {
            var kart = kartlar.itemAt(m.i)
            if (kart) pencere.kaydirGoster(kart, 0); else if (s.kaydirici) s.kaydirici.positionViewAtBeginning()
            pencere.bulunanId = m.id
        }
        function birak() { pencere.bulunanId = "" }
    }
    property bool tekSatir: true
    readonly property int kartEn: 180
    readonly property int sigan: Math.max(1, Math.floor((width - 8 + 12) / (kartEn + 12)))
    visible: liste.length > 0
    height: visible ? implicitHeight : 0
    spacing: 8
    bottomPadding: visible ? 16 : 0
    BolumBasligi { anchors.left: parent.left; baslik: s.baslik; simge: s.simge; simgeRenk: s.simgeRenk; kapanir: s.kapanir; kapali: s.kapali; sayi: s.liste.length
        bulSira: s.bulSira - 0.25
        onDegistir: s.degistir() }
    Flow {
        visible: !s.kapali
        width: parent.width
        spacing: 12
        Repeater {
            id: kartlar
            model: s.tekSatir ? Math.min(s.sigan, s.liste.length) : s.liste.length
            ShortsKarti { width: s.kartEn; liste: s.liste; sira: index; kaynak: s.kaynak }
        }
    }
    Rectangle { anchors.left: parent.left; width: parent.width - 8; height: 1; color: Renk.cizgi }
}

import QtQuick

// Abonelik sayfasındaki bir bölümün başlığı (Bolum, ShortsSeridi). kapanir ise başlığa tıklayınca bölüm kapanır
// ya da açılır: açıkken aşağı bakan ok, kapalıyken sağa bakan ok ve bölümdeki video sayısı.
// Ok başlığın hemen yanında, sayı oktan sonra ("Şu an canlı › · 10"); açıklama yazısı yok
// (gereksiz tanım, program profesyonel görünsün).
// Başlık yazısı sürükleyince seçilir (SecimKatmani), tıklayınca yine açar ya da kapatır.
// 28 Ekim (başlıklar göze çarpmıyordu): her bölümün simgesi var, yazı kalın ve büyük; sayfada bul (Ctrl+F) başlıkları
// da bulur ("shorts" yazınca bulunmuyordu). bulSira: bulunanların sırasında yeri (bölümün ilk videosundan hemen önce).
Item {
    id: b
    property string baslik
    property string simge
    property var simgeRenk: null   // [koyu görünümde, açık görünümde] (Renk.simgeRenkli); yoksa yazı renginde
    property bool kirmizi: false   // başlığın önünde kırmızı nokta (Şu an canlı)
    property bool kapanir: true
    property bool kapali: false
    property int sayi: 0
    property real bulSira: 0
    property bool bulundu: false
    signal degistir()
    width: satir.width; height: satir.height
    function tikla() { if (b.kapanir) b.degistir() }
    BulKaynagi {
        hedef: b
        function eslesmeler(sorgu) {
            return sorgu.length && pencere.bulKucuk(b.baslik).indexOf(sorgu) >= 0 ? [{ y: b.bulSira }] : []
        }
        function goster(m) { b.bulundu = true; pencere.kaydirGoster(b, 0) }
        function birak() { b.bulundu = false }
    }
    MouseArea { anchors.fill: parent; enabled: b.kapanir; cursorShape: Qt.PointingHandCursor; onClicked: b.tikla() }
    HoverHandler { id: fare }
    Row {
        id: satir
        spacing: 8
        Rectangle { visible: b.kirmizi && b.simge === ""; width: 10; height: 10; radius: 5; color: "#cc0000"
            anchors.verticalCenter: parent.verticalCenter }
        Image { visible: b.simge !== ""; source: !b.simge ? "" : b.simgeRenk ? Renk.simgeRenkli(b.simge, b.simgeRenk) : Renk.simge(b.simge); width: 24; height: 24
            sourceSize: Qt.size(48, 48); anchors.verticalCenter: parent.verticalCenter }
        Text { id: yazi; text: b.baslik; color: Renk.yazi; font.pixelSize: 20; font.weight: Font.Bold; anchors.verticalCenter: parent.verticalCenter
            // Sayfada bulununca seçili yazı rengiyle (SecilirYazi'daki gibi) işaretlenir.
            Rectangle { z: -1; anchors.fill: parent; anchors.margins: -2; radius: 3; color: "#663ea6ff"; visible: b.bulundu }
            SecimKatmani { tiklama: b.kapanir ? b.tikla : null } }
        Image { visible: b.kapanir; source: Renk.simge("expand_more"); width: 22; height: 22; sourceSize: Qt.size(44, 44)
            anchors.verticalCenter: parent.verticalCenter
            rotation: b.kapali ? (b.LayoutMirroring.enabled ? 90 : -90) : 0
            opacity: fare.hovered ? 1 : 0.6 }
        Text { visible: b.kapali && b.sayi > 0; text: "· " + b.sayi; color: Renk.yaziSoluk; font.pixelSize: 15
            anchors.verticalCenter: parent.verticalCenter }
    }
}

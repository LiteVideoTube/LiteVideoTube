import QtQuick

// Dikey Shorts kartı (abonelik sayfasının Shorts şeridi, Keşfet, kanal sayfasının Shorts bölümü). Tıklayınca
// dikey Shorts görünümü açılır; aşağı kaydırınca aynı listenin sıradakine geçer.
Item {
    id: k
    property var liste: []
    property int sira: 0
    property string kaynak     // Ana.qml, shortsKaynak
    readonly property var v: liste[sira]
    implicitHeight: resimKutu.height + 8 + yazilar.implicitHeight + 12

    // Sayfada bul (Ctrl+F) bu videoyu bulduysa bütün kart (resim ve yazı) mavi zeminle işaretlenir. Önceden yalnız
    // resmin kenarında ince çizgi vardı; kırmızı çerçeveli resimlerde seçilmiyordu, aranan söz de çoğu zaman başlığın
    // "…" ile kesilen yerindeydi (28 Ekim).
    Rectangle { anchors.fill: parent; anchors.margins: -6; anchors.bottomMargin: 0; radius: 14
        color: "#403ea6ff"; border.color: Renk.mavi; border.width: 3
        visible: !!k.v && pencere.bulunanId === k.v.id }

    Rectangle {
        id: resimKutu
        width: parent.width; height: width * 16 / 9; radius: 12; color: Renk.yuzey
        Image {
            anchors.fill: parent; fillMode: Image.PreserveAspectCrop
            source: k.v ? k.v.resim : ""; asynchronous: true; sourceSize.width: 240
        }
        IlerlemeCizgisi { videoId: k.v ? k.v.id : "" }
    }
    Column {
        id: yazilar
        z: 1   // yazılar sürükleyince seçilsin (SecimKatmani): kartın tıklama alanının üstünde
        anchors { left: parent.left; right: parent.right; top: resimKutu.bottom; topMargin: 8 }
        spacing: 3
        Text { width: parent.width; text: k.v ? k.v.baslik : ""; color: Renk.yazi; font.pixelSize: 14; font.weight: Font.Medium
            wrapMode: Text.Wrap; maximumLineCount: 2; elide: Text.ElideRight
            SecimKatmani { tiklama: k.solTik } }
        Text { width: parent.width; color: Renk.yaziSoluk; font.pixelSize: 12; elide: Text.ElideRight
            text: k.v ? [k.v.kanal, k.v.izlenme, k.v.tarih].filter(function(x) { return x }).join(" • ") : ""
            SecimKatmani { tiklama: k.solTik } }
    }
    // Sol tık açar; orta tık ya da Ctrl+tık yeni sekmede (tarayıcı alışkanlığı).
    function solTik(tuslar) {
        if (tuslar & Qt.ControlModifier) pencere.shortsYeniSekmede(k.liste, k.sira, k.kaynak)
        else pencere.shortsAc(k.liste, k.sira, k.kaynak)
    }
    MouseArea {
        anchors.fill: parent; cursorShape: Qt.PointingHandCursor
        acceptedButtons: Qt.LeftButton | Qt.MiddleButton | Qt.RightButton
        onClicked: function(m) {
            if (m.button === Qt.RightButton) pencere.yeniSekmeMenusu(function() { pencere.shortsYeniSekmede(k.liste, k.sira, k.kaynak) })
            else if (m.button === Qt.MiddleButton) pencere.shortsYeniSekmede(k.liste, k.sira, k.kaynak)
            else k.solTik(m.modifiers)
        }
    }
}
